# 运行项目完整流程计划

## 1. 项目概述

该项目是一个基于Agent架构的AI视频生成系统，主要流程包括：
- 抖音热点获取
- 脚本拆解
- 分镜规划
- 关键帧生成（使用Flux模型）
- 图像生成
- 一致性检验
- 视频合成

## 2. 运行前准备

### 2.1 检查依赖
- 确保Python 3.10+已安装
- 确保MySQL数据库已启动
- 确保ComfyUI服务已运行（用于图像和视频生成）

### 2.2 安装依赖
```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装爬虫依赖
cd crawler/Douyin_TikTok_Download_API-main
pip install -r requirements.txt
```

## 3. 启动服务

### 3.1 启动抖音爬虫服务
```bash
# 在项目根目录执行
python start_crawler.py start
```

### 3.2 启动后端服务
```bash
# 在backend目录执行
python run.py
```

## 4. 测试完整流程

### 4.1 使用API测试
- 后端服务启动后，访问API文档：http://localhost:5000/api/docs
- 调用`/api/video_recreation`端点触发视频生成流程

### 4.2 使用测试脚本
```bash
# 在项目根目录执行
python -m backend.tests.test_full_video_workflow
```

## 5. 流程监控

- 查看日志输出了解各阶段执行情况
- 监控ComfyUI服务状态
- 检查生成的视频文件

## 6. 预期结果

- ✅ 抖音爬虫服务启动成功
- ✅ 后端服务启动成功
- ✅ 数据库初始化成功
- ✅ 视频生成流程执行完成
- ✅ 生成最终视频文件

## 7. 常见问题排查

- **爬虫服务启动失败**：检查爬虫目录是否存在，依赖是否正确安装
- **后端服务启动失败**：检查数据库连接配置，确保MySQL服务正常运行
- **视频生成失败**：检查ComfyUI服务是否正常，工作流配置是否正确
- **一致性检验失败**：调整一致性阈值或优化提示词

## 8. 后续优化建议

- 根据实际生成结果调整工作流参数
- 优化提示词以提高生成质量
- 增加更多测试用例覆盖不同场景
- 监控系统性能，优化资源使用

## 9. 输出文件位置

- 生成的视频文件：`output/videos/`目录
- 日志文件：`logs/agent_system.log`
- 数据库文件：`instance/video_agent.db`（SQLite）

## 10. 技术栈

- **Web框架**：Flask + FastAPI
- **视频处理**：MoviePy
- **图像处理**：Pillow, numpy
- **AI模型**：ComfyUI (Flux, Wan2.1)
- **数据库**：MySQL
- **异步处理**：aiohttp

该计划将指导您完成项目的完整运行流程，从服务启动到视频生成的整个过程。