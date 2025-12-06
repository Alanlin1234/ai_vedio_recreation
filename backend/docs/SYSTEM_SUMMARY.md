# AI 视频创作 Agent 系统 - 功能总结

## 🎯 系统核心功能

这是一个**端到端的 AI 视频自动创作系统**，能够从抖音热点采集到最终视频生成的全流程自动化。

---

## 📊 核心 Agent

### 1️⃣ HotspotAgent - 热点采集
- **功能**: 从抖音获取当天热点时评
- **输入**: 关键词、数量、分类
- **输出**: 热点列表 + 选中的最佳热点
- **状态**: ⚠️ 需实现抖音 API

### 2️⃣ ScriptAgent - 脚本拆解
- **功能**: 将热点内容拆解成视频脚本和场景
- **输入**: 热点信息、风格、时长
- **输出**: 完整脚本 + 场景列表 + 旁白文本
- **状态**: ⚠️ 可接入大模型优化

### 3️⃣ StoryboardAgent - 分镜规划
- **功能**: 为每个场景规划具体镜头和拍摄参数
- **输入**: 场景列表、视觉风格
- **输出**: 分镜列表 + 镜头列表（含提示词）
- **状态**: ✅ 完成

### 4️⃣ ReferenceAgent - 关键帧生成 ⭐🆕
- **功能**: 使用 ComfyUI Flux 模型直接生成关键帧图片
- **输入**: 镜头列表、Flux 工作流配置
- **输出**: 生成的关键帧图片列表
- **状态**: ✅ 完成
- **特性**:
  - 直接使用 Flux 模型生成
  - 不再从图库中选取参考图
  - 自动构建优化的提示词
  - 支持批量生成
  - 异步处理
  - 支持风格 LoRA 和 ControlNet

### 5️⃣ ConsistencyAgent - 一致性检验 🆕
- **功能**: 检查生成图像的一致性和质量
- **输入**: 生成的图像、分镜信息
- **输出**: 一致性报告 + 通过/失败的图像
- **检查维度**: 7 个维度（颜色、风格、构图、纹理、光照、对比度、边缘）
- **阈值**: 0.85（场景一致性）
- **状态**: ✅ 完成

### 6️⃣ RegenerationAgent - 自动重新生成 🆕
- **功能**: 自动重新生成一致性不达标的场景
- **输入**: 失败的图像、原始镜头、工作流配置
- **输出**: 重新生成的图像 + 重试统计
- **特性**:
  - 最多重试 3 次
  - 智能优化提示词
  - 自动调整 CFG Scale 和采样步数
  - 按场景分组处理
- **状态**: ✅ 完成

### 7️⃣ VideoSynthesisAgent - 视频合成
- **功能**: 将所有素材合成最终视频
- **输入**: 通过检验的图像、音频、音乐
- **输出**: 最终视频文件（MP4）
- **状态**: ✅ 完成

---

## 🔄 完整工作流程

```
用户输入 (关键词、风格、时长)
    ↓
1. 热点采集 → 获取抖音热点
    ↓
2. 脚本拆解 → 生成场景和旁白
    ↓
3. 分镜规划 → 规划镜头和提示词
    ↓
4. 关键帧生成 → 使用 Flux 模型直接生成关键帧 ⭐
    ↓
5. 一致性检验 → 7 维度检查（阈值 0.85）
    ↓
    ├─ 通过 → 继续
    └─ 失败 → 5.5 自动重新生成（最多 3 次）🆕
    ↓
6. 视频合成 → 合成最终视频
    ↓
输出: final_video.mp4
```

---

## 🎬 使用示例

### 通过 API 调用（支持 Flux）

```bash
curl -X POST http://localhost:5000/api/agent/create-video \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["人工智能", "科技"],
    "style": "cinematic",
    "duration": 60,
    "comfyui_workflow": {
      "type": "flux",
      "width": 1024,
      "height": 576,
      "steps": 25,
      "cfg_scale": 3.5,
      "style_prefix": "cinematic, high quality, detailed"
    },
    "retry_failed": true
  }'
```

