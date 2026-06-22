"""Generate data placeholders and README_RELEASE.md for the release package."""

from __future__ import annotations

import sys
from pathlib import Path


def write_release_files(root: Path) -> None:
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    # Ensure the release template does not ship runtime caches.
    for forbidden in ("usage.json", "ui_state.json", "deepseek_daily.json"):
        (data_dir / forbidden).unlink(missing_ok=True)
    (data_dir / ".gitkeep").write_text("", encoding="utf-8")
    (data_dir / "README.md").write_text(
        "# Data Directory\n\n"
        "This folder holds runtime data created by CodingPlanWidget:\n"
        "  - usage.json\n"
        "  - ui_state.json\n"
        "  - deepseek_daily.json\n\n"
        "Do NOT place your .env or auth.json here.\n",
        encoding="utf-8",
    )
    source_readme = Path(__file__).resolve().parent.parent / "README_RELEASE.md"
    (root / "README_RELEASE.md").write_text(
        source_readme.read_text(encoding="utf-8"),
        encoding="utf-8",
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: generate_release_files.py <release_root>", file=sys.stderr)
        raise SystemExit(1)
    write_release_files(Path(sys.argv[1]))
    print("Release files generated.")
