# 完整环境库列表（用于运行run_complete_workflow.py）

## 1. 系统级依赖

这些是必需的外部软件，需要先安装：

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install -y ffmpeg mysql-server git curl

# CentOS/RHEL系统
sudo dnf update
sudo dnf install -y ffmpeg mysql-server git curl

# 使用conda安装FFmpeg（推荐，版本可控）
conda install -c conda-forge ffmpeg -y
```

## 2. Python包依赖

### 2.1 核心依赖

这些是运行`run_complete_workflow.py`必需的Python包：

```bash
pip install -r backend/requirements.txt
```

### 2.2 缺失的依赖（需要额外安装）

通过代码分析，发现以下依赖在requirements.txt中缺失但在代码中使用：

```bash
# Flask相关依赖
pip install flask flask-cors flask-sqlalchemy

# 数据库依赖
pip install sqlalchemy pymysql

# HTTP客户端
pip install httpx

# 其他依赖
pip install aiohttp aiofiles
```

## 3. 一次性完整安装命令

### 3.1 使用pip一次性安装所有依赖

```bash
# 确保在项目根目录下执行
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql httpx aiohttp aiofiles -r backend/requirements.txt
```

### 3.2 使用conda创建完整环境

```bash
# 创建名为video_agent的conda环境
conda create -n video_agent python=3.10 -y

# 激活环境
conda activate video_agent

# 安装系统依赖
conda install -c conda-forge ffmpeg -y

# 安装Python依赖
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql httpx aiohttp aiofiles -r backend/requirements.txt
```

## 4. 必需的服务

### 4.1 启动MySQL服务

```bash
# Ubuntu/Debian系统
sudo systemctl start mysql
sudo systemctl enable mysql

# CentOS/RHEL系统
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 设置MySQL根密码（首次安装时）
sudo mysql_secure_installation

# 创建数据库
sudo mysql -u root -p -e "CREATE DATABASE video_agent;"
```

### 4.2 启动ComfyUI服务

```bash
# 克隆ComfyUI仓库（如果还没有）
git clone https://github.com/comfyanonymous/ComfyUI.git

# 进入ComfyUI目录
cd ComfyUI

# 创建并激活虚拟环境（可选，但推荐）
python -m venv venv
./venv/bin/activate  # Linux

# 安装ComfyUI依赖
pip install -r requirements.txt

# 启动ComfyUI服务
python main.py --listen
```

## 5. 运行前配置

### 5.1 创建并配置.env文件

```bash
# 进入backend目录
cd backend

# 复制.env.example为.env
cp .env.example .env

# 编辑.env文件，配置必要的环境变量
# 至少需要配置：COMFYUI_URL=http://127.0.0.1:8188
```

## 6. 运行run_complete_workflow.py

```bash
# 确保在项目根目录下执行
# 确保conda环境已激活（如果使用conda）
# 确保ComfyUI服务正在运行

python backend/run_complete_workflow.py
```

## 7. 可选的优化和调试

### 7.1 安装调试工具

```bash
pip install ipdb debugpy
```

### 7.2 安装性能监控工具

```bash
pip install psutil memory-profiler
```

## 8. 常见问题解决方案

### 8.1 问题：找不到FFmpeg
解决：确保FFmpeg已安装并添加到系统路径，或在.env文件中指定FFmpeg路径。

### 8.2 问题：无法连接到MySQL
解决：确保MySQL服务正在运行，并且用户名和密码正确。

### 8.3 问题：无法连接到ComfyUI
解决：确保ComfyUI服务正在运行，并且配置的COMFYUI_URL正确。

### 8.4 问题：缺少依赖包
解决：使用上述完整安装命令重新安装所有依赖。

### 8.5 问题：asyncio运行时错误
解决：确保Python版本为3.8或更高，并且没有其他asyncio事件循环正在运行。

## 9. 完整的环境检查命令

运行以下命令检查所有依赖是否已正确安装：

```bash
# 检查Python版本
python --version

# 检查FFmpeg
ffmpeg -version

# 检查MySQL服务
mysql --version

# 检查ComfyUI连接
curl -I http://127.0.0.1:8188

# 检查Python包
pip list | grep -E "flask|sqlalchemy|pymysql|httpx|aiohttp|aiofiles|requests|numpy|Pillow|moviepy|imageio|pydub|python-dotenv|orjson"
```

## 10. 快速启动脚本

您可以创建一个快速启动脚本`setup_env.sh`，包含以下内容：

```bash
#!/bin/bash

# 安装系统依赖
echo "安装系统依赖..."
sudo apt update
sudo apt install -y ffmpeg git curl

# 创建并激活conda环境
echo "创建并激活conda环境..."
conda create -n video_agent python=3.10 -y
conda activate video_agent

# 安装FFmpeg
echo "安装FFmpeg..."
conda install -c conda-forge ffmpeg -y

# 安装Python依赖
echo "安装Python依赖..."
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql httpx aiohttp aiofiles -r backend/requirements.txt

# 启动MySQL服务
echo "启动MySQL服务..."
sudo systemctl start mysql
sudo systemctl enable mysql

# 创建数据库
echo "创建数据库..."
sudo mysql -u root -p -e "CREATE DATABASE video_agent;"

# 配置.env文件
echo "配置.env文件..."
cd backend
cp .env.example .env
echo "COMFYUI_URL=http://127.0.0.1:8188" >> .env

# 返回项目根目录
cd ..

echo "环境设置完成！"
echo "请确保ComfyUI服务正在运行，然后执行：python backend/run_complete_workflow.py"
```

然后运行：
```bash
chmod +x setup_env.sh
./setup_env.sh
```

# 总结

运行`run_complete_workflow.py`需要以下组件：

1. **系统级依赖**：FFmpeg、MySQL、Git、Curl
2. **Python包**：Flask相关包、数据库包、HTTP客户端包等
3. **服务**：MySQL服务、ComfyUI服务
4. **配置**：正确配置的.env文件

按照上述步骤安装所有依赖和服务后，您应该能够成功运行`run_complete_workflow.py`。