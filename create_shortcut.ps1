# 创建ComfyUI桌面快捷方式
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\ComfyUI.lnk')
$Shortcut.TargetPath = 'C:\Program Files\Python310\python.exe'
$Shortcut.Arguments = 'main.py --lowvram'
$Shortcut.WorkingDirectory = 'D:\ComfyUI-master'
$Shortcut.Description = '启动ComfyUI'
$Shortcut.Save()
Write-Host "✅ ComfyUI快捷方式已创建到桌面"
