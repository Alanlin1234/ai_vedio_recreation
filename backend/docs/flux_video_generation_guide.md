# Flux 视频生成指南

本指南介绍如何使用 Flux 工作流生成高质量、风格一致的视频关键帧。

## 功能特点

### 1. Flux 工作流集成
- 使用 Flux 模型生成高质量关键帧
- 支持风格 LoRA 确保视频风格一致
- 支持 ControlNet 参考图控制
- 优化的提示词构建策略

### 2. 视频一致性检查
- **场景一致性阈值：0.85**
- 自动检测风格、角色、场景的一致性
- 详细的一致性报告和问题诊断

### 3. 自动重新生成机制
- 一致性低于 0.85 的场景自动重新生成
- 最多重试 3 次
- 每次重试优化提示词和生成参数
- 智能调整 CFG Scale 和采样步数

## 核心文件

- `app/agents/regeneration_agent.py` - 重新生成代理
- `comfyui_flux_workflow.py` - Flux 工作流配置
- `app/agents/image_generation_agent.py` - 图像生成代理（已支持 Flux）
- `app/agents/consistency_agent.py` - 一致性检查代理
- `app/agents/orchestrator.py` - 编排器（已集成重新生成）

## 配置步骤

### 步骤 1: 配置 Flux 工作流

1. 在 ComfyUI 中设计你的 Flux 工作流
2. 导出 API 格式的 JSON（点击 "Save (API Format)"）
3. 将 JSON 粘贴到 `backend/comfyui_flux_workflow.py` 的 `FLUX_WORKFLOW_TEMPLATE` 中
4. 更新 `FLUX_NODES` 配置，指定各节点的 ID

```python
# 示例配置
FLUX_NODES = {
    "model_loader": "4",           # Flux 模型加载节点
    "positive_prompt": "6",        # 正向提示词
    "negative_prompt": "7",        # 负向提示词
    "sampler": "3",                # 采样器
    "latent_image": "5",           # 空白潜在图像
    "vae_decode": "8",             # VAE 解码
    "save_image": "9",             # 保存图像
}
```

### 步骤 2: 配置风格参数

在调用 API 时，传入 Flux 配置：

```python
workflow_config = {
    'type': 'flux',                    # 使用 Flux 工作流
    'width': 1024,
    'height': 576,
    'steps': 25,                       # Flux 推荐 20-30 步
    'cfg_scale': 3.5,                  # Flux 推荐 1.5-4.0
    'style_prefix': 'cinematic, high quality, detailed, professional lighting',
    'style_lora': 'your_style_lora.safetensors',  # 可选：风格 LoRA
    'style_lora_strength': 0.8,
    'use_controlnet': False,           # 是否使用 ControlNet
    'negative_prompt': 'low quality, blurry, distorted, inconsistent style'
}
```

### 步骤 3: 配置一致性检查

在 `config.py` 中配置一致性参数：

```python
CONSISTENCY_CONFIG = {
    'threshold': 0.85,                 # 场景一致性阈值
    'max_retries': 3,                  # 最大重试次数
    
    # 可选：配置图像分析 API
    'vision_api_key': '',              # 留空则使用启发式方法
    'vision_api_endpoint': '',
    'face_api_key': '',
    'face_api_endpoint': '',
    'quality_api_key': '',
    'quality_api_endpoint': ''
}
```

## 使用方法

### 通过 API 调用

```python
import requests

# 启动视频生成
response = requests.post('http://localhost:5000/api/agent/create-video', json={
    'keywords': ['科技', '未来'],
    'style': 'cinematic',
    'duration': 60,
    'comfyui_workflow': {
        'type': 'flux',
        'width': 1024,
        'height': 576,
        'steps': 25,
        'cfg_scale': 3.5,
        'style_prefix': 'cinematic, high quality, detailed',
        'style_lora': None  # 可选：指定风格 LoRA 文件名
    },
    'retry_failed': True  # 启用自动重新生成
})

result = response.json()
```

## 工作流程

```
1. 热点获取
   ↓
2. 脚本拆解
   ↓
3. 分镜规划
   ↓
4. 参考图选取
   ↓
5. 图像生成 (Flux)
   ↓
6. 一致性检查 (阈值: 0.85)
   ↓
   ├─ 通过 → 继续
   └─ 失败 → 重新生成 (最多 3 次)
      ├─ 优化提示词
      ├─ 调整 CFG Scale
      ├─ 增加采样步数
      └─ 重新检查
   ↓
7. 视频合成
```

## 一致性检查详情

### 检查维度（7 个维度）

