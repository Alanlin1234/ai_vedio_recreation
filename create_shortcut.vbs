' 创建ComfyUI桌面快捷方式
Set WshShell = WScript.CreateObject("WScript.Shell")
DesktopPath = "C:\Users\林\Desktop"
Set Shortcut = WshShell.CreateShortcut(DesktopPath & "\ComfyUI.lnk")
Shortcut.TargetPath = "C:\Program Files\Python310\python.exe"
Shortcut.Arguments = "main.py --lowvram"
Shortcut.WorkingDirectory = "D:\ComfyUI-master"
Shortcut.Description = "启动ComfyUI"
Shortcut.Save()
WScript.Echo "ComfyUI快捷方式已创建到桌面"
