' 🌊 GA4 Data Analyst Tools Suite - Silent Launcher
' Double-click this file to launch the gorgeous PySide6 GUI! 💙✨

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory where this script is located
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Build full path to main.py
strMainPy = strScriptPath & "\main.py"

' Check if main.py exists
If Not objFSO.FileExists(strMainPy) Then
    MsgBox "Error: main.py not found in:" & vbCrLf & strScriptPath, vbCritical, "GA4 Tools Launcher"
    WScript.Quit
End If

' Change to the script directory
objShell.CurrentDirectory = strScriptPath

' Launch with pythonw (windowless Python - no console!)
On Error Resume Next
Err.Clear

' Try pythonw first (clean, no terminal)
objShell.Run "pythonw """ & strMainPy & """", 0, False

If Err.Number <> 0 Then
    ' If pythonw fails, try regular python (will show terminal for debugging)
    Err.Clear
    objShell.Run "python """ & strMainPy & """", 1, False
    
    If Err.Number <> 0 Then
        ' If both fail, show error
        MsgBox "Error: Could not launch Python." & vbCrLf & vbCrLf & _
               "Please make sure Python is installed and added to PATH.", _
               vbCritical, "GA4 Tools Launcher"
    End If
End If

On Error GoTo 0

Set objShell = Nothing
Set objFSO = Nothing

