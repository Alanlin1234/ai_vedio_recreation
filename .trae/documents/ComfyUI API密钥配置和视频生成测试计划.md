# ComfyUI工作流配置和视频生成测试计划

## 1. 需求分析

用户提供了两个ComfyUI工作流文件：
- `FLUX_GGUF_WORKFLOW .json`：用于Flux模型生成关键帧
- `wan2.1_t2v.json`：用于wan2.1模型生成视频

需要将这些工作流配置到项目中，并测试视频生成功能。

## 2. 配置结构分析

从当前代码分析：
- 项目使用`comfyui_flux_workflow.py`配置Flux工作流
- 工作流需要以API格式保存，并粘贴到`FLUX_WORKFLOW_TEMPLATE`中
- 需要配置`FLUX_NODES`指定各个节点ID
- 目前没有wan2.1模型的工作流配置文件
- `comfyui_manager.py`负责统一管理ComfyUI的配置和调用

## 3. 实施计划

### 3.1 配置Flux工作流

1. 将`FLUX_GGUF_WORKFLOW .json`内容粘贴到`comfyui_flux_workflow.py`的`FLUX_WORKFLOW_TEMPLATE`中
2. 配置`FLUX_NODES`，指定各个节点ID
3. 更新Flux默认参数

### 3.2 配置wan2.1工作流

1. 创建新文件`comfyui_wan21_workflow.py`
2. 将`wan2.1_t2v.json`内容粘贴到新文件中
3. 配置wan2.1工作流节点
4. 添加wan2.1默认参数
5. 实现获取wan2.1工作流的函数

### 3.3 更新ComfyUI管理器

1. 修改`comfyui_manager.py`，添加wan2.1工作流支持
2. 在`build_workflow`方法中添加wan2.1工作流配置
3. 在`execute_workflow`方法中添加wan2.1模型支持

### 3.4 更新配置文件

1. 在`config.py`中添加wan2.1模型配置
2. 更新`COMFYUI_CONFIG`，包含wan2.1相关配置

### 3.5 测试视频生成

1. 运行测试脚本，验证视频生成功能
2. 检查日志，确保工作流被正确加载
3. 验证生成的视频质量

## 4. 具体实施步骤

### 步骤1：配置Flux工作流

```python
# 更新comfyui_flux_workflow.py
import json

# 读取用户提供的Flux工作流文件
with open('d:/ai-agent-comfy/FLUX_GGUF_WORKFLOW .json', 'r', encoding='utf-8') as f:
    FLUX_WORKFLOW_TEMPLATE = json.load(f)

# 配置Flux节点
FLUX_NODES = {
    "model_loader": "4",           # Flux模型加载节点
    "positive_prompt": "6",        # 正向提示词
    "negative_prompt": "7",        # 负向提示词
    "sampler": "3",                # 采样器
    "latent_image": "5",           # 空白潜在图像
    "vae_decode": "8",             # VAE解码
    "save_image": "9",             # 保存图像
}
```

### 步骤2：创建wan2.1工作流配置文件

```python
# 创建comfyui_wan21_workflow.py
import json

# 读取用户提供的wan2.1工作流文件
with open('d:/ai-agent-comfy/wan2.1_t2v.json', 'r', encoding='utf-8') as f:
    WAN21_WORKFLOW_TEMPLATE = json.load(f)

# wan2.1工作流节点配置
WAN21_NODES = {
    "model_loader": "39",          # wan2.1模型加载节点
    "positive_prompt": "42",       # 正向提示词
    "negative_prompt": "43",       # 负向提示词
    "sampler": "48",               # 采样器
    "latent_image": "50",          # 空白潜在图像
    "vae_decode": "39",            # VAE解码
    "save_animated": "28",         # 保存动画
}

# wan2.1默认参数
WAN21_DEFAULT_PARAMS = {
    "model_name": "wan_2.1.safetensors",
    "width": 1024,
    "height": 576,
    "steps": 30,
    "cfg_scale": 7.5,
    "sampler_name": "euler",
    "scheduler": "simple",
    "denoise": 1.0,
    "negative_prompt": "low quality, blurry, distorted, watermark, text",
}

def get_wan21_workflow(
    positive_prompt: str,
    shot_id: int,
    **kwargs
) -> dict:
    """获取配置好的wan2.1工作流"""
    import copy
    
    workflow = copy.deepcopy(WAN21_WORKFLOW_TEMPLATE)
    
    if not workflow:
        raise ValueError("wan2.1工作流未配置！")
    
    # 获取参数
    width = kwargs.get("width", WAN21_DEFAULT_PARAMS["width"])
    height = kwargs.get("height", WAN21_DEFAULT_PARAMS["height"])
    steps = kwargs.get("steps", WAN21_DEFAULT_PARAMS["steps"])
    cfg_scale = kwargs.get("cfg_scale", WAN21_DEFAULT_PARAMS["cfg_scale"])
    negative_prompt = kwargs.get("negative_prompt", WAN21_DEFAULT_PARAMS["negative_prompt"])
    seed = kwargs.get("seed", -1)
    
    # 修改正向提示词
    positive_node = WAN21_NODES.get("positive_prompt")
    if positive_node and positive_node in workflow:
        workflow[positive_node]["inputs"]["text"] = positive_prompt
    
    # 修改负向提示词
    negative_node = WAN21_NODES.get("negative_prompt")
    if negative_node and negative_node in workflow:
        workflow[negative_node]["inputs"]["text"] = negative_prompt
    
    # 修改采样器参数
    sampler_node = WAN21_NODES.get("sampler")
    if sampler_node and sampler_node in workflow:
        workflow[sampler_node]["inputs"]["seed"] = seed
        workflow[sampler_node]["inputs"]["steps"] = steps
        workflow[sampler_node]["inputs"]["cfg"] = cfg_scale
    
    # 修改图像尺寸
    size_node = WAN21_NODES.get("latent_image")
    if size_node and size_node in workflow:
        workflow[size_node]["inputs"]["width"] = width
        workflow[size_node]["inputs"]["height"] = height
    
    return workflow
```

