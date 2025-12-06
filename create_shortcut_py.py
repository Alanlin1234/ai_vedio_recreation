#!/usr/bin/env python3
"""
使用Python创建ComfyUI桌面快捷方式
"""

import win32com.client

# 创建WScript.Shell对象
wsh = win32com.client.Dispatch('WScript.Shell')

# 设置桌面路径（使用原始字符串）
desktop_path = r'C:\Users\林\Desktop'

# 创建快捷方式对象
shortcut_path = f'{desktop_path}\ComfyUI.lnk'
shortcut = wsh.CreateShortcut(shortcut_path)

# 设置快捷方式属性
shortcut.TargetPath = r'C:\Program Files\Python310\python.exe'  # Python解释器路径
shortcut.Arguments = 'main.py --lowvram'  # 启动参数
shortcut.WorkingDirectory = r'D:\ComfyUI-master'  # 工作目录
shortcut.Description = '启动ComfyUI'  # 快捷方式描述

# 保存快捷方式
shortcut.Save()

print(f'✅ ComfyUI快捷方式已创建到桌面: {shortcut_path}')
