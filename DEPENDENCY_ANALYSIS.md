# 项目依赖分析报告

## 1. 系统级依赖

这些是项目运行必需的外部软件，需要单独安装：

| 依赖名称 | 用途 | 安装方式 |
|---------|------|---------|
| **FFmpeg** | 视频和音频处理核心工具 | `conda install -c conda-forge ffmpeg -y` 或 `sudo apt install ffmpeg -y` |
| **MySQL** | 数据库服务器 | `sudo apt install mysql-server -y` 或使用Docker容器 |
| **ComfyUI** | AI图像/视频生成服务 | 需要单独下载并运行（https://github.com/comfyanonymous/ComfyUI） |

## 2. Python依赖缺失

通过代码分析，发现以下依赖在requirements.txt中缺失但在代码中使用：

| 缺失的依赖 | 用途 | 安装命令 |
|-----------|------|---------|
| **Flask-CORS** | 处理跨域请求 | `pip install flask-cors` |
| **SQLAlchemy** | 数据库ORM框架 | `pip install sqlalchemy` |
| **pymysql** | MySQL数据库驱动 | `pip install pymysql` |
| **flask-sqlalchemy** | Flask SQLAlchemy集成 | `pip install flask-sqlalchemy` |

## 3. 可选依赖

这些依赖根据项目配置可能需要：

| 依赖名称 | 用途 | 安装命令 |
|---------|------|---------|
| **opencv-python** | 高级图像处理 | `pip install opencv-python` |
| **scikit-image** | 图像分析算法 | `pip install scikit-image` |
| **face-recognition** | 人脸识别功能 | `pip install face-recognition` |
| **dlib** | 人脸检测库（face-recognition依赖） | `pip install dlib` |

## 4. 服务依赖

项目运行需要以下服务：

| 服务名称 | 状态 | 配置方式 |
|---------|------|---------|
| **MySQL服务** | 必需 | 启动MySQL服务，创建数据库 `video_agent` |
| **ComfyUI服务** | 必需 | 启动ComfyUI服务，默认地址：http://127.0.0.1:8188 |

## 5. 环境变量配置

项目需要配置以下环境变量（在.env文件中）：

| 环境变量 | 用途 | 默认值 |
|---------|------|---------|
| **DASHSCOPE_API_KEY** | 阿里云DashScope API密钥 | sk-09888bd521f143baa39870a1a648d830 |
| **SILICONFLOW_API_KEY** | SiliconFlow API密钥 | sk-vkxacmptbqpmmsnvdaayvvxzvlhfdvdxyemjfbjwscbimytd |
| **COMFYUI_URL** | ComfyUI服务地址 | http://127.0.0.1:8188 |
| **OPENAI_API_KEY** | OpenAI API密钥（可选） | 无 |

## 6. 完整安装命令

```bash
# 1. 安装缺失的Python依赖
pip install flask-cors sqlalchemy pymysql flask-sqlalchemy

# 2. 安装FFmpeg（推荐使用conda）
conda install -c conda-forge ffmpeg -y

# 3. 安装MySQL（Ubuntu/Debian）
sudo apt update
sudo apt install mysql-server -y

# 4. 启动MySQL服务
sudo systemctl start mysql
sudo systemctl enable mysql

# 5. 创建数据库
sudo mysql -u root -p -e "CREATE DATABASE video_agent;"

# 6. 启动ComfyUI服务（在ComfyUI目录下）
python main.py --listen
```

## 7. 验证安装

```bash
# 检查FFmpeg是否安装成功
ffmpeg -version

# 检查MySQL服务是否运行
sudo systemctl status mysql

# 检查ComfyUI是否运行
curl -I http://127.0.0.1:8188
```

## 8. 常见问题

### Q: 为什么需要单独安装ComfyUI？
A: ComfyUI是一个独立的AI图像/视频生成服务，项目通过API调用它来生成图像和视频。

### Q: 可以使用其他数据库替代MySQL吗？
A: 可以，但需要修改config.py中的数据库连接配置。

### Q: 可以不安装MySQL吗？
A: 不可以，项目需要数据库来存储视频和作者信息。如果只是测试，可以考虑使用SQLite作为替代方案（需要修改配置）。

### Q: FFmpeg必须安装吗？
A: 是的，FFmpeg是视频处理的核心工具，项目无法在没有FFmpeg的情况下运行。