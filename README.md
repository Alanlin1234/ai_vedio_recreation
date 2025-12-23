# AI视频生成系统 - 说明文档

## 1. 项目概述

AI视频生成系统是一个基于AI技术的端到端视频创作平台，能够自动从热点内容生成完整的视频作品。系统整合了热点分析、脚本生成、分镜规划、图像生成、视频合成等全流程功能，实现了AI辅助的自动化视频创作。

## 2. 核心功能

### 2.1 端到端视频创作流程
- **热点分析**：自动获取抖音热点内容
- **脚本生成**：基于热点内容生成视频脚本
- **分镜规划**：将脚本转换为分镜镜头
- **图像生成**：使用ComfyUI生成关键帧图像
- **一致性检验**：确保生成图像风格一致
- **视频合成**：将图像合成为完整视频

### 2.2 API接口
- **Agent API**：端到端视频创建接口
- **视频管理API**：视频的增删改查
- **作者管理API**：作者信息管理
- **抖音数据API**：抖音数据爬取和分析
- **视频二创API**：视频重建和二次创作

## 3. 架构设计

### 3.1 系统架构
```
┌─────────────────────────────────────────────────────────────────┐
│                       AI视频生成系统                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────────┐ │
│  │ 热点分析 │  │ 脚本生成 │  │ 分镜规划 │  │     图像生成       │ │
│  │  Agent  │  │  Agent  │  │  Agent  │  │ ┌─────────┐ ┌─────┐ │ │
│  └─────────┘  └─────────┘  └─────────┘  │ │关键帧生成│ │完整图像│ │ │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │ └─────────┘ └─────┘ │ │
│  │一致性检验│  │ 重新生成 │  │ 抖音爬取 │  │ ┌─────────┐       │ │ │
│  │  Agent  │  │  Agent  │  │ Service │  │ │风格一致性│       │ │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────────┘ │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │ │
│  │视频合成 │  │文本转语音│  │ 数据存储 │  │ 工作流管理│          │ │
│  │  Agent  │  │ Service │  │  Service │  │  Service │          │ │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  ┌─────────┘ │
│                  ┌───────────────────────────────────┐           │
│                  │           Orchestrator           │           │
│                  └───────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
        │           │           │           │           │
        └───────────┼───────────┼───────────┼───────────┘
                    ▼           ▼           ▼
            ┌─────────────────────────────────┐
            │           ComfyUI API          │
            └─────────────────────────────────┘
```

### 3.2 技术栈
- **后端框架**：Flask
- **数据库**：MySQL
- **AI模型**：通过ComfyUI调用（支持Flux、Wan21等模型）
- **API设计**：RESTful API
- **Agent系统**：基于角色的多Agent协作架构
- **工作流管理**：Orchestrator统一编排端到端流程
- **服务组件**：模块化服务设计，支持文本转语音、数据存储等功能

### 3.3 Agent系统架构

系统采用基于角色的多Agent协作架构，由Orchestrator统一编排，每个Agent负责特定的功能模块：

| Agent名称 | 功能描述 |
|-----------|----------|
| **Orchestrator** | 端到端流程编排，协调所有Agent工作 |
| **HotspotAgent** | 热点分析和内容选择，从抖音获取热点 |
| **ScriptAgent** | 脚本生成和拆解，基于热点生成结构化脚本 |
| **StoryboardAgent** | 分镜规划和镜头设计，将脚本转换为镜头序列 |
| **ImageGenerationAgent** | 图像生成和处理，调用ComfyUI生成图像 |
| **ConsistencyAgent** | 图像一致性检验，确保生成图像风格一致 |
| **RegenerationAgent** | 失败场景重新生成，对未通过检验的图像进行重试 |
| **VideoSynthesisAgent** | 视频合成和处理，将图像合成为完整视频 |

### 3.4 核心服务组件

| 服务名称 | 功能描述 |
|----------|----------|
| **TextToSpeechService** | 文本转语音服务，支持多种模型和参数配置 |
| **ComfyUIManager** | ComfyUI接口管理，负责构建和执行工作流 |
| **TrackingManager** | 流程跟踪和监控，记录系统运行状态 |
| **DatabaseService** | 数据存储和管理，保存视频、作者等信息 |
| **DouyinCrawler** | 抖音数据爬取服务，获取热点内容和用户视频 |

## 4. 目录结构

