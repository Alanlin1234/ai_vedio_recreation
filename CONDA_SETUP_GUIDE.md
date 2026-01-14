# Conda环境配置指南

## 1. 安装Miniconda（推荐）或Anaconda

### 1.1 下载并安装Miniconda

```bash
# 下载Miniconda安装脚本
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 运行安装脚本
bash Miniconda3-latest-Linux-x86_64.sh

# 按照提示完成安装，建议选择默认选项

# 激活conda（安装后需要重新启动终端或执行）
source ~/.bashrc  # 或 source ~/.zshrc 取决于您使用的shell
```

## 2. 创建conda环境

### 2.1 创建新环境

```bash
# 创建名为video_agent的conda环境，使用Python 3.10
conda create -n video_agent python=3.10 -y
```

### 2.2 激活环境

```bash
conda activate video_agent
```

## 3. 安装项目依赖

### 3.1 进入项目目录

```bash
cd /path/to/your/project
```

### 3.2 安装Python依赖

```bash
# 进入backend目录
cd backend

# 使用pip安装项目依赖
pip install -r requirements.txt
```

## 4. 安装系统依赖

### 4.1 安装FFmpeg（视频处理必需）

```bash
# Ubuntu/Debian系统
sudo apt update
sudo apt install ffmpeg -y

# CentOS/RHEL系统
sudo dnf install ffmpeg -y

# 或者使用conda安装（推荐，因为版本可控）
conda install -c conda-forge ffmpeg -y
```

### 4.2 安装其他可能需要的系统依赖

```bash
# Ubuntu/Debian系统
sudo apt install -y libsm6 libxext6 libxrender1 libfontconfig1

# CentOS/RHEL系统
sudo dnf install -y libXext libSM libXrender
```

## 5. 配置环境变量

### 5.1 创建.env文件

```bash
# 进入backend目录
cd backend

# 复制.env.example为.env
cp .env.example .env

# 使用文本编辑器编辑.env文件，配置所需的环境变量
# 例如：vi .env 或 nano .env
```

### 5.2 配置关键环境变量

在.env文件中，确保配置以下关键变量：

```
# ComfyUI配置
COMFYUI_API_URL=http://localhost:8188
COMFYUI_WORKFLOW_PATH=./comfyui_workflow_template.py

# 其他配置
LOG_LEVEL=INFO
OUTPUT_DIR=./output
DOWNLOADS_DIR=./downloads
```

## 6. 运行项目

### 6.1 激活conda环境

```bash
conda activate video_agent
```

### 6.2 运行主程序

```bash
# 进入backend目录
cd backend

# 运行主程序
python run.py
```

### 6.3 运行完整工作流测试

```bash
# 运行完整工作流测试
python run_complete_workflow.py
```

### 6.4 运行特定测试脚本

```bash
# 测试本地视频处理
python test_local_video_recreation.py

# 测试JSON提示词解析器
python test_json_prompt_parser.py
```

## 7. 管理conda环境

### 7.1 列出所有conda环境

```bash
conda env list
```

### 7.2 退出conda环境

```bash
conda deactivate
```

### 7.3 删除conda环境（如果需要）

```bash
conda env remove -n video_agent
```

### 7.4 更新conda和依赖

```bash
# 更新conda本身
conda update conda -y

# 更新环境中的所有包
conda update --all -y

# 更新特定包
pip install --upgrade package_name
```

## 8. 常见问题解决

### 8.1 权限问题

如果遇到权限错误，可以尝试：

```bash
# 确保项目目录有正确的权限
chmod -R 755 /path/to/your/project
```

### 8.2 依赖冲突

如果遇到依赖冲突，可以尝试：

```bash
# 使用conda的环境修复功能
conda install --freeze-installed package_name

# 或者创建一个新的环境并重新安装依赖
```

### 8.3 FFmpeg路径问题

如果ffmpeg命令找不到，可以将ffmpeg添加到PATH中：

```bash
# 查找ffmpeg位置
which ffmpeg

# 如果使用conda安装的ffmpeg，确保conda环境已激活
```

## 9. Docker替代方案（可选）

如果您更喜欢使用Docker，可以创建一个Dockerfile：

```dockerfile
FROM continuumio/miniconda3

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app

# 创建conda环境
RUN conda create -n video_agent python=3.10 -y && \
    echo "conda activate video_agent" > ~/.bashrc

# 激活环境并安装依赖
SHELL ["/bin/bash", "-c"]
RUN source activate video_agent && \
    conda install -c conda-forge ffmpeg -y && \
    pip install -r backend/requirements.txt

# 暴露端口（如果项目需要）
EXPOSE 8000

# 设置默认命令
CMD ["/bin/bash", "-c", "source activate video_agent && cd backend && python run.py"]
```

然后构建和运行Docker容器：

```bash
docker build -t video_agent .
docker run -it --rm video_agent
```

# 总结

使用conda环境可以更好地管理项目依赖，避免与系统Python环境冲突。按照上述步骤，您可以在Linux系统上成功创建和配置conda环境，并运行项目。

如果您遇到任何问题，请检查错误信息并参考conda官方文档或项目README.md文件。