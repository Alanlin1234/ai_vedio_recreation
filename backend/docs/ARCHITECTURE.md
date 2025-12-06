# 项目架构文档

## 系统概述

这是一个端到端的AI视频生成系统，从抖音热点采集到最终视频输出的完整自动化流程。

## 技术栈

- **后端框架**: Flask
- **数据库**: MySQL
- **异步处理**: asyncio, aiohttp
- **视频处理**: MoviePy
- **图像生成**: ComfyUI (外部服务)
- **AI模型**: 支持多种大模型API

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户请求                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Flask API Layer                             │
│              (agent_routes.py)                               │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              VideoCreationOrchestrator                       │
│                  (流程编排器)                                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ HotspotAgent │ │ ScriptAgent  │ │StoryboardAgent│
│  (热点采集)   │ │  (脚本拆解)   │ │  (分镜规划)   │
└──────────────┘ └──────────────┘ └──────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌────────────────────────┐ ┌────────────────────────┐
│ImageGenerationAgent    │ │ConsistencyAgent        │
│ (图像生成)              │ │ (一致性检验)            │
└────────────────────────┘ └────────────────────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
              ┌──────────────┐
              │VideoSynthesis│
              │    Agent     │
              │  (视频合成)   │
              └──────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  最终视频     │
              └──────────────┘
```

## 目录结构

```
backend/
├── app/
│   ├── agents/                    # Agent系统核心
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Agent基类
│   │   ├── hotspot_agent.py       # 热点采集Agent
│   │   ├── script_agent.py        # 脚本拆解Agent
│   │   ├── storyboard_agent.py    # 分镜规划Agent
│   │   ├── image_generation_agent.py  # 图像生成Agent (ComfyUI)
│   │   ├── consistency_agent.py   # 一致性检验Agent
│   │   ├── video_synthesis_agent.py   # 视频合成Agent
│   │   ├── regeneration_agent.py  # 重新生成Agent
│   │   ├── tracking_manager.py    # 追踪管理器
│   │   └── orchestrator.py        # 流程编排器
│   │
│   ├── models/                    # 数据模型
│   │   ├── __init__.py
│   │   ├── video.py
│   │   ├── author.py
│   │   └── video_recreation.py
│   │
│   ├── routes/                    # API路由
│   │   ├── __init__.py
│   │   ├── agent_routes.py        # Agent系统API
│   │   ├── video_routes.py
│   │   ├── author_routes.py
│   │   ├── douyin_routes.py
│   │   └── video_recreation_routes.py
│   │
│   ├── services/                  # 业务服务
│   │   ├── __init__.py
│   │   ├── douyin_service.py
│   │   ├── video_service.py
│   │   ├── author_service.py
│   │   ├── data_service.py
│   │   ├── db_service.py
│   │   ├── text_to_speech_service.py
│   │   ├── video_recreation_service.py
│   │   └── video_analysis_agent.py
│   │
│   ├── utils/                     # 工具类
│   │   ├── __init__.py
│   │   ├── comfyui_manager.py     # ComfyUI配置和调用管理器
│   │   ├── config_validator.py    # 配置验证器
│   │   └── time_utils.py          # 时间工具
│   │
│   └── __init__.py                # Flask应用工厂
│
├── crawler/                       # 爬虫功能
│   └── Douyin_TikTok_Download_API-main/  # 抖音爬虫
│
├── docs/                          # 文档
│   ├── ARCHITECTURE.md
│   ├── comfyui_integration_guide.md
│   ├── consistency_algorithm_details.md
│   ├── flux_video_generation_guide.md
│   ├── IMPLEMENTATION_STATUS.md
│   ├── SYSTEM_SUMMARY.md
│   ├── 快速开始指南.md
│   └── 系统完整说明文档.md
│
├── output/                        # 输出目录
│   ├── videos/                    # 生成的视频
│   └── comfyui/                   # ComfyUI输出
│
├── references/                    # 参考图库
│
├── logs/                          # 日志文件
│
├── tests/                         # 测试代码
│   ├── test_full_video_workflow.py
│   ├── test_tracking_system.py
│   └── test_video_generation.py
│
├── config.py                      # 配置文件
├── requirements.txt               # Python依赖
├── run.py                         # 启动脚本
└── video_agent.sql                # 数据库初始化脚本
```

## Agent详细说明

### 1. BaseAgent (基类)

所有Agent的抽象基类，提供：
- 统一的执行接口 `execute()`
- 日志记录功能
- 输入验证
- 结果标准化

### 2. HotspotAgent (热点采集)

**职责**: 从抖音获取当天热点时评

**输入**:
```python
{
    'keywords': ['关键词1', '关键词2'],
    'count': 10,
    'category': '时事'
}
```

**输出**:
```python
{
    'hotspots': [...],
    'selected_hotspot': {...},
    'total_count': 10
}
```

### 3. ScriptAgent (脚本拆解)

**职责**: 分析热点内容，生成视频脚本

**输入**:
```python
{
    'hotspot': {...},
    'style': 'commentary',
    'duration': 60
}
```

**输出**:
```python
{
    'script': {...},
    'scenes': [...],
    'narration': '完整旁白文本',
    'total_scenes': 4
}
```

### 4. StoryboardAgent (分镜规划)

**职责**: 为每个场景规划镜头

**输入**:
```python
{
    'scenes': [...],
    'style': 'cinematic'
}
```

**输出**:
```python
{
    'storyboard': [...],
    'shots': [...],
    'total_shots': 12
}
```



### 6. ImageGenerationAgent (图像生成)

**职责**: 调用ComfyUI生成图像和关键帧，支持Flux模型和标准SD/SDXL模型

**输入**:
```python
{
    'shots_with_references': [...],
    'workflow': {
        'type': 'flux',  # 或 'standard'
        'width': 1024,
        'height': 576,
        'steps': 25,
        'cfg_scale': 3.5,
        'negative_prompt': 'low quality, blurry, distorted'
    },
    'batch_size': 1
}
```

**输出**:
```python
{
    'generated_images': [...],
    'total_images': 12
}
```

**关键方法**:
- `_generate_single_image()` - 生成单张图像
- `_build_comfyui_workflow()` - 构建ComfyUI工作流
- 使用 `comfyui_manager.py` 统一管理ComfyUI配置和调用
- 支持Flux模型生成关键帧和标准模型生成图像

### 7. ConsistencyAgent (一致性检验)

**职责**: 检查生成图像的一致性

**输入**:
```python
{
    'generated_images': [...],
    'storyboard': [...]
}
```

**输出**:
```python
{
    'consistency_report': {...},
    'passed_images': [...],
    'failed_images': [...],
    'overall_score': 0.92,
    'pass_rate': 0.85
}
```

**检查项**:
- 风格一致性
- 角色一致性
- 场景连贯性
- 图像质量

### 8. VideoSynthesisAgent (视频合成)

**职责**: 将所有素材合成最终视频

**输入**:
```python
{
    'passed_images': [...],
    'narration_audio': 'audio.mp3',
    'background_music': 'music.mp3',
    'output_filename': 'final.mp4'
}
```

**输出**:
```python
{
    'video_path': 'output/videos/final.mp4',
    'duration': 60.5,
    'resolution': '1920x1080',
    'fps': 30
}
```

## 数据流

```
用户输入
  ↓
