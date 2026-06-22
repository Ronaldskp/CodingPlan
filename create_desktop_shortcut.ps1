$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "CodingPlanWidget.lnk"
$TargetPath = Join-Path $ProjectDir "start_widget_silent.vbs"
$IconPath = Join-Path $ProjectDir "assets\coding_plan.ico"

if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "Silent launcher not found: $TargetPath"
}

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "Coding Plan Widget"
if (Test-Path -LiteralPath $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()

Write-Host "Desktop shortcut created: $ShortcutPath"
