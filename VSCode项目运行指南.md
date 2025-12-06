# VSCode项目运行详细指南

## 1. 项目结构概述

本项目是一个视频生成系统，主要包含以下核心组件：
- **backend/**: 后端服务，包含API、代理和视频生成逻辑
- **backend/crawler/**: 抖音/TikTok下载爬虫
- **venv/**: Python虚拟环境（将在后续步骤创建）
- **FLUX_GGUF_WORKFLOW .json**: ComfyUI工作流配置
- **generate_video.py**: 视频生成主脚本

## 2. 环境准备

### 2.1 VSCode基本设置

1. **安装VSCode**: 确保已安装最新版本的VSCode
2. **安装Python扩展**: 
   - 在VSCode扩展商店搜索"Python"并安装
   - 同时安装"Pylance"扩展以获得更好的代码智能提示
3. **安装DotENV扩展**: 搜索"DotENV"并安装，用于加载环境变量

### 2.2 创建和激活虚拟环境

1. **打开VSCode终端**: 
   - 点击顶部菜单 `终端 > 新建终端`
   - 确保终端类型为`PowerShell`或`Command Prompt`

2. **创建虚拟环境**: 
   ```bash
   cd d:\ai-agent-comfy
   python -m venv venv
   ```

3. **激活虚拟环境**: 
   - **PowerShell**: `.\venv\Scripts\Activate.ps1`
   - **Command Prompt**: `.\venv\Scripts\activate.bat`
   - 激活后终端左侧会显示`(venv)`

4. **升级pip**: 
   ```bash
   python -m pip install --upgrade pip
   ```

## 3. 依赖安装

### 3.1 安装后端依赖

```bash
cd d:\ai-agent-comfy\backend
pip install -r requirements.txt
```

### 3.2 安装爬虫依赖

```bash
cd d:\ai-agent-comfy\backend\crawler\Douyin_TikTok_Download_API-main
pip install -r requirements.txt
```

> **注意**: 安装爬虫依赖时可能会导致部分包版本降级，这是正常现象，因为爬虫依赖有特定版本要求，虚拟环境会自动处理这些冲突。

## 4. 环境变量配置

### 4.1 创建.env文件

1. 在项目根目录创建`.env`文件
2. 复制以下内容到`.env`文件，并根据实际情况填写API密钥：

```env
# API密钥配置
DASHSCOPE_API_KEY=your_dashscope_api_key_here
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# 数据库配置（如果需要使用MySQL）
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DB=video_agent

# ComfyUI配置
COMFYUI_URL=http://127.0.0.1:8188

# 输出目录配置
OUTPUT_DIR=output/videos
```

### 4.2 配置VSCode加载.env文件

1. 确保已安装"DotENV"扩展
2. 在VSCode中打开项目根目录
3. VSCode会自动识别并加载`.env`文件中的环境变量

## 5. ComfyUI配置检查

### 5.1 确保ComfyUI已安装

- 确认ComfyUI已安装在本地，常见路径：
  - `C:\ComfyUI`
  - `D:\ComfyUI`
  - `%USERPROFILE%\ComfyUI`

### 5.2 模型文件检查

1. 打开ComfyUI安装目录
2. 检查 `models/checkpoints/` 目录，确保包含以下模型文件：
   - Flux模型（如`flux_dev.safetensors`）
   - Wan2.1模型（如`wan_2.1.safetensors`和`wan_2.1_vae.safetensors`）

### 5.3 启动ComfyUI

- **Windows**: 运行ComfyUI目录下的 `run_nvidia_gpu.bat`（GPU）或 `run_cpu.bat`（CPU）
- **命令行启动**: 
  ```bash
  cd path/to/ComfyUI
  python main.py
  ```

- **验证启动成功**: 
  - 等待30秒-1分钟，直到看到"Server started at http://127.0.0.1:8188"提示
  - 访问 http://127.0.0.1:8188 确认服务运行

## 6. 启动项目流程

### 6.1 验证ComfyUI连接

在VSCode终端中运行：

```bash
cd d:\ai-agent-comfy
python check_comfyui.py
```

如果输出显示"✅ ComfyUI服务正常响应"，则继续下一步。

### 6.2 启动后端服务（可选）

如果需要使用API服务，可启动后端：

```bash
cd d:\ai-agent-comfy\backend
python run.py
```

后端服务将在 http://0.0.0.0:5000 启动。

### 6.3 运行视频生成脚本

这是项目的核心功能，生成视频：

```bash
cd d:\ai-agent-comfy
python generate_video.py
```

## 7. VSCode调试配置

### 7.1 配置调试器

1. 点击VSCode左侧的调试图标（或按`Ctrl+Shift+D`）
2. 点击"创建launch.json文件"
3. 选择"Python"环境
4. 选择"Python文件"模板
5. 修改launch.json为：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "生成视频",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/generate_video.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "envFile": "${workspaceFolder}/.env"
        },
        {
            "name": "启动后端",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/run.py",
            "console": "integratedTerminal",
            "justMyCode": true,
            "envFile": "${workspaceFolder}/.env"
        }
    ]
}
```

6. 保存后，可直接点击调试按钮启动对应服务

## 8. 常见问题及解决方案

### 8.1 ComfyUI连接失败

**问题**: `check_comfyui.py` 输出"❌ ComfyUI服务未响应"

**解决方案**:
- 确认ComfyUI已启动
- 检查ComfyUI端口是否为8188（默认）
- 检查防火墙是否阻止了连接
- 尝试重启ComfyUI

### 8.2 端口冲突

**问题**: "Address already in use: 127.0.0.1:8188"

**解决方案**:
- 查找占用端口的进程：
  ```bash
  netstat -ano | findstr :8188
  ```
- 终止占用端口的进程：
  ```bash
  taskkill /PID <进程ID> /F
  ```
- 或修改ComfyUI启动端口：
  ```bash
  python main.py --port 8189
  ```
- 同时修改`.env`文件中的`COMFYUI_URL`为新端口

### 8.3 缺少依赖包

**问题**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
- 确保虚拟环境已激活
- 重新安装缺失的依赖：
  ```bash
  pip install xxx
  ```
- 或重新安装所有依赖：
  ```bash
  pip install -r backend/requirements.txt
  pip install -r backend/crawler/Douyin_TikTok_Download_API-main/requirements.txt
  ```

### 8.4 模型文件未找到

**问题**: ComfyUI报错"Model file not found"

**解决方案**:
- 确认模型文件已正确放置在 `ComfyUI/models/checkpoints/` 目录
- 检查模型文件名是否与工作流配置中的名称一致
- 重新下载缺失的模型文件

### 8.5 API密钥错误

**问题**: "Invalid API key"或"API key not provided"

**解决方案**:
- 检查`.env`文件中的API密钥是否正确
- 确保API密钥格式正确，没有多余的空格或引号
- 确认API服务是否可用（如网络连接正常）

### 8.6 生成超时

**问题**: 视频生成过程中出现"TimeoutError"

**解决方案**:
- 检查ComfyUI是否正常运行
- 增加超时时间：修改`config.py`中的`AGENT_TIMEOUT`值
- 减少生成视频的时长或分辨率

## 9. 项目运行流程总结

1. **启动ComfyUI** → 2. **激活虚拟环境** → 3. **安装依赖** → 4. **配置环境变量** → 5. **验证ComfyUI连接** → 6. **运行视频生成脚本**

## 10. 开发建议

1. **使用虚拟环境**: 始终在虚拟环境中运行项目，避免依赖冲突
2. **定期更新依赖**: 定期运行`pip install --upgrade -r requirements.txt`更新依赖
3. **查看日志**: 生成过程中的详细日志保存在`logs/`目录，可用于调试
4. **调试模式**: 使用VSCode调试功能逐步调试代码
5. **ComfyUI界面**: 可在ComfyUI界面中实时查看图像生成状态

## 11. 联系方式

如果遇到无法解决的问题，请联系项目维护者或查看项目文档。

---

**祝您使用愉快！** 🎉