1. **颜色相似度**（权重 20%）
   - RGB 颜色分布
   - 色调、饱和度、亮度
   - 使用余弦相似度算法

2. **风格相似度**（权重 25%）
   - 艺术风格特征
   - 渲染风格、视觉质感
   - 使用风格特征向量比较

3. **构图相似度**（权重 15%）
   - 主体位置、三分法
   - 视觉重心、对称性、平衡性
   - 使用多维度构图特征比较

4. **纹理相似度**（权重 10%）
   - 表面纹理、材质质感
   - 细节层次、纹理方向
   - 使用纹理特征相关系数

5. **光照相似度**（权重 15%）
   - 平均亮度、光源方向
   - 阴影强度、高光区域、色温
   - 使用多维度光照特征比较

6. **对比度相似度**（权重 8%）
   - 整体对比度、色彩饱和度
   - 动态范围、色调分布
   - 使用对比度特征比较

7. **边缘相似度**（权重 7%）
   - 边缘检测结果、轮廓特征
   - 边缘密度、边缘方向
   - 使用汉明距离或欧氏距离

**详细算法说明**: 参考 [一致性算法详解](./consistency_algorithm_details.md)

### 一致性阈值

- **0.85+**: 通过，直接使用
- **0.70-0.85**: 重新生成
- **<0.70**: 多次重新生成

### 重新生成策略

#### 第 1 次重试
- 添加基础风格约束关键词
- CFG Scale 降低 0.5
- 提示词：`consistent style, uniform lighting`

#### 第 2 次重试
- 增强风格约束
- CFG Scale 降低 1.0
- 采样步数 +5
- 提示词：`highly consistent style, matching color palette, uniform lighting`

#### 第 3 次重试
- 最强风格约束
- CFG Scale 降低 1.5
- 采样步数 +10
- 提示词：`extremely consistent style, identical color grading, perfectly matching lighting`

## 风格模板

系统在 `comfyui_flux_workflow.py` 中提供了预定义的风格模板：
- **电影风格 (cinematic)**: 电影感、胶片颗粒、戏剧性光照
- **动漫风格 (anime)**: 赛璐璐着色、鲜艳色彩、清晰线条
- **写实风格 (realistic)**: 照片级真实、自然光照、锐利对焦
- **艺术风格 (artistic)**: 绘画感、风格化、创意构图

使用方法：在 `comfyui_flux_workflow.py` 中调用 `get_style_config(style_name)` 获取配置。

## API 配置（可选）

如果需要更精确的一致性检查，可以在 `config.py` 的 `CONSISTENCY_CONFIG` 中配置图像分析 API：
- Google Cloud Vision API
- AWS Rekognition
- Azure Computer Vision

**注意**: 如果不配置 API，系统会使用启发式方法进行一致性检查（基于提示词分析）。

## 输出结果

成功时返回视频路径和各阶段统计信息，包括：
- 生成的图像数量
- 一致性得分和通过率
- 重新生成统计（如果有）
- 最终视频路径和时长

## 故障排除

### Flux 工作流未配置
在 ComfyUI 中导出 Flux 工作流，粘贴到 `comfyui_flux_workflow.py` 的 `FLUX_WORKFLOW_TEMPLATE`，并更新 `FLUX_NODES` 配置。

### 一致性不达标
1. 使用风格 LoRA
2. 降低一致性阈值（config.py 中的 `AGENT_CONSISTENCY_THRESHOLD`）
3. 增加重试次数（`AGENT_MAX_RETRIES`）
4. 优化提示词，添加更强的风格约束

### 生成速度慢
1. 减少采样步数（20-25 步）
2. 降低图像分辨率
3. 禁用 ControlNet（如果不需要）

## 最佳实践

### 提示词设计
- 在所有镜头中使用统一的风格前缀
- 避免在不同镜头中使用冲突的风格关键词
- 使用详细的场景描述

### 参数调优
- Flux 推荐 CFG Scale: 1.5-4.0
- 采样步数: 20-30 步
- 分辨率: 1024x576 或 1024x1024

### 风格一致性
- 使用风格 LoRA（强烈推荐）
- 保持光照描述一致
- 保持色调描述一致

## 相关文档

- [一致性算法详解](./consistency_algorithm_details.md) - 详细的相似度算法说明
- [ComfyUI 集成指南](./comfyui_integration_guide.md)
- [如何调用 ComfyUI 工作流](./如何调用ComfyUI工作流.md)
- [系统架构文档](./ARCHITECTURE.md)
- [系统功能总结](./系统功能总结.md)
