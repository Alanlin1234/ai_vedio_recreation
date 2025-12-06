# AI视频生成系统 - GPU加速使用指南

## 🎯 项目概述

这是一个基于AI的自动化视频生成系统，能够从热点采集、脚本生成、图像生成到视频合成的全流程自动化处理。系统包含8个AI Agent协同工作，支持多种风格和主题的视频创作。

### 核心功能
- 🔥 **热点采集** - 自动采集抖音热点内容
- 📝 **脚本生成** - AI自动生成视频脚本
- 🎨 **图像生成** - 使用GPU加速的Flux模型生成高质量图像
- 🎬 **视频合成** - 自动合成图像序列为视频
- 🔍 **一致性检验** - 确保场景风格统一
- 📊 **追踪系统** - 完整的执行记录和监控

## 🚀 快速开始 - GPU加速版

### 系统要求
- Python 3.10+ （推荐3.10.11）
- NVIDIA GPU（支持CUDA 12.1+，推荐RTX 40系列）
- 至少8GB VRAM（推荐16GB+）
- 至少16GB系统内存
- NVIDIA驱动531.61+（支持CUDA 12.1）

### 1. 环境准备

#### 安装依赖
```bash
# 进入项目根目录
cd d:\ai-agent-comfy

# 创建并激活虚拟环境
python -m venv venv
venv\Scripts\activate.bat

# 安装Python依赖
cd backend
pip install -r requirements.txt
```

#### 配置环境变量
```bash
# 复制环境变量模板
copy .env.example .env

# 编辑.env文件，配置以下关键参数
```

**必需配置**：
```bash
# ComfyUI服务地址（必须配置）
COMFYUI_URL=http://127.0.0.1:8188

# 大模型API（用于脚本生成）
DASHSCOPE_API_KEY=your_dashscope_api_key
SILICONFLOW_API_KEY=your_siliconflow_api_key
```

### 2. GPU加速启动ComfyUI

我们提供了专门的GPU加速启动脚本 `run_nvidia_gpu_simple.bat`，用于快速启动使用NVIDIA GPU加速的ComfyUI服务。

#### 脚本内容说明
```batch
@echo off
REM Start ComfyUI with NVIDIA GPU acceleration
cd /d D:\ComfyUI-master
echo Starting ComfyUI with NVIDIA GPU acceleration...

REM Check if NVIDIA GPU is available
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo Warning: NVIDIA GPU not detected
    pause
    exit /b 1
)

REM Start ComfyUI with GPU parameters
python main.py --gpu-only --cuda-device 0

if %ERRORLEVEL% neq 0 (
    echo Error: ComfyUI failed to start
    pause
    exit /b %ERRORLEVEL%
)

echo ComfyUI started successfully
pause
```

#### 启动步骤

1. **确保ComfyUI安装正确**
   - 请确保ComfyUI已安装在 `D:\ComfyUI-master` 目录
   - 如ComfyUI安装在其他目录，请修改脚本中的 `cd /d D:\ComfyUI-master` 行

2. **启动GPU加速的ComfyUI**
   ```bash
   # 在项目根目录执行
   run_nvidia_gpu_simple.bat
   ```

3. **验证ComfyUI启动状态**
   - 启动后会显示类似信息：
     ```
     Starting ComfyUI with NVIDIA GPU acceleration...
     Set cuda device to: 0
     Total VRAM 8188 MB, total RAM 15540 MB
     pytorch version: 2.5.1+cu121
     Set vram state to: HIGH_VRAM
     Device: cuda:0 NVIDIA GeForce RTX 4060 Laptop GPU : cudaMallocAsync
     ```
   - 访问 http://127.0.0.1:8188 确认ComfyUI已成功启动

### 3. 启动系统服务

#### 启动抖音爬虫服务（端口80）
```bash
# 进入爬虫目录
cd d:\ai-agent-comfy\backend\crawler\Douyin_TikTok_Download_API-main

# 启动爬虫服务
python start.py
```

#### 验证服务状态
```bash
# 检查ComfyUI GPU状态
python check_comfyui_gpu.py

# 检查抖音爬虫API
python test_douyin_hotsearch.py
```

### 4. 生成视频

#### 使用脚本生成测试视频
```bash
# 进入项目根目录
cd d:\ai-agent-comfy

# 运行视频生成测试脚本
python test_comfyui_video.py
```

#### 使用API生成视频
```bash
# 使用curl调用视频生成API
curl -X POST http://localhost:5000/api/agent/create-video \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["风景", "自然"],
    "style": "cinematic",
    "duration": 10,
    "batch_size": 1
  }'
```

## 📋 详细操作流程

### 1. GPU加速配置说明