---

## 📁 核心文件说明

| 文件 | 作用 | 状态 |
|------|------|------|
| `base_agent.py` | Agent 基类 | ✅ |
| `orchestrator.py` | 流程编排器 | ✅ |
| `reference_agent.py` | 关键帧生成（Flux） 🆕 | ✅ |
| `regeneration_agent.py` | 自动重新生成 🆕 | ✅ |
| `consistency_agent.py` | 一致性检验（7 维度） 🆕 | ✅ |
| `video_synthesis_agent.py` | 视频合成 | ✅ |
| `hotspot_agent.py` | 热点采集 | ⚠️ |
| `script_agent.py` | 脚本拆解 | ⚠️ |
| `storyboard_agent.py` | 分镜规划 | ✅ |
| `comfyui_flux_workflow.py` | Flux 工作流配置 🆕 | ⚠️ 需填充 |

---

## ⚙️ 配置步骤

### 1. 配置 Flux 工作流（推荐）

编辑 `comfyui_flux_workflow.py`，粘贴从 ComfyUI 导出的 Flux 工作流 JSON 到 `FLUX_WORKFLOW_TEMPLATE`，并更新 `FLUX_NODES` 节点 ID。

详细步骤参考：[Flux 视频生成指南](./flux_video_generation_guide.md)

### 2. 启动 ComfyUI

```bash
cd ComfyUI
python main.py
```

### 3. 启动系统

```bash
python start_agent_system.py
```

---

## ✨ 系统特性

### 已实现 ✅

- ✅ 完整的 Agent 架构
- ✅ 端到端流程编排
- ✅ ComfyUI 异步集成
- ✅ **Flux 工作流支持** 🆕
- ✅ **直接生成关键帧（不需要参考图库）** 🆕
- ✅ **7 维度一致性检查（阈值 0.85）** 🆕
- ✅ **自动重新生成机制** 🆕
- ✅ 视频合成功能
- ✅ HTTP API 接口
- ✅ 详细日志系统
- ✅ 错误处理机制

### 待实现 ⚠️

- ⚠️ 抖音 API 集成
- ⚠️ 大模型 API 集成
- ⚠️ 图像分析 API（可选，当前使用启发式方法）

---

## 📚 相关文档

- **flux_video_generation_guide.md** - Flux 视频生成完整指南 🆕
- **consistency_algorithm_details.md** - 一致性算法详解 🆕
- **系统完整说明文档.md** - 详细的系统说明
- **如何调用ComfyUI工作流.md** - ComfyUI 技术细节
- **ComfyUI集成步骤.md** - ComfyUI 快速开始

---

## 🎯 核心优势

1. **简化流程** - 直接使用 Flux 生成关键帧，无需参考图库
2. **高质量** - Flux 模型生成高质量、风格一致的图像
3. **智能重试** - 自动检测并重新生成不达标的场景
4. **多维度检查** - 7 个维度全面评估一致性
5. **异步处理** - 高性能，不阻塞
6. **端到端** - 全流程自动化

---

## 🚀 快速开始

```bash
# 1. 配置 Flux 工作流
vim comfyui_flux_workflow.py

# 2. 启动 ComfyUI
cd ComfyUI && python main.py

# 3. 启动系统
python start_agent_system.py

# 4. 调用 API（使用 Flux）
curl -X POST http://localhost:5000/api/agent/create-video \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["AI"],
    "duration": 60,
    "comfyui_workflow": {
      "type": "flux",
      "style_prefix": "cinematic, high quality"
    },
    "retry_failed": true
  }'
```

---

## 🆕 最新更新

### v2.0 - 关键帧直接生成

- ✅ ReferenceAgent 改为使用 Flux 模型直接生成关键帧
- ✅ 移除图库依赖，简化流程
- ✅ 自动构建优化的提示词
- ✅ 支持批量生成和异步处理

### v1.5 - 一致性增强

- ✅ 7 维度一致性检查算法
- ✅ 自动重新生成机制
- ✅ 智能参数优化

---

**版本**: 2.0  
**日期**: 2025-11-10
