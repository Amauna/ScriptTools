' 🌊 GA4 Data Analyst Tools Suite - Smart Launcher
' Launches the GUI using the project venv when available

Const WINDOW_HIDDEN = 0
Const WINDOW_NORMAL = 1

Dim objShell, objFSO, scriptDir, mainPy
Dim interpreters, i, exePath, windowStyle, launched

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
mainPy = scriptDir & "\main.py"

If Not objFSO.FileExists(mainPy) Then
    MsgBox "Error: main.py not found in:" & vbCrLf & scriptDir, vbCritical, "GA4 Tools Launcher"
    WScript.Quit 1
End If

' Build the preferred interpreter list
' Each entry = Array(path, windowStyle)
Set interpreters = CreateObject("System.Collections.ArrayList")

exePath = scriptDir & "\venv\Scripts\pythonw.exe"
If objFSO.FileExists(exePath) Then interpreters.Add Array(exePath, WINDOW_HIDDEN)

exePath = scriptDir & "\venv\Scripts\python.exe"
If objFSO.FileExists(exePath) Then interpreters.Add Array(exePath, WINDOW_NORMAL)

interpreters.Add Array("pythonw", WINDOW_HIDDEN)
interpreters.Add Array("python", WINDOW_NORMAL)

launched = False

For i = 0 To interpreters.Count - 1
    exePath = interpreters(i)(0)
    windowStyle = interpreters(i)(1)

    If Left(exePath, 1) = "p" Then
        ' Assume PATH-based executable (python / pythonw)
        objShell.CurrentDirectory = scriptDir
        On Error Resume Next
        objShell.Run exePath & " """ & mainPy & """", windowStyle, False
        If Err.Number = 0 Then
            launched = True
            Exit For
        End If
        Err.Clear
        On Error GoTo 0
    ElseIf objFSO.FileExists(exePath) Then
        objShell.CurrentDirectory = scriptDir
        On Error Resume Next
        objShell.Run """" & exePath & """ """ & mainPy & """", windowStyle, False
        If Err.Number = 0 Then
            launched = True
            Exit For
        End If
        Err.Clear
        On Error GoTo 0
    End If
Next

If Not launched Then
    MsgBox "Unable to launch the GA4 Tools Suite." & vbCrLf & _
           "Checked interpreters:" & vbCrLf & _
           "  • venv\Scripts\pythonw.exe" & vbCrLf & _
           "  • venv\Scripts\python.exe" & vbCrLf & _
           "  • pythonw" & vbCrLf & _
           "  • python" & vbCrLf & vbCrLf & _
           "Ensure your virtual environment is created and Python is installed.", _
           vbCritical, "GA4 Tools Launcher"
    WScript.Quit 1
End If

Set objShell = Nothing
Set objFSO = Nothing

