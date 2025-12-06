# Python虚拟环境配置与使用指南

## 1. 虚拟环境概述

虚拟环境是Python项目的最佳实践，用于：
- 隔离项目依赖，避免版本冲突
- 便于团队协作，确保环境一致性
- 简化部署流程
- 减少全局依赖污染

本项目将使用Python内置的`venv`模块创建虚拟环境。

## 2. 环境要求

- Python 3.10+（项目要求）
- pip 23.0+（推荐）
- Visual Studio Code（可选，推荐）

## 3. 创建虚拟环境

### 3.1 Windows

```powershell
# 打开命令提示符或PowerShell
cd d:\ai-agent-comfy
python -m venv venv
```

### 3.2 macOS/Linux

```bash
# 打开终端
cd /path/to/ai-agent-comfy
python3 -m venv venv
```

## 4. 激活虚拟环境

### 4.1 Windows - 命令提示符

```cmd
venv\Scripts\activate
```

### 4.2 Windows - PowerShell

**首次激活需设置执行策略：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**激活虚拟环境：**
```powershell
venv\Scripts\Activate.ps1
```

### 4.3 macOS/Linux

```bash
source venv/bin/activate
```

**激活成功标志：**
- 命令提示符前出现 `(venv)` 前缀
- Windows: `(venv) C:\ai-agent-comfy>`
- macOS/Linux: `(venv) user@hostname:~/ai-agent-comfy$`

## 5. 安装项目依赖

### 5.1 升级pip

```bash
pip install --upgrade pip
```

### 5.2 安装后端依赖

```bash
pip install -r backend/requirements.txt
```

### 5.3 安装爬虫依赖

```bash
pip install -r backend/crawler/Douyin_TikTok_Download_API-main/requirements.txt
```

## 6. VSCode配置

### 6.1 设置Python解释器

1. 打开项目文件夹：`File > Open Folder`
2. 按下 `Ctrl+Shift+P` (Windows/Linux) 或 `Cmd+Shift+P` (macOS)
3. 输入并选择 `Python: Select Interpreter`
4. 选择虚拟环境的Python可执行文件：
   - Windows: `venv\Scripts\python.exe`
   - macOS/Linux: `venv/bin/python`

### 6.2 配置settings.json

创建或修改 `.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
        "${workspaceFolder}/backend"
    ],
    "terminal.integrated.env.windows": {
        "PYTHONPATH": "${workspaceFolder}/backend"
    },
    "terminal.integrated.env.linux": {
        "PYTHONPATH": "${workspaceFolder}/backend"
    },
    "terminal.integrated.env.osx": {
        "PYTHONPATH": "${workspaceFolder}/backend"
    }
}
```

### 6.3 配置launch.json

创建 `.vscode/launch.json` 用于调试：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "启动后端服务",
            "type": "python",
            "request": "launch",
            "program": "backend/run.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend"
            }
        },
        {
            "name": "运行视频生成脚本",
            "type": "python",
            "request": "launch",
            "program": "generate_video.py",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend"
            }
        }
    ]
}
```

## 7. 验证虚拟环境配置

### 7.1 检查Python路径

```bash
# Windows
where python

# macOS/Linux
which python
```

**预期输出：**
- Windows: `d:\ai-agent-comfy\venv\Scripts\python.exe`
- macOS/Linux: `/path/to/ai-agent-comfy/venv/bin/python`

### 7.2 检查已安装包

```bash
pip list
```

**预期输出：**
- 包含 `fastapi`, `uvicorn`, `aiohttp` 等项目依赖
- 不包含全局安装的无关包

### 7.3 测试模块导入

```bash
python -c "import fastapi; import aiohttp; import moviepy; print('所有依赖导入成功')"
```

**预期输出：** `所有依赖导入成功`

### 7.4 运行项目测试

```bash
python -m backend.tests.test_video_generation
```

**预期输出：** 测试通过或明确的错误信息（非依赖问题）

## 8. 常见操作

### 8.1 退出虚拟环境

```bash
deactivate
```

### 8.2 重新激活虚拟环境

参考第4节的激活命令

### 8.3 安装新依赖

```bash
pip install <package-name>
```

### 8.4 更新依赖

```bash
pip install --upgrade <package-name>
```

### 8.5 冻结依赖

```bash
pip freeze > requirements.txt
```

## 9. 跨平台注意事项

### 9.1 Windows

- PowerShell执行策略问题
- 路径分隔符使用 `\`
- 虚拟环境脚本在 `Scripts` 目录

### 9.2 macOS/Linux

- 路径分隔符使用 `/`
- 虚拟环境脚本在 `bin` 目录
- 需要 `source` 命令激活
- 可能需要安装 `python3-venv` 系统包

### 9.3 VSCode跨平台配置

- 解释器路径自动检测
- 环境变量配置区分OS
- 调试配置通用

## 10. 故障排除

### 10.1 依赖安装失败

- 检查Python版本
- 升级pip
- 检查网络连接
- 尝试使用国内镜像：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

### 10.2 VSCode无法识别虚拟环境

- 重启VSCode
- 手动指定解释器路径
- 检查 `.vscode/settings.json` 配置

### 10.3 模块导入错误

- 检查PYTHONPATH环境变量
- 确保虚拟环境已激活
- 检查依赖是否正确安装

## 11. 最佳实践

- 始终在虚拟环境中开发
- 定期更新依赖
- 将 `venv` 目录添加到 `.gitignore`
- 使用 `requirements.txt` 管理依赖
- 为不同项目创建独立虚拟环境

## 12. 总结

通过以上步骤，您已成功配置了Python虚拟环境，实现了项目依赖的隔离管理。虚拟环境将确保项目在不同开发环境中的一致性，简化部署流程，并减少依赖冲突问题。

**下一步：**
1. 启动后端服务：`python backend/run.py`
2. 运行视频生成脚本：`python generate_video.py`
3. 在VSCode中调试项目

祝您开发愉快！