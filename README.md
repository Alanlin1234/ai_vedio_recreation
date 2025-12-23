# AI视频生成系统说明文档

## 1. 项目概述

AI视频生成系统是一个基于AI技术的端到端视频创作平台，能够自动从输入视频生成完整的视频作品。系统整合了视频分析、关键帧提取、内容生成、视频合成等全流程功能，实现了AI辅助的自动化视频创作。

## 2. 核心功能

### 2.1 端到端视频处理流程

- **视频切片**：将输入视频分割成多个片段，分离音频和视频
- **视频分析**：使用AI模型分析视频内容和提取关键帧
- **提示词生成与优化**：基于视频分析结果生成和优化场景提示词
- **场景视频生成**：根据提示词生成关键帧和视频片段
- **一致性检查**：确保生成的视频内容与原视频保持一致
- **音频合成**：为生成的视频添加语音解说
- **最终视频合成**：将所有场景视频和音频合成完整视频

### 2.2 技术亮点

- 支持多种AI模型：qwen-omni-turbo、qwen3-vl-plus、qwen-image-edit
- 自动化关键帧传递，保持场景连贯性
- 实时一致性检查和优化
- 灵活的视频切片和合成策略
- 支持多种视频格式和分辨率

## 3. 技术栈

| 类别 | 技术/框架 | 用途 |
|------|----------|------|
| 后端框架 | Flask | 应用服务 |
| AI模型调用 | qwen系列模型 | 视频分析、内容生成 |
| 视频处理 | FFmpeg | 视频切片、合成、音频处理 |
| 异步编程 | asyncio | 异步任务处理 |
| JSON解析 | 自定义JSON解析器 | 提示词解析和处理 |
| 一致性检查 | 自定义一致性代理 | 生成内容一致性验证 |

## 4. 目录结构

```
backend/
├── app/                     # 主应用目录
│   ├── __init__.py          # 应用初始化
│   ├── agents/              # AI代理实现
│   │   ├── consistency_agent.py # 一致性检查代理
│   ├── services/            # 业务服务
│   │   ├── ffmpeg_service.py # FFmpeg视频处理服务
│   │   ├── qwen_vl_service.py # Qwen-VL视频分析服务
│   │   ├── qwen_video_service.py # Qwen视频生成服务
│   │   ├── content_generation_service.py # 内容生成服务
│   │   ├── scene_segmentation_service.py # 场景分割服务
│   │   └── json_prompt_parser.py # JSON提示词解析器
│   ├── routes/              # API路由
│   └── utils/               # 工具类
├── config.py                # 配置文件
├── run.py                   # 应用入口
└── requirements.txt         # 依赖列表
```

## 5. 安装和依赖

### 5.1 环境准备

1. 安装Python 3.10+
2. 安装FFmpeg并添加到系统路径
3. 安装ComfyUI（用于视频生成）
4. 安装MySQL数据库

### 5.2 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 5.3 配置文件

1. 复制`.env.example`为`.env`
2. 配置数据库连接
3. 配置ComfyUI地址
4. 配置AI模型API密钥

## 6. 使用说明

### 6.1 启动应用

```bash
cd backend
python run.py
```

应用将在 http://0.0.0.0:5000 启动

### 6.2 运行视频处理流程

使用`test_simple_video_process.py`脚本可以运行完整的视频处理流程：

```bash
python test_simple_video_process.py <视频文件路径>
```

例如：
```bash
python test_simple_video_process.py downloads/抖音20251216-605430.mp4
```

## 7. 工作流程详细说明

### 7.1 视频处理工作流

1. **初始化**：创建工作流实例，初始化各服务组件
2. **视频切片**：将输入视频分割成多个片段，分离音频和视频
3. **视频分析**：
   - 使用qwen-omni-turbo分析视频内容
   - 提取关键帧
   - 使用qwen3-vl-plus分析关键帧
4. **提示词生成与优化**：
   - 结合分析结果生成基础提示词
   - 使用qwen-plus-latest优化提示词
5. **JSON提示词解析**：解析和验证提示词格式
6. **场景视频生成**：
   - 使用qwen-image-edit生成关键帧
   - 使用wan2.5从关键帧生成视频
   - 进行一致性检查
7. **音频合成**：为生成的视频添加语音解说
8. **最终视频合成**：将所有场景视频和音频合成完整视频

### 7.2 关键帧传递机制

