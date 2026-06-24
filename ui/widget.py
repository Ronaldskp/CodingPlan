"""Frameless, draggable desktop usage widget."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QPoint, QRect, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QMouseEvent, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from core.cache import read_usage, resolve_cache_path
from core.collector import collect_usage, load_config
from core.freshness import compute_cache_freshness, format_updated_with_freshness
from core.time_display import format_reset_time
from core.paths import application_icon_path, data_path, project_root as project_root_func
from core.security import sanitize_message
from core.ui_state import read_ui_state, write_ui_state

COLOR_NORMAL = "#65d6a6"
COLOR_WARNING = "#f5c451"
COLOR_DANGER = "#ff6b7a"
COLOR_MUTED = "#87909f"


class RefreshThread(QThread):
    completed = Signal()
    failed = Signal(str)

    def __init__(self, project_root: Path, config: dict[str, Any]) -> None:
        super().__init__()
        self.project_root = project_root
        self.config = config

    def run(self) -> None:
        try:
            collect_usage(self.project_root, self.config)
        except Exception as exc:
            self.failed.emit(sanitize_message(exc))
        else:
            self.completed.emit()


class ProviderCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("providerCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 7)
        layout.setSpacing(2)
        header = QHBoxLayout()
        self.title = QLabel(title.upper())
        self.title.setObjectName("cardTitle")
        self.status = QLabel("unsupported")
        self.status.setObjectName("providerStatus")
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.status)
        layout.addLayout(header)
        self._setup_rows(layout)
        self.message = QLabel("")
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.message.hide()
        layout.addWidget(self.message)

    def _setup_rows(self, layout: QVBoxLayout) -> None:
        self.five = self._row("5H", layout)
        self.week = self._row("WEEK", layout)

    def _row(self, label: str, layout: QVBoxLayout) -> QLabel:
        widget = QLabel(f"{label:<5} --")
        widget.setObjectName("quota")
        layout.addWidget(widget)
        return widget

    def update_data(self, data: dict[str, Any]) -> None:
        status = data.get("status", "error")
        self.status.setText(str(status))
        self.status.setStyleSheet(
            f"color: {COLOR_NORMAL if status == 'ok' else COLOR_MUTED};"
        )
        self._update_rows(data, status)
        message = str(data.get("message") or "")
        self.message.setText(message)
        self.message.setVisible(bool(message) and status != "ok")

    def _update_rows(self, data: dict[str, Any], status: str) -> None:
        self._set_quota(self.five, "5H", data.get("fiveHour", {}), status)
        self._set_quota(self.week, "WEEK", data.get("weekly", {}), status)

    def _set_quota(self, label: QLabel, prefix: str, window: dict[str, Any], status: str) -> None:
        value = window.get("remainingPercent") if isinstance(window, dict) else None
        pct_text = "  --" if value is None else f"{value:>3}%"
        reset = format_reset_time(window.get("resetAt")) if isinstance(window, dict) else "--"
        stale = " stale" if value is not None and status != "ok" else ""
        label.setText(f"{prefix:<5} {pct_text}   {reset}{stale}")
        label.setStyleSheet(f"color: {_quota_color(value, status)};")


class DeepSeekCard(ProviderCard):
    def _setup_rows(self, layout: QVBoxLayout) -> None:
        self.bal = self._row("BAL", layout)
        self.today = self._row("TODAY", layout)

    def _update_rows(self, data: dict[str, Any], status: str) -> None:
        balance = data.get("balance") or {}
        today = data.get("today") or {}
        currency = str(balance.get("currency") or "CNY")
        total = balance.get("total")
        spend = today.get("estimatedSpend")
        total_text = "--" if total is None else f"{currency} {float(total):.2f}"
        spend_text = "--" if spend is None else f"~{currency} {float(spend):.2f}"
        stale = status != "ok"
        self.bal.setText(f"{'BAL':<5} {total_text}{'  stale' if stale and total is not None else ''}")
        self.today.setText(
            f"{'TODAY':<5} {spend_text}{'  stale' if stale and spend is not None else ''}"
        )
        color = _quota_color(100 if status == "ok" else None, status)
        self.bal.setStyleSheet(f"color: {color};")
        self.today.setStyleSheet(f"color: {color};")


class CodingPlanWidget(QWidget):
    def __init__(self, project_root: Path | None = None) -> None:
        super().__init__()
        self.project_root = project_root or project_root_func()
        self.config = load_config(self.project_root)
        self.cache_path = resolve_cache_path(self.project_root, self.config["app"]["cache_path"])
        self.state_path = data_path("ui_state.json")
        self.drag_offset = None
        self.refresh_thread: RefreshThread | None = None
        self.exit_requested = False
        self.last_updated_at: Any = None
        self.tray_icon: QSystemTrayIcon | None = None
        saved_state = read_ui_state(self.state_path)
        self.always_on_top = bool(
            saved_state.get("always_on_top", self.config["ui"].get("always_on_top", True))
        )
        self.collapsible = bool(self.config["ui"].get("collapsible", True))
        self.collapsed = self.collapsible and bool(saved_state.get("collapsed", False))
        self.click_title_to_toggle = bool(
            self.config["ui"].get("click_title_to_toggle_collapse", True)
        )
        self.collapsed_height = int(self.config["ui"].get("collapsed_height", 64))
        self.expanded_height = int(self.config["ui"].get("expanded_height", 300))
        self._drag_start: QPoint | None = None
        self._is_dragging = False
        self._drag_threshold = 4

        self.setWindowTitle("Coding Plan Widget")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(float(self.config["ui"].get("opacity", 0.92)))
        self.resize(int(self.config["ui"].get("width", 280)), int(self.config["ui"].get("height", 300)))
        self._apply_flags()
        self._build_ui()
        self._apply_style()
        self._setup_tray()
        self._restore_position(saved_state)
        self.load_cache()

        interval_ms = max(30, int(self.config["app"].get("refresh_interval_seconds", 180))) * 1000
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(interval_ms)
        self.freshness_timer = QTimer(self)
        self.freshness_timer.timeout.connect(self._update_freshness)
        self.freshness_timer.start(60000)
        QTimer.singleShot(0, self.refresh_data)

    def _apply_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(7)

        self.header_widget = QWidget(self)
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("CODING ENERGY")
        title.setObjectName("header")
        header.addWidget(title)
        self.face = QLabel("(?_?)")
        self.face.setObjectName("face")
        header.addWidget(self.face)
        header.addStretch()

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setObjectName("iconButton")
        self.refresh_btn.setFlat(True)
        self.refresh_btn.setFixedSize(22, 22)
        self.refresh_btn.setToolTip("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)

        self.collapse_btn = QPushButton("˄")
        self.collapse_btn.setObjectName("iconButton")
        self.collapse_btn.setFlat(True)
        self.collapse_btn.setFixedSize(22, 22)
        self.collapse_btn.setToolTip("Collapse/Expand")
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        self.collapse_btn.setVisible(self.collapsible)
        header.addWidget(self.collapse_btn)

        root.addWidget(self.header_widget)

        self.cards_widget = QWidget(self)
        cards_layout = QVBoxLayout(self.cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(7)
        self.codex_card = ProviderCard("Codex")
        self.kimi_card = ProviderCard("Kimi")
        self.deepseek_card = DeepSeekCard("DeepSeek")
        cards_layout.addWidget(self.codex_card)
        cards_layout.addWidget(self.kimi_card)
        cards_layout.addWidget(self.deepseek_card)
        root.addWidget(self.cards_widget)

        self.summary = QLabel("")
        self.summary.setObjectName("summary")
        self.summary.setMinimumWidth(0)
        self.summary.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.summary.hide()
        root.addWidget(self.summary)

        self.updated = QLabel("Updated --:--")
        self.updated.setObjectName("updated")
        root.addWidget(self.updated)

        self._apply_collapse_state(initial=True)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { color: #f1f4f8; font-family: "Segoe UI"; font-size: 12px; }
            #header { font-size: 14px; font-weight: 700; letter-spacing: 1px; }
            #face { color: #86a7ff; font-family: Consolas; font-weight: 700; }
            #providerCard { background: rgba(35, 40, 52, 215); border: 1px solid rgba(255,255,255,25); border-radius: 8px; }
            #cardTitle { color: #b9c7df; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            #providerStatus { color: #87909f; font-size: 9px; }
            #quota { font-family: Consolas; font-size: 14px; font-weight: 700; }
            #message { color: #87909f; font-size: 9px; }
            #updated { color: #87909f; font-size: 10px; }
            #iconButton { color: #b9c7df; font-family: "Segoe UI"; font-size: 14px; font-weight: 700; border: none; background: transparent; }
            #iconButton:hover { color: #f1f4f8; }
            #iconButton:disabled { color: #555c66; }
            #summary { font-family: Consolas; font-size: 10px; font-weight: 700; color: #b9c7df; }
            """
        )

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self._application_icon()
        QApplication.instance().setWindowIcon(icon)
        self.setWindowIcon(icon)
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip("CodingPlanWidget")
        menu = QMenu()
        show_action = menu.addAction("Show")
        hide_action = menu.addAction("Hide")
        refresh_action = menu.addAction("Refresh")
        menu.addSeparator()
        data_action = menu.addAction("Open Data Folder")
        project_action = menu.addAction("Open Project Folder")
        top_action = QAction("Toggle Always on Top", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self.always_on_top)
        menu.addAction(top_action)
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        show_action.triggered.connect(self.show_and_activate)
        hide_action.triggered.connect(self.hide)
        refresh_action.triggered.connect(self.refresh_data)
        data_action.triggered.connect(self.open_data_folder)
        project_action.triggered.connect(self.open_project_folder)
        top_action.triggered.connect(self.toggle_always_on_top)
        exit_action.triggered.connect(self.request_exit)
        tray.activated.connect(self._tray_activated)
        tray.setContextMenu(menu)
        tray.show()
        self.tray_icon = tray

    def _application_icon(self) -> QIcon:
        icon_path = application_icon_path()
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                return icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#26334f"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
        painter.setPen(QColor("#65d6a6"))
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(27)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "CP")
        painter.end()
        return QIcon(pixmap)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 13, 13)
        painter.fillPath(path, QColor(18, 21, 29, 235))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if not self._is_dragging and self._drag_start is not None:
                moved = (event.globalPosition().toPoint() - self._drag_start).manhattanLength()
                if moved > self._drag_threshold:
                    self._is_dragging = True
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.drag_offset = None
        if (
            not self._is_dragging
            and event.button() == Qt.MouseButton.LeftButton
            and self.collapsible
            and self.click_title_to_toggle
            and self.header_widget is not None
            and self.header_widget.geometry().contains(event.pos())
        ):
            self._toggle_collapse()
        self._is_dragging = False

    def _toggle_collapse(self) -> None:
        if not self.collapsible:
            return
        self.collapsed = not self.collapsed
        self._apply_collapse_state()
        self._save_state()

    def _apply_collapse_state(self, initial: bool = False) -> None:
        width = int(self.config["ui"].get("width", 280))
        if self.collapsed:
            self.setFixedWidth(width)
            self.cards_widget.hide()
            self.summary.show()
            self.updated.hide()
            self.collapse_btn.setText("˅")
            self.setFixedHeight(self.collapsed_height)
            self.resize(width, self.collapsed_height)
        else:
            self.cards_widget.show()
            self.summary.hide()
            self.updated.show()
            self.collapse_btn.setText("˄")
            self.setMaximumSize(16777215, 16777215)
            self.setMinimumSize(0, 0)
            self.setFixedWidth(width)
            self.resize(width, self.expanded_height)
        self._update_summary()

    def _update_summary(self) -> None:
        usage = read_usage(self.cache_path, create_if_missing=True)
        providers = usage.get("providers", {})
        show_reset = (
            self.config["ui"].get("show_reset_times", True)
            and self.config["ui"].get("compact_summary_show_reset", True)
        )
        text = _format_compact_summary(providers, show_reset=show_reset)
        freshness = compute_cache_freshness(
            str(usage.get("updatedAt")) if usage.get("updatedAt") else None
        )
        lines = text.splitlines()
        if lines:
            lines[-1] = f"{lines[-1]}  {freshness.status}"
        self.summary.setText("\n".join(lines))
        if self.collapsed and "\n" in self.summary.text():
            new_height = max(self.collapsed_height, 78)
            self.setFixedHeight(new_height)
            self.resize(self.width(), new_height)
        elif self.collapsed:
            self.setFixedHeight(self.collapsed_height)
            self.resize(self.width(), self.collapsed_height)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        hide_action = menu.addAction("Hide")
        refresh_action = menu.addAction("Refresh")
        top_action = QAction("Always on Top", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self.always_on_top)
        menu.addAction(top_action)
        folder_action = menu.addAction("Open Data Folder")
        project_action = menu.addAction("Open Project Folder")
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        chosen = menu.exec(event.globalPos())
        if chosen == hide_action:
            self.hide()
        elif chosen == refresh_action:
            self.refresh_data()
        elif chosen == top_action:
            self.toggle_always_on_top()
        elif chosen == folder_action:
            self.open_data_folder()
        elif chosen == project_action:
            self.open_project_folder()
        elif chosen == exit_action:
            self.request_exit()

    def refresh_data(self) -> None:
        if self.refresh_thread and self.refresh_thread.isRunning():
            return
        self.updated.setText("Refreshing...")
        if self.collapsed:
            self.summary.setText("Refreshing...")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("...")
        self.refresh_thread = RefreshThread(self.project_root, self.config)
        self.refresh_thread.completed.connect(self.load_cache)
        self.refresh_thread.failed.connect(self._refresh_failed)
        self.refresh_thread.finished.connect(self._refresh_finished)
        self.refresh_thread.start()

    def _refresh_failed(self, message: str) -> None:
        self.updated.setText(f"Refresh error: {sanitize_message(message, 120)}")
        if self.collapsed:
            self.summary.setText("Refresh error")

    def _refresh_finished(self) -> None:
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("↻")
        thread = self.refresh_thread
        self.refresh_thread = None
        if thread is not None:
            thread.deleteLater()
        if self.exit_requested:
            self._finish_exit()

    def load_cache(self) -> None:
        usage = read_usage(self.cache_path, create_if_missing=True)
        providers = usage.get("providers", {})
        codex = providers.get("codex", {})
        kimi = providers.get("kimi", {})
        deepseek = providers.get("deepseek", {})
        self.codex_card.update_data(codex)
        self.kimi_card.update_data(kimi)
        self.deepseek_card.update_data(deepseek)
        values = _remaining_values((codex, kimi))
        self.face.setText(_face(min(values) if values else None))
        self.last_updated_at = usage.get("updatedAt")
        self._update_summary()
        self._update_freshness()

    def _update_freshness(self) -> None:
        if self.refresh_thread and self.refresh_thread.isRunning():
            return
        freshness = compute_cache_freshness(
            str(self.last_updated_at) if self.last_updated_at else None
        )
        self.updated.setText(format_updated_with_freshness(self.last_updated_at))
        color = COLOR_DANGER if freshness.status == "Expired" else COLOR_MUTED
        self.updated.setStyleSheet(f"color: {color};")
        if self.collapsed:
            self._update_summary()

    def toggle_always_on_top(self) -> None:
        position = self.pos()
        self.always_on_top = not self.always_on_top
        self._apply_flags()
        self.move(position)
        self.show()
        self._save_state()

    def open_data_folder(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._open_folder(self.cache_path.parent, "data")

    def open_project_folder(self) -> None:
        self._open_folder(self.project_root, "project")

    def _open_folder(self, path: Path, label: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError:
            self.updated.setText(f"Unable to open {label} folder")

    def closeEvent(self, event) -> None:
        self._save_state()
        if self.tray_icon is not None and not self.exit_requested:
            self.hide()
            event.ignore()
            return
        self.request_exit()
        event.accept()

    def show_and_activate(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_and_activate()

    def request_exit(self) -> None:
        if self.exit_requested:
            return
        self.exit_requested = True
        self.timer.stop()
        self.freshness_timer.stop()
        self._save_state()
        self.hide()
        if self.refresh_thread and self.refresh_thread.isRunning():
            self.refresh_thread.requestInterruption()
            return
        self._finish_exit()

    def _finish_exit(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()
        QApplication.quit()

    def _restore_position(self, state: dict[str, Any]) -> None:
        x = state.get("x")
        y = state.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return
        target = QRect(QPoint(x, y), self.size())
        screens = QApplication.screens()
        if any(screen.availableGeometry().intersects(target) for screen in screens):
            self.move(x, y)

    def _save_state(self) -> None:
        try:
            write_ui_state(
                self.state_path,
                {
                    "x": self.x(),
                    "y": self.y(),
                    "always_on_top": self.always_on_top,
                    "collapsed": self.collapsed,
                },
            )
        except OSError:
            pass


def run_widget(project_root: Path | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(not QSystemTrayIcon.isSystemTrayAvailable())
    widget = CodingPlanWidget(project_root)
    widget.show()
    return app.exec()


def _remaining_values(providers: tuple[dict[str, Any], ...]) -> list[int]:
    values: list[int] = []
    for provider in providers:
        for key in ("fiveHour", "weekly"):
            window = provider.get(key, {})
            value = window.get("remainingPercent") if isinstance(window, dict) else None
            if isinstance(value, (int, float)):
                values.append(round(value))
    return values


def _format_compact_summary(providers: dict[str, Any], show_reset: bool = True) -> str:
    codex = providers.get("codex", {})
    kimi = providers.get("kimi", {})
    deepseek = providers.get("deepseek", {})

    def pct(window: Any) -> str:
        if isinstance(window, dict) and window.get("remainingPercent") is not None:
            return f"{round(window['remainingPercent'])}"
        return "--"

    def provider_summary(provider: dict[str, Any], prefix: str) -> str:
        if provider.get("status") != "ok":
            return f"{prefix} offline"
        five = provider.get("fiveHour", {})
        weekly = provider.get("weekly", {})
        return f"{prefix} {pct(five)}/{pct(weekly)}"

    parts = [
        provider_summary(codex, "C"),
        provider_summary(kimi, "K"),
    ]

    balance = deepseek.get("balance") or {}
    if deepseek.get("status") == "ok" and balance.get("total") is not None:
        parts.append(f"DS {float(balance['total']):.2f}")
    else:
        parts.append("DS offline")

    summary = "  ".join(parts)

    if not show_reset:
        return summary

    reset_parts = []
    for label, provider in (("C", codex), ("K", kimi)):
        if provider.get("status") != "ok":
            continue
        five = provider.get("fiveHour", {})
        if isinstance(five, dict):
            reset = format_reset_time(five.get("resetAt"))
            if reset != "--":
                reset_parts.append(f"{label}{reset}")
    if not reset_parts:
        return summary
    return f"{summary}\nR {' '.join(reset_parts)}"


def _summary_pct(window: Any) -> str:
    if isinstance(window, dict) and window.get("remainingPercent") is not None:
        return f"{round(window['remainingPercent'])}"
    return "--"


def _face(value: int | None) -> str:
    if value is None:
        return "(?_?)"
    if value >= 50:
        return "(^_^)"
    if value >= 30:
        return "(-_-)"
    if value >= 15:
        return "(>_<)"
    return "(x_x)"


def _quota_color(value: Any, status: str) -> str:
    if status != "ok" or not isinstance(value, (int, float)):
        return COLOR_MUTED
    if value >= 30:
        return COLOR_NORMAL
    if value >= 15:
        return COLOR_WARNING
    return COLOR_DANGER
