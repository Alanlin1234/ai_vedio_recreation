"""
ComfyUI 工作流配置模板

使用说明：
1. 在 ComfyUI 界面中设计你的工作流
2. 点击 "Save (API Format)" 导出 API 格式的 JSON
3. 将导出的 JSON 复制到下面的 COMFYUI_WORKFLOW 字典中
4. 标记需要动态修改的节点（如提示词节点）
5. 在 image_generation_agent.py 的 _build_comfyui_workflow 方法中使用这个配置
"""

# ============================================================
# 在这里放置你的 ComfyUI 工作流 JSON
# ============================================================

# 示例工作流（基础文生图）
COMFYUI_WORKFLOW_EXAMPLE = {
    "3": {
        "inputs": {
            "seed": -1,  # -1 表示随机种子
            "steps": 30,
            "cfg": 7.5,
            "sampler_name": "euler_a",
            "scheduler": "normal",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
            "ckpt_name": "sd_xl_base_1.0.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
            "width": 1024,
            "height": 576,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "PLACEHOLDER_POSITIVE_PROMPT",  # 这里会被动态替换
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
            "text": "low quality, blurry, distorted",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "ComfyUI",  # 这里会被动态替换
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}

# ============================================================
# 你的实际工作流（从 ComfyUI 导出后粘贴到这里）
# ============================================================

COMFYUI_WORKFLOW = {
    # TODO: 在这里粘贴你从 ComfyUI 导出的工作流 JSON
    # 例如：
    # "3": {...},
    # "4": {...},
    # ...
}

# ============================================================
# 工作流配置说明
# ============================================================

# 需要动态修改的节点 ID（根据你的工作流调整）
DYNAMIC_NODES = {
    "positive_prompt_node": "6",  # 正向提示词节点 ID
    "negative_prompt_node": "7",  # 负向提示词节点 ID
    "save_image_node": "9",       # 保存图像节点 ID
    "seed_node": "3",             # 种子节点 ID（KSampler）
    "size_node": "5",             # 图像尺寸节点 ID
}

# 默认参数
DEFAULT_PARAMS = {
    "width": 1024,
    "height": 576,
    "steps": 30,
    "cfg_scale": 7.5,
    "negative_prompt": "low quality, blurry, distorted, watermark, text",
}


def get_workflow_with_params(positive_prompt: str, shot_id: int, **kwargs) -> dict:
    """
    获取带参数的工作流
    
    Args:
        positive_prompt: 正向提示词
        shot_id: 镜头 ID
        **kwargs: 其他参数（如 width, height, steps 等）
        
    Returns:
        配置好的工作流字典
    """
    import copy
    
    # 深拷贝工作流，避免修改原始配置
    workflow = copy.deepcopy(COMFYUI_WORKFLOW if COMFYUI_WORKFLOW else COMFYUI_WORKFLOW_EXAMPLE)
    
    # 获取节点 ID
    positive_node = DYNAMIC_NODES.get("positive_prompt_node")
    negative_node = DYNAMIC_NODES.get("negative_prompt_node")
    save_node = DYNAMIC_NODES.get("save_image_node")
    seed_node = DYNAMIC_NODES.get("seed_node")
    size_node = DYNAMIC_NODES.get("size_node")
    
    # 修改正向提示词
    if positive_node and positive_node in workflow:
        workflow[positive_node]["inputs"]["text"] = positive_prompt
    
    # 修改负向提示词
    if negative_node and negative_node in workflow:
        negative_prompt = kwargs.get("negative_prompt", DEFAULT_PARAMS["negative_prompt"])
        workflow[negative_node]["inputs"]["text"] = negative_prompt
    
    # 修改文件名前缀
    if save_node and save_node in workflow:
        workflow[save_node]["inputs"]["filename_prefix"] = f"shot_{shot_id}"
    
    # 修改种子（如果指定）
    if seed_node and seed_node in workflow:
        seed = kwargs.get("seed", -1)
        workflow[seed_node]["inputs"]["seed"] = seed
    
    # 修改图像尺寸
    if size_node and size_node in workflow:
        width = kwargs.get("width", DEFAULT_PARAMS["width"])
        height = kwargs.get("height", DEFAULT_PARAMS["height"])
        workflow[size_node]["inputs"]["width"] = width
        workflow[size_node]["inputs"]["height"] = height
    
    # 修改采样步数
    if seed_node and seed_node in workflow:
        steps = kwargs.get("steps", DEFAULT_PARAMS["steps"])
        if "steps" in workflow[seed_node]["inputs"]:
            workflow[seed_node]["inputs"]["steps"] = steps
    
    # 修改 CFG Scale
    if seed_node and seed_node in workflow:
        cfg = kwargs.get("cfg_scale", DEFAULT_PARAMS["cfg_scale"])
        if "cfg" in workflow[seed_node]["inputs"]:
            workflow[seed_node]["inputs"]["cfg"] = cfg
    
    return workflow


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 测试工作流配置
    test_workflow = get_workflow_with_params(
        positive_prompt="电影风格，城市夜景，霓虹灯，赛博朋克",
        shot_id=1,
        width=1024,
        height=576,
        steps=30,
        cfg_scale=7.5
    )
    
    import json
    print("生成的工作流配置：")
    print(json.dumps(test_workflow, indent=2, ensure_ascii=False))