```
backend/
├── app/                     # 主应用目录
│   ├── agents/              # Agent实现
│   │   ├── orchestrator.py  # 端到端流程编排器
│   │   ├── hotspot_agent.py # 热点分析Agent
│   │   ├── script_agent.py  # 脚本生成Agent
│   │   ├── storyboard_agent.py # 分镜规划Agent
│   │   ├── image_generation_agent.py # 图像生成Agent
│   │   ├── consistency_agent.py # 一致性检验Agent
│   │   ├── video_synthesis_agent.py # 视频合成Agent
│   │   └── regeneration_agent.py # 重新生成Agent
│   ├── models/              # 数据模型
│   ├── routes/              # API路由
│   ├── services/            # 业务服务
│   └── utils/               # 工具类
├── crawler/                 # 抖音爬虫
├── .env.example             # 环境变量示例
├── config.py                # 配置文件
├── run.py                   # 应用入口
└── requirements.txt         # 依赖列表
```

## 5. 快速启动指南

### 5.1 环境准备

#### 5.1.1 安装依赖
```bash
# 进入backend目录
cd backend

# 安装Python依赖
pip install -r requirements.txt
```

#### 5.1.2 配置数据库
- 安装MySQL数据库
- 创建数据库：`video_agent`
- 配置数据库连接（在`config.py`中修改）

#### 5.1.3 配置ComfyUI
- 安装并启动ComfyUI
- 确保ComfyUI可以正常访问（默认地址：http://127.0.0.1:8188）

### 5.2 启动应用

#### 5.2.1 启动后端服务
```bash
# 进入backend目录
cd backend

# 启动Flask应用
python run.py
```

应用将在 `http://0.0.0.0:5000` 启动

#### 5.2.2 访问API
- API基础URL：`http://localhost:5000/api`
- Agent API：`http://localhost:5000/api/agent`

### 5.3 测试完整流程

#### 5.3.1 使用API创建视频
```bash
curl -X POST http://localhost:5000/api/agent/create-video \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["热点关键词"],
    "style": "commentary",
    "duration": 60,
    "output_filename": "my_video.mp4"
  }'
```

#### 5.3.2 检查生成结果
- 生成的视频将保存在 `output/videos/` 目录下
- 可以通过API获取生成状态和结果

## 6. 核心功能详细说明

### 6.1 Agent系统

Agent系统是整个平台的核心，负责协调各个组件完成端到端视频生成。

#### 6.1.1 主要Agent
| Agent名称 | 功能描述 |
|-----------|----------|
| HotspotAgent | 热点分析和内容选择 |
| ScriptAgent | 脚本生成和拆解 |
| StoryboardAgent | 分镜规划和镜头设计 |
| ImageGenerationAgent | 图像生成和处理 |
| ConsistencyAgent | 图像一致性检验 |
| VideoSynthesisAgent | 视频合成和处理 |
| RegenerationAgent | 失败场景重新生成 |

#### 6.1.2 工作流程
```
输入: 关键词列表
├─→ 阶段1: 热点分析 (HotspotAgent)
│   └─→ 从抖音获取并筛选热点内容
├─→ 阶段2: 脚本生成 (ScriptAgent)
│   └─→ 基于热点生成结构化视频脚本
├─→ 阶段3: 分镜规划 (StoryboardAgent)
│   └─→ 将脚本转换为镜头序列，定义每个镜头参数
├─→ 阶段4: 图像生成 (ImageGenerationAgent)
│   ├─→ 子阶段4.1: 关键帧生成 (Flux模型)
│   └─→ 子阶段4.2: 完整图像生成 (标准工作流)
├─→ 阶段5: 一致性检验 (ConsistencyAgent)
│   ├─→ 计算图像风格一致性
│   ├─→ 筛选通过一致性检验的图像
│   └─→ 标记未通过的图像
├─→ 阶段6: 重新生成 (RegenerationAgent)
│   ├─→ 按场景分组未通过的图像
│   ├─→ 重新生成图像
│   ├─→ 再次进行一致性检验
│   └─→ 合并通过检验的图像
└─→ 阶段7: 视频合成 (VideoSynthesisAgent)
    ├─→ 图像片段拼接
    ├─→ 音频合成 (旁白 + 背景音乐)
    └─→ 导出完整视频
```

**详细流程说明**：

1. **热点获取**：
   - 调用抖音爬虫获取热点数据
   - 根据关键词筛选相关热点
   - 选择最适合的热点内容

2. **脚本生成**：
   - 分析热点内容，提取核心信息
   - 生成结构化的视频脚本（包含场景、台词等）
   - 支持多种视频风格（commentary、narrative等）

