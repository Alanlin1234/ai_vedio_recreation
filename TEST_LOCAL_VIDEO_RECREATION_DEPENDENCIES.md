# 运行test_local_video_recreation.py所需的库

## 1. 核心依赖

以下是运行`test_local_video_recreation.py`必需的Python库：

### 1.1 基础库（来自requirements.txt）

```bash
# 从requirements.txt安装基础依赖
pip install -r backend/requirements.txt
```

### 1.2 缺失的依赖（需要额外安装）

通过代码分析，发现以下依赖在requirements.txt中缺失但在代码中使用：

```bash
# Flask相关依赖（用于应用框架和路由）
pip install flask flask-cors flask-sqlalchemy

# 数据库依赖（用于数据存储和ORM）
pip install sqlalchemy pymysql

# 视频处理依赖（用于视频编辑和处理）
pip install moviepy
```

## 2. 一次性完整安装命令

### 2.1 使用pip一次性安装所有依赖

```bash
# 确保在项目根目录下执行
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql moviepy -r backend/requirements.txt
```

### 2.2 使用conda创建完整环境

```bash
# 创建名为video_agent的conda环境
conda create -n video_agent python=3.10 -y

# 激活环境
conda activate video_agent

# 安装系统依赖（FFmpeg是视频处理必需的）
conda install -c conda-forge ffmpeg -y

# 安装Python依赖
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql moviepy -r backend/requirements.txt
```

## 3. 必需的系统依赖

### 3.1 安装FFmpeg（视频处理必需）

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install ffmpeg -y

# CentOS/RHEL系统
sudo dnf install ffmpeg -y

# 使用conda安装（推荐，版本可控）
conda install -c conda-forge ffmpeg -y
```

### 3.2 安装MySQL数据库（用于存储视频和作者信息）

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install mysql-server -y

# CentOS/RHEL系统
sudo dnf install mysql-server -y

# 启动MySQL服务
sudo systemctl start mysql  # Ubuntu/Debian
sudo systemctl start mysqld  # CentOS/RHEL

# 设置MySQL根密码（首次安装时）
sudo mysql_secure_installation

# 创建数据库
sudo mysql -u root -p -e "CREATE DATABASE video_agent;"
```

## 4. 运行前配置

### 4.1 创建并配置.env文件

```bash
# 进入backend目录
cd backend

# 复制.env.example为.env
cp .env.example .env

# 编辑.env文件，配置必要的环境变量
# 至少需要配置：COMFYUI_URL=http://127.0.0.1:8188
```

### 4.2 初始化数据库

```bash
# 进入backend目录
cd backend

# 运行Flask应用来初始化数据库（或使用数据库迁移工具）
# 应用启动时会自动创建数据库表
python run.py  # 运行后可以立即停止，因为我们只需要初始化数据库
```

## 5. 运行test_local_video_recreation.py

### 5.1 基本用法

```bash
# 确保在项目根目录下执行
# 确保已激活虚拟环境（如果使用）

python backend/test_local_video_recreation.py /path/to/your/video.mp4
```

### 5.2 示例

```bash
# 使用示例视频文件
python backend/test_local_video_recreation.py downloads/抖音20251216-192137.mp4
```

## 6. 依赖分析详情

### 6.1 直接依赖

| 依赖名称 | 用途 | 来源 |
|---------|------|------|
| **flask** | Web应用框架 | 缺失，需要额外安装 |
| **flask-cors** | 处理跨域请求 | 缺失，需要额外安装 |
| **flask-sqlalchemy** | Flask数据库集成 | 缺失，需要额外安装 |
| **sqlalchemy** | 数据库ORM框架 | 缺失，需要额外安装 |
| **pymysql** | MySQL数据库驱动 | 缺失，需要额外安装 |
| **moviepy** | 视频处理和编辑 | 来自requirements.txt |
| **requests** | HTTP客户端，用于API调用 | 来自requirements.txt |
| **python-dotenv** | 环境变量管理 | 来自requirements.txt |
| **orjson** | 高性能JSON处理 | 来自requirements.txt |
| **aiohttp** | 异步HTTP客户端 | 来自requirements.txt |
| **aiofiles** | 异步文件操作 | 来自requirements.txt |
| **numpy** | 数值计算（moviepy依赖） | 来自requirements.txt |
| **Pillow** | 图像处理（moviepy依赖） | 来自requirements.txt |
| **imageio** | 图像和视频I/O（moviepy依赖） | 来自requirements.txt |
| **imageio-ffmpeg** | 视频编解码（moviepy依赖） | 来自requirements.txt |

### 6.2 间接依赖

| 依赖名称 | 用途 | 被哪个库依赖 |
|---------|------|------------|
| **FFmpeg** | 视频和音频处理 | moviepy |
| **MySQL** | 数据库服务器 | sqlalchemy + pymysql |

## 7. 常见问题解决方案

### 7.1 问题：找不到FFmpeg
解决：确保FFmpeg已安装并添加到系统路径，或在.env文件中指定FFmpeg路径。

### 7.2 问题：无法连接到MySQL
解决：确保MySQL服务正在运行，并且用户名和密码正确。

### 7.3 问题：MoviePy无法导入
解决：确保已正确安装moviepy及其依赖：`pip install moviepy`

### 7.4 问题：无法导入自定义模块
解决：确保Python路径设置正确，项目根目录已添加到PYTHONPATH。

### 7.5 问题：数据库表不存在
解决：确保已初始化数据库，应用启动时会自动创建数据库表。

## 8. 验证安装

```bash
# 检查FFmpeg是否安装成功
ffmpeg -version

# 检查MySQL服务是否运行
sudo systemctl status mysql  # Ubuntu/Debian
sudo systemctl status mysqld  # CentOS/RHEL

# 检查Python库是否安装成功
pip list | grep -E "flask|sqlalchemy|moviepy|requests|python-dotenv|orjson|aiohttp|aiofiles|numpy|Pillow|imageio|imageio-ffmpeg"
```

## 9. 快速启动脚本

您可以创建一个快速启动脚本`setup_test_env.sh`，包含以下内容：

```bash
#!/bin/bash

# 安装系统依赖
echo "安装系统依赖..."
sudo apt update
sudo apt install -y ffmpeg mysql-server git curl

# 启动MySQL服务
echo "启动MySQL服务..."
sudo systemctl start mysql
sudo systemctl enable mysql

# 创建数据库
echo "创建数据库..."
sudo mysql -u root -p -e "CREATE DATABASE video_agent;"

# 安装Python依赖
echo "安装Python依赖..."
pip install flask flask-cors flask-sqlalchemy sqlalchemy pymysql moviepy -r backend/requirements.txt

# 配置.env文件
echo "配置.env文件..."
cd backend
cp .env.example .env
echo "COMFYUI_URL=http://127.0.0.1:8188" >> .env

# 返回项目根目录
cd ..

echo "环境设置完成！"
echo "现在可以运行：python backend/test_local_video_recreation.py /path/to/your/video.mp4"
```

然后运行：
```bash
chmod +x setup_test_env.sh
./setup_test_env.sh
```

# 总结

运行`test_local_video_recreation.py`需要以下组件：

1. **系统级依赖**：FFmpeg、MySQL、Git、Curl
2. **Python库**：Flask相关库、数据库库、视频处理库、HTTP客户端库等
3. **服务**：MySQL服务
4. **配置**：正确配置的.env文件和初始化的数据库

按照上述步骤安装所有依赖和服务后，您应该能够成功运行`test_local_video_recreation.py`。