系统采用关键帧传递机制，确保生成的视频场景之间保持连贯：

1. 从每个视频切片提取关键帧
2. 将当前场景的关键帧传递给下一个场景
3. 在下一个场景生成时，参考上一个场景的关键帧
4. 实时进行一致性检查，确保场景过渡自然

## 8. 核心功能模块

### 8.1 FFmpegService

提供视频处理的核心功能：
- 视频信息获取
- 视频切片（支持音频分离）
- 关键帧提取
- 视频下载
- 音频-视频同步
- 视频合成

### 8.2 QwenVLService

使用qwen-omni-turbo模型分析视频内容：
- 视频内容理解
- 场景识别
- 关键信息提取

### 8.3 QwenVideoService

负责视频生成相关功能：
- 关键帧生成（使用qwen-image-edit）
- 从关键帧生成视频（使用wan2.5）
- 视频分析和优化

### 8.4 ContentGenerationService

负责内容生成：
- 提示词优化
- 文本转语音
- 脚本生成

### 8.5 JSONPromptParser

自定义JSON解析器，处理各种可能的JSON格式错误：
- 严格模式和宽松模式
- 支持多种JSON格式变体
- 自动修复常见错误

### 8.6 ConsistencyAgent

确保生成的视频内容与原视频保持一致：
- 内容一致性检查
- 风格一致性检查
- 时序一致性检查
- 自动优化建议

## 9. API参考

### 9.1 主要API端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/agent` | POST | 端到端视频创建 |
| `/api/videos` | GET | 获取视频列表 |
| `/api/videos/<id>` | GET | 获取视频详情 |
| `/api/videos` | POST | 创建新视频 |
| `/api/videos/<id>` | PUT | 更新视频信息 |
| `/api/videos/<id>` | DELETE | 删除视频 |

### 9.2 请求示例

```json
{
  "video_url": "https://example.com/input_video.mp4",
  "slice_count": 5,
  "parameters": {
    "resolution": "1920x1080",
    "frame_rate": 24,
    "consistency_threshold": 0.8
  }
}
```

## 10. 配置说明

### 10.1 主要配置项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `FFMPEG_PATH` | FFmpeg可执行文件路径 | `ffmpeg` |
| `COMFYUI_URL` | ComfyUI服务地址 | `http://127.0.0.1:8188` |
| `QWEN_API_KEY` | Qwen模型API密钥 | - |
| `DEFAULT_FRAME_RATE` | 默认帧率 | 24 |
| `DEFAULT_RESOLUTION` | 默认分辨率 | `1920x1080` |
| `CONSISTENCY_THRESHOLD` | 一致性阈值 | 0.8 |

### 10.2 环境变量配置

```
# 数据库配置
DATABASE_URL=mysql://user:password@localhost:3306/video_agent

# ComfyUI配置
COMFYUI_URL=http://127.0.0.1:8188

# AI模型配置
QWEN_API_KEY=your_api_key
```

## 11. 常见问题和解决方案

### 11.1 视频生成失败

**问题**：场景视频生成失败
**解决方案**：
- 检查AI模型API密钥是否正确
- 确保ComfyUI服务正常运行
- 检查提示词格式是否正确
- 调整视频生成参数（分辨率、帧率等）

### 11.2 一致性检查失败

**问题**：生成的视频一致性检查失败
**解决方案**：
- 降低一致性阈值
- 调整提示词，增加更多细节描述
- 增加参考关键帧数量
- 调整视频生成参数

### 11.3 视频合成失败

**问题**：最终视频合成失败
**解决方案**：
- 检查FFmpeg是否正确安装
- 确保所有场景视频都成功生成
- 检查视频格式是否支持
- 调整合成参数

## 12. 贡献指南

1. Fork仓库
2. 创建功能分支
3. 提交代码
4. 运行测试
5. 提交Pull Request

## 13. 许可证

MIT License

## 14. 联系方式

- 项目地址：https://github.com/Alanlin1234/ai-agent-comfy
- 问题反馈：GitHub Issues

## 15. 更新日志

### v1.0.0 (2025-12-23)

- 初始版本
- 实现完整的视频处理工作流
- 支持多种AI模型
- 实现关键帧传递机制
- 支持一致性检查和优化

---

**注**：本系统需要配置AI模型API密钥才能正常运行。请确保在使用前完成所有配置。