### 步骤3：更新comfyui_manager.py

```python
# 在build_workflow方法中添加wan2.1工作流支持
if workflow_type == 'wan21':
    # 使用wan2.1工作流
    from comfyui_wan21_workflow import get_wan21_workflow
    
    comfyui_workflow = get_wan21_workflow(
        prompt=prompt,
        shot_id=shot_id,
        width=config['width'],
        height=config['height'],
        steps=config['steps'],
        cfg_scale=config['cfg_scale'],
        negative_prompt=config['negative_prompt'],
        seed=seed
    )
    
    self.logger.info(f"已构建 wan2.1 工作流 (镜头 {shot_id})")
```

### 步骤4：更新config.py

```python
# 在Config类中添加
# wan2.1模型配置
WAN21_DEFAULT_CONFIG = {
    'type': 'wan21',
    'width': 1024,
    'height': 576,
    'steps': 30,
    'cfg_scale': 7.5,
    'negative_prompt': 'low quality, blurry, distorted, watermark, text',
    'style_prefix': 'cinematic, high quality, detailed, professional lighting',
    'use_controlnet': False,
}

# 更新workflow_config
self.workflow_config = {
    'flux': {
        # 现有配置...
    },
    'standard': {
        # 现有配置...
    },
    'wan21': {
        'width': self.config.get('wan21_width', 1024),
        'height': self.config.get('wan21_height', 576),
        'steps': self.config.get('wan21_steps', 30),
        'cfg_scale': self.config.get('wan21_cfg_scale', 7.5),
        'negative_prompt': self.config.get('wan21_negative_prompt', 'low quality, blurry, distorted'),
        'style_prefix': self.config.get('wan21_style_prefix', 'cinematic, high quality, detailed'),
        'use_controlnet': self.config.get('wan21_use_controlnet', False)
    }
}
```

### 步骤5：测试视频生成

1. 运行测试脚本：`python backend/tests/test_video_generation.py`
2. 检查日志，确保工作流被正确加载
3. 验证生成的视频质量

## 5. 预期效果

- 成功配置Flux和wan2.1工作流
- 视频生成功能正常工作
- 生成的视频质量符合预期

## 6. 具体实施步骤

### 步骤1：配置Flux工作流
1. 将`FLUX_GGUF_WORKFLOW .json`内容粘贴到`comfyui_flux_workflow.py`
2. 配置`FLUX_NODES`节点ID

### 步骤2：创建wan2.1工作流配置
1. 创建`comfyui_wan21_workflow.py`文件
2. 将`wan2.1_t2v.json`内容粘贴到文件中
3. 配置`WAN21_NODES`节点ID

### 步骤3：更新comfyui_manager.py
1. 添加wan2.1工作流支持
2. 更新build_workflow方法

### 步骤4：更新config.py
1. 添加wan2.1模型配置
2. 更新workflow_config

### 步骤5：测试视频生成
1. 运行测试脚本
2. 检查日志
3. 验证生成的视频

## 7. 风险评估

- 节点ID配置错误：通过日志检查和调试解决
- 工作流格式不兼容：确保使用API格式导出的工作流
- 模型文件缺失：确保ComfyUI服务器已安装相应模型

## 8. 后续优化

- 添加工作流验证机制
- 支持动态切换工作流
- 实现工作流版本管理

## 9. 实施时间

预计需要2-3小时完成配置和测试。