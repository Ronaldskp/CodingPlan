# Development Log

## 2026-06-24 — V1.5 Reset Time Display

- 新增 `core/time_display.py`，统一解析 ISO 8601、短格式 `MM-DD HH:MM` 和时间-only `HH:MM` 的重置时间字符串。
- `core/normalizer.py` 保留 Kimi `reset_at` 字段；Codex 支持 `reset_at`、`resetAt`、`resetsAt`、`resets_at` 字段别名。
- `core/collector.py` 与 `config.yaml` 新增 `show_reset_times`、`reset_display_mode`、`compact_summary_show_reset` 配置项。
- CLI `status` / `refresh` 在 Codex/Kimi 额度行末尾输出 `reset <time>`。
- UI 展开卡片改为三列布局（类型、额度、重置时间），错误/离线保持短文案。
- UI 折叠摘要可选显示第二行 `R C18:44 K18:44    Fresh`。
- 新增测试：`tests/test_time_display.py`、`tests/test_reset_normalization.py`、`tests/test_ui_summary_format.py`。
- 新增 `docs/ui_notes.md`，更新 `README.md`、`docs/development_log.md`、`docs/packaging_notes.md`、`docs/troubleshooting.md`。

## 2026-06-18 — V1 baseline

- 建立 provider/core/ui 分层、统一 usage schema、原子缓存和集中脱敏。
- Codex 支持现有 ChatGPT OAuth usage 路径及 custom command。
- Kimi 支持 `kimi-usage --json`。
- PySide6 悬浮窗支持拖动、置顶、手动和定时刷新。
- Codex 与 Kimi 的真实 5H/weekly 数据均已在本机验证。

## 2026-06-18 — V1.1 stabilization

- 新增项目本地 `.env` 与 `.env.example`，所有 CLI/UI 命令通过统一配置入口加载。
- doctor 新增 `.env file: found/missing` 和两个 Kimi key 的 `set/not set` 检查。
- 子进程继承 `.env` 加载后的环境，并把当前 Python 的 Scripts 目录加入命令查找路径。
- Kimi 解析按真实 `Weekly Usage`、`5h Limit` label 和 percent/used、remaining、reset_at 字段固化。
- UI 后台刷新增加 `Refreshing...` 与非致命失败显示。
- 新增 `data/ui_state.json`，保存窗口位置和 Always on Top 状态。
- 修正 warning/danger 阈值，缓存缺失或损坏时继续 fallback。
- 新增 `start_widget.bat`、`setup_env.bat`、`.gitignore`。
- 新增 security、Kimi parser、cache、normalizer/collector 测试。
- 更新 README 与 provider 文档，明确安全边界和 endpoint 风险。

## 2026-06-22 — V1.4.1 Codex SSL/network resilience + widget collapse/refresh

- 增强 `providers/codex_provider.py` 的 SSL/timeout/proxy/network 错误捕获，统一返回短文案（`SSL/network error`、`Network timeout`、`Network error`），避免 UI 卡片塞满 traceback。
- `core/collector.py` 在 provider 刷新失败时，自动用上一次缓存的 `fiveHour`/`weekly`/`balance`/`today` 数值回填，避免 UI 直接显示 `--`；回填后状态保持 `offline`/`error`，message 改为 `Last value shown; refresh failed.`。
- 新增 `data/ui_state.json` 的 `collapsed` 字段；`core/ui_state.py` 读写时保留未知字段，旧版本缺少 `collapsed` 时默认 `false`。
- `config.yaml` 的 `ui` 区增加 `collapsible`、`collapsed_height`、`expanded_height`、`click_title_to_toggle_collapse` 配置。
- `ui/widget.py` 增加标题栏刷新按钮 `↻` 和折叠按钮 `˄/˅`；支持点击标题栏区域切换折叠/展开；折叠后显示单行摘要并保留拖动、右键菜单、手动刷新、托盘功能。
- 折叠态把 Fresh/Stale/Expired 合并进摘要，64px 高度内不再裁切；刷新时摘要显示 `Refreshing...`。
- Provider 使用旧值回填时，展开卡片的对应数值行显示 `stale`。
- `core/doctor.py` 增加 Codex usage source 和网络诊断提示。
- 新增测试：`tests/test_ui_state_collapse.py`、`tests/test_provider_stale_fallback.py`、`tests/test_codex_error_messages.py`。
- 新增 `docs/troubleshooting.md`，记录 Codex SSL 错误排查方式。
- EXE 打包方式保持不变，`.env` 仍然外置，release 中仍不包含真实 `.env`。