热点数据 → 脚本数据 → 场景数据 → 镜头数据
  ↓         ↓          ↓          ↓
热点列表   场景列表   分镜列表   镜头+参考图
                                  ↓
                              生成图像
                                  ↓
                              一致性检验
                                  ↓
                              通过的图像
                                  ↓
                              最终视频
```

## API接口

### 创建视频

```http
POST /api/agent/create-video
Content-Type: application/json

{
  "keywords": ["AI", "科技"],
  "style": "commentary",
  "duration": 60,
  "comfyui_workflow": {},
  "output_filename": "my_video.mp4"
}
```

### 获取状态

```http
GET /api/agent/status
```

### 测试ComfyUI

```http
POST /api/agent/test-comfyui
Content-Type: application/json

{
  "comfyui_url": "http://127.0.0.1:8188"
}
```

## 配置说明

### 环境变量

```bash
# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=123456
MYSQL_DB=video_agent

# API密钥
DASHSCOPE_API_KEY=your_key
SILICONFLOW_API_KEY=your_key
OPENAI_API_KEY=your_key

# ComfyUI
COMFYUI_URL=http://127.0.0.1:8188

# Agent配置
AGENT_OUTPUT_DIR=output/videos
AGENT_CONSISTENCY_THRESHOLD=0.8
```

### config.py

主要配置项：
- 数据库连接
- API密钥
- ComfyUI URL
- 输出目录
- 一致性阈值

## 扩展性

### 添加新的Agent

1. 继承 `BaseAgent`
2. 实现 `execute()` 方法
3. 在 `orchestrator.py` 中集成
4. 更新 `__init__.py`

示例：
```python
from .base_agent import BaseAgent

class NewAgent(BaseAgent):
    def __init__(self, config=None):
        super().__init__("NewAgent", config)
    
    async def execute(self, input_data):
        # 实现逻辑
        return self.create_result(True, {...})
```

### 自定义工作流

在 `orchestrator.py` 中修改流程顺序或添加新阶段。

## 性能优化

1. **批处理**: 图像生成支持批处理
2. **异步处理**: 所有Agent使用async/await
3. **缓存**: 可添加结果缓存
4. **并行处理**: 独立任务可并行执行

## 错误处理

- 每个Agent独立处理错误
- Orchestrator统一错误处理
- 支持阶段重试
- 详细的错误日志

## 监控和日志

- 每个Agent记录执行日志
- 流程编排器记录整体进度
- 日志保存在 `logs/` 目录

## 测试

```bash
# 测试完整流程
python test_agent_system.py

# 测试单个Agent
python -c "from app.agents.hotspot_agent import HotspotAgent; import asyncio; asyncio.run(HotspotAgent().execute({}))"
```

## 部署

1. 安装依赖: `pip install -r requirements.txt`
2. 配置环境变量
3. 启动ComfyUI服务
4. 运行: `python run.py`

## 下一步开发

- [ ] 实现抖音API集成
- [ ] 接入大模型生成脚本
- [ ] 完善ComfyUI工作流
- [ ] 添加参考图检索
- [ ] 优化一致性检查算法
- [ ] 添加进度追踪
- [ ] 实现Web界面
