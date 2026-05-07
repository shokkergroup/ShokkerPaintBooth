Option Explicit

Dim fso, shell, root, appDir, electronCmd, command

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

root = fso.GetParentFolderName(WScript.ScriptFullName)
appDir = fso.BuildPath(root, "electron-app")
electronCmd = fso.BuildPath(appDir, "node_modules\.bin\electron.cmd")

If Not fso.FolderExists(appDir) Then
  MsgBox "Could not find the SPB electron-app folder next to this launcher.", vbExclamation, "SHOKKER Finish Viewer"
  WScript.Quit 1
End If

If fso.FileExists(electronCmd) Then
  command = "cmd /c cd /d """ & appDir & """ && """ & electronCmd & """ . --open-finish-viewer"
Else
  command = "cmd /c cd /d """ & appDir & """ && npm start -- --open-finish-viewer"
End If

shell.Run command, 0, False