## 安全边界

- 不记录 API Key、Bearer token、cookie 或 auth.json 内容。
- `usage.json` 写入前递归移除敏感字段并脱敏字符串。
- Kimi schema 异常诊断只记录字段名和类型。
- `.env` 仅包含空占位，并由 `.gitignore` 排除。

## V1.1 verification

- `python -m compileall -q main.py core providers ui tests` 通过。
- `python -m pytest -q`：18 passed。
- `python main.py doctor`、`refresh`、`status` 通过且无 traceback。
- Codex OAuth provider 再次真实返回 5H 与 weekly 数据。
- Kimi 真实 JSON 固定样例解析测试通过；验收时 `.env` 按安全要求保持空值，因此 live refresh 正确返回 `unsupported / credentials not configured`。
- PySide6 离屏启动、后台刷新、关闭和 UI state 写入通过。
- `setup_env.bat` 命令行执行通过。
- `start_widget.bat` 已确认能拉起 `codingplan\Scripts\python.exe` 的 widget 进程。

## 2026-06-18 — V1.2 daily desktop release

- 新增 `start_widget_silent.vbs`，通过虚拟环境 `pythonw.exe` 无黑窗口启动。
- 新增桌面快捷方式创建脚本、可替换本地图标和调试/日常双启动路径。
- 新增缓存 Fresh / Stale / Expired / Unknown 计算，CLI 与 UI 共用。
- 新增系统托盘 Show、Hide、Refresh、打开目录、置顶切换和 Exit。
- 窗口关闭默认隐藏到托盘；Exit 时后台刷新受 provider timeout 约束。
- 新增统一 `provider.timeout_seconds: 15`，覆盖 Kimi/Codex 子进程和 Codex 网络请求。
- 新增 `requirements.lock.txt`，用于复现当前验证环境。
- 新增 freshness、桌面启动器和 timeout 配置测试。

## 2026-06-22 — V1.3 DeepSeek balance provider

- 新增 `providers/deepseek_provider.py`，使用 `urllib.request` 调用 DeepSeek 官方余额接口。
- 新增 `core/deepseek_daily.py`，管理本地每日余额快照和 `todaySpend` 估算。
- 扩展 `core/normalizer.py` 支持 DeepSeek `balance` / `today` schema，Codex/Kimi 结构保持兼容。
- `core/collector.py` 并行采集三个 provider，DeepSeek 失败不影响 Codex/Kimi。
- `core/cache.py` 初始 usage 包含 deepseek；`core/doctor.py` 增加 DEEPSEEK_API_KEY 和快照检查。
- CLI `refresh` / `status` 输出 DeepSeek 余额和今日估算消费（ASCII 格式）。
- UI 新增 DeepSeek 卡片，默认高度从 220 调整为 300；托盘、置顶、位置恢复保持不变。
- 新增 `tests/test_deepseek_provider_parser.py`、`test_deepseek_daily_snapshot.py`、
  `test_deepseek_security.py`；原有 Codex/Kimi 测试全部通过。
- 更新 `README.md`、`.env.example`、`config.yaml`、`.gitignore`，新增
  `docs/deepseek_provider_notes.md`。
- 安全：`.env` 中仅追加 `DEEPSEEK_API_KEY=` 占位符，未覆盖已有 Kimi key；
  `usage.json` 与 `deepseek_daily.json` 写入前经过 `sanitize_data` 脱敏。

## 2026-06-22 — V1.4 PyInstaller EXE 打包

- 新增 `core/paths.py`，统一源码运行与 EXE 运行时的路径解析。
- 新增 `app_launcher.py` 作为 PyInstaller GUI 入口。
- `main.py` 支持 `main(argv=None)`，CLI 行为不变。
- `core/collector.py`、`core/doctor.py`、`ui/widget.py`、`providers/kimi_provider.py` 迁移到 `core.paths`。
- 新增 `CodingPlanWidget.spec`（onedir, noconsole, icon）。
- 新增 `build_exe.bat` 一键打包脚本和 `scripts/generate_release_files.py`。
- `requirements.txt` / `requirements.lock.txt` 增加 PyInstaller。
- 新增 `tests/test_paths.py` 和 `tests/test_release_safety.py`。
- 更新 `README.md`，新增 `docs/packaging_notes.md`。
- Release 目录只包含 `.env.example`、`config.yaml`、`assets/coding_plan.ico` 和空 `data/`，不包含真实 `.env` 或缓存数据。
