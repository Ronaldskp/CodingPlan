# CodingPlanWidget icon

Place a Windows icon at:

```text
assets/coding_plan.ico
```

`create_desktop_shortcut.ps1` automatically uses this file when creating or
updating the desktop shortcut. If the file is absent, Windows uses its default
shortcut icon. The application also falls back to a locally generated PySide6
icon at runtime.

You may replace `coding_plan.ico` with your own `.ico` file and rerun the
shortcut creation script. No icon is downloaded from the network.
