# 影坊 · AI 视频二创工作台

基于 Flask + React（Vite）的端到端流水线：上传视频 → 解析（教育专家）→ 审核 → 二创新故事（故事编剧）→ 分镜与分镜图（分镜导演）→ 分场景视频（视频生成）→ 拼接与导出（视频合成）。

## 技术栈概览

| 层级 | 技术 |
|------|------|
| 后端 | Flask、Flask-SQLAlchemy（SQLite）、Flask-CORS、会话登录 |
| 前端 | React 18、React Router 6、Vite 4、Tailwind CSS、axios、@vitejs/plugin-react-swc |
| AI | 阿里云 DashScope（qwen-vl-plus、qwen-plus、qwen-image-2.0、视频生成 API 等） |
| 媒体 | FFmpeg（服务端调用）、可选 MoviePy（部分 Agent） |
| 一致性模块 | `video_consistency_agent/`（YAML + OpenCV 等） |

## 目录说明（核心）

```
backend/                 # Flask 应用
  app/
    routes/              # frontend_pipeline、auth、review、agent 等
    services/            # 解析、编剧、分镜、视频、审核等
    utils/prompt_trace.py  # 调试：各步骤提示词追踪
  config.py
  requirements.txt
  run.py                 # 本地启动入口

frontend/                # Vite + React 工作台与落地页
  package.json
  postcss.config.cjs
  public/

video_consistency_agent/ # 分镜视频一致性检查（被 pipeline 引用）
```

## 环境要求

- **Python** 3.10+
- **Node.js** 建议 18+（Vite 与部分依赖对 16 会告警）
- **FFmpeg** 在系统 PATH 中（拼接、转码等）
- 阿里云 **DASHSCOPE_API_KEY**（或通过环境变量注入）

数据库默认为项目内的 **SQLite**（`sqlite:///video_agent.db`），无需单独安装 MySQL。

## 后端安装与启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

服务默认：`http://127.0.0.1:5000`。API 前缀示例：`/api/pipeline`、`/api/auth`、`/api/reviewer`。

## 前端安装与启动

```bash
cd frontend
npm install
npm run dev
```

开发地址：`http://127.0.0.1:3000`（`vite.config.js` 将 `/api` 代理到后端，需与后端同源策略、Cookie 登录一致）。

生产构建：`npm run build`，静态资源在 `frontend/dist/`。

## 主要 API（影坊流水线）

| 说明 | 方法 | 路径 |
|------|------|------|
| 上传视频 | POST | `/api/pipeline/upload-video` |
| 解析视频 | POST | `/api/pipeline/analyze-video/<id>` |
| 二创审核 | POST | `/api/reviewer/<id>` |
| 新故事 | POST | `/api/pipeline/generate-new-story/<id>` |
| 分镜 | POST | `/api/pipeline/generate-storyboard/<id>` |
| 分场景视频 | POST | `/api/pipeline/generate-scene-videos/<id>` |
| 拼接成片 | POST | `/api/pipeline/combine-video/<id>` |
| 登录等 | - | `/api/auth/*` |

