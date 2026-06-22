Option Explicit

Dim shell, fso, projectDir, pythonw, python, mainpy, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = fso.BuildPath(projectDir, "codingplan\Scripts\pythonw.exe")
python = fso.BuildPath(projectDir, "codingplan\Scripts\python.exe")
mainpy = fso.BuildPath(projectDir, "main.py")

If Not fso.FileExists(pythonw) Then
    MsgBox "codingplan virtual environment not found. Please run setup_env.bat first.", vbExclamation, "CodingPlanWidget"
    WScript.Quit 1
End If

If Not fso.FileExists(mainpy) Then
    MsgBox "main.py was not found in the project folder.", vbExclamation, "CodingPlanWidget"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectDir
cmd = """" & pythonw & """ """ & mainpy & """ widget"
On Error Resume Next
shell.Run cmd, 0, False
If Err.Number <> 0 Then
    Err.Clear
    If Not fso.FileExists(python) Then
        On Error GoTo 0
        MsgBox "Unable to start the codingplan virtual environment. Please run setup_env.bat first.", vbExclamation, "CodingPlanWidget"
        WScript.Quit 1
    End If
    cmd = """" & python & """ """ & mainpy & """ widget"
    shell.Run cmd, 0, False
End If
If Err.Number <> 0 Then
    On Error GoTo 0
    MsgBox "CodingPlanWidget could not be started. Use start_widget.bat for diagnostics.", vbExclamation, "CodingPlanWidget"
    WScript.Quit 1
End If
On Error GoTo 0