#### ComfyUI GPU启动参数详解
- `--gpu-only`：强制使用GPU，不使用CPU回退
- `--cuda-device 0`：指定使用第0个CUDA设备（通常是主GPU）
- 可选参数：
  - `--lowvram`：低显存模式（适合4-8GB VRAM）
  - `--normalvram`：普通显存模式（适合8-16GB VRAM）
  - `--highvram`：高显存模式（适合16GB+ VRAM）

#### 推荐GPU参数组合
| GPU VRAM | 推荐参数 |
|----------|----------|
| 4-8GB    | `--lowvram --cuda-device 0` |
| 8-16GB   | `--normalvram --cuda-device 0` |
| 16GB+    | `--highvram --cuda-device 0` |

### 2. 视频生成完整流程

```
热点采集 → 脚本生成 → 分镜规划 → 图像生成 → 一致性检验 → 视频合成
```

#### 阶段1：热点采集（自动）
- 调用抖音爬虫API获取热门话题
- 分析热点趋势和用户兴趣
- 生成视频主题建议

#### 阶段2：脚本生成（AI）
- 基于热点生成结构化脚本
- 包含场景描述、镜头切换、旁白文本
- 支持多种风格模板

#### 阶段3：分镜规划（AI）
- 将脚本转换为可视化分镜
- 设计每个镜头的构图和风格
- 生成图像生成提示词

#### 阶段4：图像生成（GPU加速）
- 使用Flux模型生成高质量图像
- GPU加速处理，提高生成速度
- 支持批量生成多张图像

#### 阶段5：一致性检验（AI）
- 检查图像风格一致性
- 评估图像质量和相关性
- 自动重生成不符合要求的图像

#### 阶段6：视频合成（自动）
- 将图像序列合成为视频
- 添加背景音乐和过渡效果
- 输出最终视频文件

## 🔧 高级配置

### 调整视频生成参数

在 `backend/config.py` 中调整视频生成参数：

```python
class Config:
    # GPU加速配置
    GPU_ACCELERATION = {
        "enabled": True,
        "device_id": 0,  # 对应 --cuda-device 参数
        "vram_mode": "normal",  # low, normal, high
        "force_gpu": True  # 对应 --gpu-only 参数
    }
    
    # 图像生成参数
    IMAGE_GENERATION = {
        "default_width": 1280,
        "default_height": 720,
        "steps": 20,  # 推荐20-30步，平衡质量和速度
        "cfg": 8.0,
        "batch_size": 1  # GPU显存充足可增加到2-4
    }
    
    # 视频合成参数
    VIDEO_SYNTHESIS = {
        "fps": 30,
        "transition_duration": 0.5,
        "audio_enabled": True
    }
```

### 优化GPU利用率

1. **调整生成分辨率**：
   - 降低分辨率可提高GPU利用率
   - 推荐：1280x720（平衡质量和速度）
   - 高质量：1920x1080（需要更多显存）

2. **调整采样步骤**：
   - 增加采样步骤可提高图像质量，但会增加生成时间
   - 推荐：20-30步

3. **启用异步处理**：
   - 系统默认启用异步处理，提高并发性能
   - 可在配置中调整异步线程数

## 📊 GPU性能监控

### 实时监控GPU状态

```bash
# 实时查看GPU利用率
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader,nounits -l 1

# 查看详细GPU信息
nvidia-smi -a
```

### 监控GPU利用率的脚本

```bash
# 创建监控脚本
@echo off
for /l %%i in (1,1,30) do (
    nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu --format=csv,noheader,nounits
    timeout /t 2 >nul
)
```

### 性能优化建议

- ✅ 关闭其他占用GPU的应用程序
- ✅ 确保NVIDIA驱动是最新版本
- ✅ 使用高质量电源，确保GPU稳定供电
- ✅ 保持GPU温度在合理范围（<80°C）
- ✅ 定期清理GPU驱动缓存

## 🐛 故障排除

### 常见问题及解决方案

#### 问题1：ComfyUI启动失败，提示端口被占用
**症状**：`OSError: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8188)`

**解决**：
```bash
# 查找占用8188端口的进程
netstat -ano | findstr :8188

# 终止占用端口的进程
# 假设PID为12345
taskkill /F /PID 12345

# 或者终止所有Python进程
 taskkill /F /IM python.exe /T
```

#### 问题2：GPU未被检测到
**症状**：`Warning: NVIDIA GPU not detected`

**解决**：
1. 检查NVIDIA驱动是否正确安装：`nvidia-smi`
2. 确认CUDA环境变量配置正确
3. 重启电脑后重试
4. 检查GPU是否被其他应用占用

#### 问题3：CUDA内存不足
**症状**：`RuntimeError: CUDA out of memory`

