# 简单的Flux工作流模板，符合ComfyUI API格式

SIMPLE_FLUX_WORKFLOW = {
    "3": {
        "inputs": {
            "seed": 12345,
            "steps": 25,
            "cfg": 3.5,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
            "ckpt_name": "flux1-krea-dev_fp8_scaled.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
            "width": 1920,
            "height": 1080,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "cinematic, high quality, detailed, professional lighting, 风景, 旅行, 自然",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
            "text": "low quality, blurry, distorted, inconsistent style, watermark, text",
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
            "filename_prefix": "ComfyUI",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}

def get_simple_flux_workflow(
    positive_prompt: str,
    shot_id: int,
    width: int = 1920,
    height: int = 1080,
    steps: int = 25,
    cfg_scale: float = 4.0,  # 调整为与配置文件一致的默认值
    negative_prompt: str = "low quality, blurry, distorted, inconsistent style, watermark, text",
    **kwargs
) -> dict:
    """
    获取简单的Flux工作流，符合ComfyUI API格式
    """
    import copy
    
    # 深拷贝工作流模板
    workflow = copy.deepcopy(SIMPLE_FLUX_WORKFLOW)
    
    # 修改正向提示词
    workflow["6"]["inputs"]["text"] = positive_prompt
    
    # 修改负向提示词
    workflow["7"]["inputs"]["text"] = negative_prompt
    
    # 修改尺寸
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    
    # 修改采样参数
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["cfg"] = cfg_scale
    
    # 修改保存文件名
    workflow["9"]["inputs"]["filename_prefix"] = f"flux_shot_{shot_id}"
    
    return workflow