3. **分镜规划**：
   - 为每个场景生成多个镜头
   - 定义每个镜头的参数（提示词、时长、风格等）
   - 生成完整的分镜脚本

4. **图像生成**：
   - **关键帧生成**：使用Flux模型生成高质量关键帧
   - **完整图像生成**：基于关键帧生成完整的图像序列
   - 支持批量生成和自定义工作流

5. **一致性检验**：
   - 计算图像之间的风格一致性
   - 筛选通过一致性阈值（默认0.85）的图像
   - 标记需要重新生成的图像

6. **重新生成**：
   - 对未通过一致性检验的图像进行多次尝试（默认3次）
   - 按场景分组，确保场景内图像风格一致
   - 支持动态调整生成参数

7. **视频合成**：
   - 将图像序列合成为视频片段
   - 支持添加旁白和背景音乐
   - 支持转场效果和视频特效
   - 导出高质量视频文件

### 6.2 API接口说明

#### 6.2.1 核心API

| API路径 | 方法 | 功能描述 |
|---------|------|----------|
| /api/agent/create-video | POST | 端到端创建视频 |
| /api/agent/status | GET | 获取Agent系统状态 |
| /api/videos | GET | 获取视频列表 |
| /api/videos/<video_id> | PUT | 更新视频 |
| /api/videos/<video_id> | DELETE | 删除视频 |
| /api/authors | GET | 获取作者列表 |
| /api/fetch_author_by_sec_uid | POST | 获取抖音作者信息 |
| /api/crawl_user_today_videos | POST | 爬取用户当天视频 |
| /api/videos/<video_id>/recreate | POST | 视频二创 |

#### 6.2.2 请求示例

**创建视频请求**：
```json
{
  "keywords": ["AI", "科技"],
  "style": "commentary",
  "duration": 60,
  "comfyui_workflow": {},
  "output_filename": "ai_tech_video.mp4"
}
```

## 7. 配置说明

### 7.1 核心配置文件
- **config.py**：主配置文件，包含数据库、API、Agent等配置
- **.env**：环境变量，包含API密钥等敏感信息

### 7.2 关键配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| COMFYUI_URL | ComfyUI访问地址 | http://127.0.0.1:8188 |
| AGENT_OUTPUT_DIR | 视频输出目录 | output/videos |
| AGENT_CONSISTENCY_THRESHOLD | 一致性阈值 | 0.85 |
| AGENT_MAX_RETRIES | 最大重试次数 | 3 |
| SQLALCHEMY_DATABASE_URI | 数据库连接 | mysql+pymysql://root:123456@localhost:3306/video_agent |

## 8. 常见问题排查

### 8.1 ComfyUI连接问题
- 确保ComfyUI已启动并运行
- 检查COMFYUI_URL配置是否正确
- 测试ComfyUI API是否可访问：`curl http://127.0.0.1:8188/system_stats`

### 8.2 数据库连接问题
- 检查数据库服务是否启动
- 验证数据库用户名和密码
- 确保数据库`video_agent`已创建

### 8.3 视频生成失败
- 检查日志文件（logs/agent_system.log）
- 验证API密钥配置
- 检查ComfyUI工作流配置

## 9. 开发与扩展

### 9.1 添加新Agent
1. 在`app/agents/`目录下创建新的Agent类
2. 继承`BaseAgent`基类
3. 实现`execute`方法
4. 在`orchestrator.py`中注册新Agent

### 9.2 扩展API
1. 在`app/routes/`目录下创建新的路由文件
2. 定义Blueprint和路由函数
3. 在`app/__init__.py`中注册Blueprint

## 10. 监控与维护

### 10.1 日志管理
- 日志文件：`logs/agent_system.log`
- 日志级别：可通过LOG_LEVEL配置
- 日志包含：系统运行状态、错误信息、性能指标

### 10.2 性能监控
- 可通过API获取系统状态
- 监控关键指标：视频生成时间、成功率、资源使用率

## 11. 总结

AI视频生成系统是一个功能完整的端到端视频创作平台，整合了AI技术和自动化流程，能够帮助用户快速生成高质量视频内容。系统提供了丰富的API接口，支持定制化开发和扩展，适用于各种视频创作场景。

通过本指南，您应该能够快速了解系统的核心功能和架构，并成功启动和使用系统。如果遇到问题，请参考常见问题排查部分，或查看日志文件获取详细信息。

祝您使用愉快！
