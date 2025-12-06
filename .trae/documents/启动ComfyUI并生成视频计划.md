# 启动ComfyUI并生成视频计划

## 1. 启动ComfyUI服务

### 1.1 查找ComfyUI安装位置
- 检查常见安装目录：
  - `C:\ComfyUI`
  - `D:\ComfyUI`
  - `%USERPROFILE%\ComfyUI`
  - `%USERPROFILE%\Downloads\ComfyUI`

### 1.2 启动ComfyUI
- **Windows**: 运行 `run_nvidia_gpu.bat` 或 `run_cpu.bat`
- **命令行**: `python main.py`
- **后台运行**: 使用 `python main.py --listen` 允许外部访问

### 1.3 验证ComfyUI启动
- 等待服务启动（通常需要30秒-1分钟）
- 访问 http://127.0.0.1:8188 确认服务运行
- 使用 `check_comfyui.py` 脚本验证API响应

## 2. 配置ComfyUI模型

### 2.1 确保Flux模型已安装
- 检查 `ComfyUI/models/checkpoints/` 目录
- 确保包含 `flux_dev.safetensors` 或类似文件

### 2.2 确保Wan2.1模型已安装
- 检查 `ComfyUI/models/checkpoints/` 目录
- 确保包含 `wan_2.1.safetensors` 和 `wan_2.1_vae.safetensors`

### 2.3 配置工作流
- 确保FLUX_GGUF_WORKFLOW .json和wan2.1_t2v.json已正确配置
- 检查模型路径和节点配置

## 3. 执行视频生成

### 3.1 运行生成脚本
```bash
python generate_video.py
```

### 3.2 监控生成过程
- 查看控制台输出，监控各阶段进度
- 检查ComfyUI界面，确认图像生成状态
- 查看日志文件 `logs/video_generation_*.log`

### 3.3 处理可能的错误
- **模型未找到**: 检查模型路径配置
- **节点错误**: 检查工作流节点ID配置
- **生成超时**: 调整超时参数

## 4. 结果检查

### 4.1 检查生成的视频
- 查看 `output/videos/` 目录下的视频文件
- 验证视频质量和内容

### 4.2 查看生成日志
- 分析生成过程中的性能指标
- 检查可能的优化点

## 5. 预期结果

- ✅ ComfyUI服务成功启动
- ✅ 视频生成流程执行完成
- ✅ 生成一个60秒的风景旅行视频
- ✅ 视频风格符合cinematic要求
- ✅ 视频分辨率1024x576
- ✅ 帧率24fps

## 6. 故障排除

### 6.1 ComfyUI启动失败
- 检查显卡驱动和CUDA版本
- 检查Python环境和依赖
- 查看ComfyUI启动日志

### 6.2 模型加载失败
- 检查模型文件是否完整
- 检查模型路径配置
- 确保模型与ComfyUI版本兼容

### 6.3 生成质量不佳
- 优化提示词
- 调整采样步数和CFG比例
- 尝试不同的模型

## 7. 后续优化

- 添加背景音乐和字幕
- 优化视频转场效果
- 调整色彩和对比度
- 增加视频长度和复杂度

## 8. 输出位置

- 生成的视频文件：`output/videos/`
- 日志文件：`logs/video_generation_*.log`
- ComfyUI日志：`ComfyUI/logs/`