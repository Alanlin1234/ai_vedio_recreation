# 快速修复：找不到requirements.txt文件

## 问题分析

错误信息：`Could not open requirements.txt: [Errno 2] No such file or directory: 'backend/requirements.txt'`

这是因为您当前不在项目根目录下执行命令。

## 解决方案

### 1. 首先进入项目根目录

```bash
# 假设您的项目位于home目录下的video-agent文件夹
cd ~/video-agent  # 替换为您的实际项目路径

# 确认目录结构
ls -la
```

### 2. 确认文件路径

```bash
# 检查backend目录下是否存在requirements.txt文件
ls -la backend/
```

### 3. 正确的安装命令顺序

```bash
# 1. 激活conda环境
conda activate video_agent

# 2. 进入项目根目录（如果还没进入）
cd /path/to/your/project  # 替换为您的实际项目路径

# 3. 使用pip安装依赖
pip install -r backend/requirements.txt
```

## 完整的命令示例

```bash
# 假设您的项目位于 ~/projects/video-agent
cd ~/projects/video-agent
conda activate video_agent
pip install -r backend/requirements.txt
```

## 常见问题

### Q: 如何确认我的项目路径？
A: 您可以使用 `pwd` 命令查看当前目录路径，使用 `ls` 命令查看当前目录下的文件和文件夹。

### Q: 如何找到我的项目？
A: 您可以使用 `find` 命令搜索项目文件夹：
   ```bash
   find ~ -name "video-agent" -type d  # 替换为您的实际项目名称
   ```

### Q: 我忘记了项目的准确位置怎么办？
A: 您可以使用 `locate` 命令（如果已安装）或查看最近访问的目录：
   ```bash
   # 查看最近访问的目录
history | grep cd
   ```

## 后续步骤

安装成功后，您可以继续执行：

```bash
# 进入backend目录
cd backend

# 运行项目
python run.py
```