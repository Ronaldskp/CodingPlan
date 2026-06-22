$ErrorActionPreference = "Stop"

$ProjectDir = "E:\Ronald\CodingPlanWidget"
$ReleaseDir = Join-Path $ProjectDir "release\CodingPlanWidget"
$ExePath = Join-Path $ReleaseDir "CodingPlanWidget.exe"
$IconPath = Join-Path $ReleaseDir "assets\coding_plan.ico"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "CodingPlanWidget.lnk"

if (!(Test-Path -LiteralPath $ExePath -PathType Leaf)) {
    Write-Host "[ERROR] EXE not found: $ExePath"
    exit 1
}

if (!(Test-Path -LiteralPath $IconPath -PathType Leaf)) {
    Write-Host "[ERROR] Icon not found: $IconPath"
    exit 1
}

$WScriptShell = New-Object -ComObject WScript.Shell
$OldTarget = "(shortcut did not exist)"

if (Test-Path -LiteralPath $ShortcutPath) {
    try {
        $OldShortcut = $WScriptShell.CreateShortcut($ShortcutPath)
        $OldTarget = $OldShortcut.TargetPath
    }
    catch {
        $OldTarget = "(existing shortcut could not be inspected)"
    }
}

Write-Host "[INFO] Existing shortcut target:"
Write-Host "       $OldTarget"

$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $ReleaseDir
$Shortcut.Description = "Coding Plan Widget"
$Shortcut.IconLocation = "$IconPath,0"
$Shortcut.Save()

$SavedShortcut = $WScriptShell.CreateShortcut($ShortcutPath)
Write-Host "[OK] Desktop shortcut created/updated:"
Write-Host "     $ShortcutPath"
Write-Host "[OK] New shortcut target:"
Write-Host "     $($SavedShortcut.TargetPath)"
Write-Host "[OK] Working directory:"
Write-Host "     $($SavedShortcut.WorkingDirectory)"
Write-Host "[OK] Icon:"
Write-Host "     $($SavedShortcut.IconLocation)"