**解决**：
1. 减少生成分辨率：`width=1280, height=720`
2. 减少采样步骤：`steps=20`
3. 减少批量大小：`batch_size=1`
4. 使用低显存模式：`--lowvram`
5. 关闭其他占用GPU内存的应用

#### 问题4：视频生成速度慢
**症状**：生成10秒视频需要超过30分钟

**解决**：
1. 确保使用GPU加速：`--gpu-only --cuda-device 0`
2. 调整生成参数：降低分辨率、减少采样步骤
3. 检查系统资源：确保内存充足，CPU使用率正常
4. 优化工作流：减少不必要的处理步骤

## 📁 文件结构说明

```
d:\ai-agent-comfy\
├── backend\                 # 后端核心系统
│   ├── app\                # 应用代码
│   │   ├── agents\         # 8个AI Agent
│   │   ├── services\       # 业务服务
│   │   ├── routes\         # API路由
│   │   └── models\         # 数据模型
│   ├── crawler\            # 抖音爬虫
│   ├── config.py           # 系统配置
│   └── requirements.txt    # 依赖列表
├── output\                 # 输出目录
│   ├── comfyui\           # 生成的图像
│   └── videos\            # 最终视频
├── logs\                  # 系统日志
├── run_nvidia_gpu_simple.bat  # GPU加速启动脚本
└── check_comfyui_gpu.py       # GPU状态检查脚本
```

## 📋 命令速查

### GPU相关命令
```bash
# 检查GPU状态
nvidia-smi

# 查看GPU详细信息
nvidia-smi -a

# 实时监控GPU
nvidia-smi -l 1

# 查看CUDA版本
nvcc --version
```

### 服务管理命令
```bash
# 启动ComfyUI GPU加速版
run_nvidia_gpu_simple.bat

# 检查ComfyUI状态
python check_comfyui_gpu.py

# 检查抖音爬虫API
python test_douyin_hotsearch.py

# 运行视频生成测试
python test_comfyui_video.py
```

### 系统监控命令
```bash
# 查看系统资源
 tasklist | findstr python

# 查看端口占用
netstat -ano | findstr :8188

# 终止进程
taskkill /F /PID <PID>
```

## 🔄 项目重启流程

### 完整重启步骤

1. **终止所有相关进程**
   ```bash
   taskkill /F /IM python.exe /T
   ```

2. **启动GPU加速的ComfyUI**
   ```bash
   run_nvidia_gpu_simple.bat
   ```

3. **启动抖音爬虫服务**
   ```bash
   cd backend\crawler\Douyin_TikTok_Download_API-main
   python start.py
   ```

4. **验证服务状态**
   ```bash
   python check_comfyui_gpu.py
   python test_douyin_hotsearch.py
   ```

5. **开始生成视频**
   ```bash
   python test_comfyui_video.py
   ```

## 🎯 最佳实践

### 视频生成质量优化

1. **选择合适的风格**
   - 根据视频主题选择合适的风格模板
   - 保持风格一致性，避免风格切换过于频繁

2. **优化提示词**
   - 提供详细的场景描述
   - 使用具体的形容词和视觉元素
   - 避免模糊和歧义的表述

3. **调整生成参数**
   - 根据GPU显存调整分辨率和批量大小
   - 平衡质量和速度，选择合适的采样步骤
   - 调整CFG值，控制生成图像的多样性

4. **后期处理**
   - 对生成的视频进行适当的后期调整
   - 添加合适的背景音乐和音效
   - 调整视频的亮度、对比度和色彩

### 系统维护建议

- ✅ 定期更新NVIDIA驱动和CUDA工具包
- ✅ 定期清理系统垃圾和临时文件
- ✅ 备份重要的配置文件和生成结果
- ✅ 监控系统资源使用情况
- ✅ 定期重启系统，保持系统稳定

## 🚀 下一步

### 扩展功能
1. **多语言支持** - 支持中文、英文、日文等多种语言
2. **自定义模板** - 允许用户创建和使用自定义视频模板
3. **实时预览** - 生成过程中的实时预览功能
4. **批量处理** - 支持大规模视频批量生成
5. **云GPU支持** - 支持使用云GPU资源进行生成

### 性能提升
1. **模型优化** - 优化图像生成模型，提高生成速度
2. **分布式处理** - 支持多GPU并行处理
3. **缓存机制** - 实现智能缓存，避免重复计算
4. **异步处理** - 优化异步处理逻辑，提高并发性能

---

**开始你的AI视频创作之旅吧！** 🎬

如果有任何问题，请参考本文档的故障排除部分，或查看系统日志获取详细信息。

**注意**：本系统仅用于学习和研究目的，请勿用于商业用途或违法活动。