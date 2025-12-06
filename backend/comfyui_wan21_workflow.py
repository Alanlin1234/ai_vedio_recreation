#ComfyUI Wan2.1 工作流配置
#本配置用于视频生成场景

# ============================================================
# Wan2.1 工作流模板
# ============================================================

# 基础 Wan2.1 工作流（从用户提供的 wan2.1_t2v.json 导入）
Wan21_WORKFLOW_TEMPLATE = {
    "id": "8a815138-573d-48df-88b4-599fd7994cbb",
    "revision": 0,
    "last_node_id": 52,
    "last_link_id": 99,
    "nodes": [
        {
            "id": 39,
            "type": "VAELoader",
            "pos": [20, 250],
            "size": [330, 60],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [
                {
                    "localized_name": "vae名称",
                    "name": "vae_name",
                    "type": "COMBO",
                    "widget": {
                        "name": "vae_name"
                    },
                    "link": None
                }
            ],
            "outputs": [
                {
                    "localized_name": "VAE",
                    "name": "VAE",
                    "type": "VAE",
                    "slot_index": 0,
                    "links": [76, 99]
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.3.27",
                "Node name for S&R": "VAELoader",
                "models": [
                    {
                        "name": "wan_2.1_vae.safetensors",
                        "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors?download=true",
                        "directory": "vae"
                    }
                ]
            },
            "widgets_values": ["wan_2.1_vae.safetensors"],
            "color": "#322",
            "bgcolor": "#533"
        },
        {
            "id": 48,
            "type": "ModelSamplingSD3",
            "pos": [440, -30],
            "size": [210, 58],
            "flags": {},
            "order": 8,
            "mode": 0,
            "inputs": [
                {
                    "localized_name": "模型",
                    "name": "model",
                    "type": "MODEL",
                    "link": 94
                },
                {
                    "localized_name": "移位",
                    "name": "shift",
                    "type": "FLOAT",
                    "widget": {
                        "name": "shift"
                    },
                    "link": None
                }
            ],
            "outputs": [
                {
                    "localized_name": "模型",
                    "name": "MODEL",
                    "type": "MODEL",
                    "slot_index": 0,
                    "links": [95]
                }
            ],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.3.27",
                "Node name for S&R": "ModelSamplingSD3"
            },
            "widgets_values": [8.000000000000002]
        },
        {
            "id": 28,
            "type": "SaveAnimatedWEBP",
            "pos": [1669.1553955078125, 366.9211120605469],
            "size": [600, 492.1538391113281],
            "flags": {},
            "order": 1,
            "mode": 4,
            "inputs": [
                {
                    "localized_name": "图片",
                    "name": "images",
                    "type": "IMAGE",
                    "link": None
                },
                {
                    "localized_name": "文件名前缀",
                    "name": "filename_prefix",
                    "type": "STRING",
                    "widget": {
                        "name": "filename_prefix"
                    },
                    "link": None
                },
                {
                    "localized_name": "帧率",
                    "name": "fps",
                    "type": "FLOAT",
                    "widget": {
                        "name": "fps"
                    },
                    "link": None
                },
                {
                    "localized_name": "无损",
                    "name": "lossless",
                    "type": "BOOLEAN",
                    "widget": {
                        "name": "lossless"
                    },
                    "link": None
                },
                {
                    "localized_name": "质量",
                    "name": "quality",
                    "type": "INT",
                    "widget": {
                        "name": "quality"
                    },
                    "link": None
                },
                {
                    "localized_name": "方法",
                    "name": "method",
                    "type": "COMBO",
                    "widget": {
                        "name": "method"
                    },
                    "link": None
                }
            ],
            "outputs": [],
            "properties": {
                "cnr_id": "comfy-core",
                "ver": "0.3.27"
            },
            "widgets_values": [
                "ComfyUI",
                24,
                False,
                80,
                "2"
            ]
        }
    ]
}

# Wan2.1 工作流节点配置
Wan21_NODES = {
    "model_loader": "38",          # Wan2.1 模型加载节点
    "vae_loader": "39",            # VAE 加载节点
    "positive_prompt": "6",        # 正向提示词
    "negative_prompt": "7",        # 负向提示词
    "sampler": "8",                # 采样器
    "latent_image": "3",           # 空白潜在图像
    "video_saver": "28",           # 视频保存节点
    "model_sampling": "48",        # 模型采样配置
}

# Wan2.1 默认参数
Wan21_DEFAULT_PARAMS = {
    "model_name": "wan_2.1.safetensors",  # Wan2.1 模型文件名
    "vae_name": "wan_2.1_vae.safetensors",  # Wan2.1 VAE 文件名
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7.0,
    "sampler_name": "euler",
    "scheduler": "simple",
    "denoise": 1.0,
    "negative_prompt": "low quality, blurry, distorted, watermark, text, bad anatomy",
    "fps": 24,
    "video_length": 8,  # 视频长度（秒）
    "lossless": False,
    "quality": 80,
}


def get_wan21_workflow(
    positive_prompt: str,
    video_id: int,
    **kwargs
) -> dict:
    """
    获取配置好的 Wan2.1 视频生成工作流
    
    Args:
        positive_prompt: 正向提示词
        video_id: 视频 ID
        **kwargs: 其他参数
        
    Returns:
        配置好的工作流字典
    """
    import copy
    
    # 深拷贝工作流
    workflow = copy.deepcopy(Wan21_WORKFLOW_TEMPLATE)
    
    if not workflow:
        raise ValueError(
            "Wan2.1 工作流未配置！\n"
            "请在 ComfyUI 中导出 Wan2.1 工作流，并粘贴到 Wan21_WORKFLOW_TEMPLATE 中。"
        )
    
    # 获取参数
    width = kwargs.get("width", Wan21_DEFAULT_PARAMS["width"])
    height = kwargs.get("height", Wan21_DEFAULT_PARAMS["height"])
    steps = kwargs.get("steps", Wan21_DEFAULT_PARAMS["steps"])
    cfg_scale = kwargs.get("cfg_scale", Wan21_DEFAULT_PARAMS["cfg_scale"])
    negative_prompt = kwargs.get("negative_prompt", Wan21_DEFAULT_PARAMS["negative_prompt"])
    seed = kwargs.get("seed", -1)
    fps = kwargs.get("fps", Wan21_DEFAULT_PARAMS["fps"])
    
    # 修改正向提示词
    positive_node = Wan21_NODES.get("positive_prompt")
    if positive_node and positive_node in workflow:
        workflow[positive_node]["inputs"]["text"] = positive_prompt
    
    # 修改负向提示词
    negative_node = Wan21_NODES.get("negative_prompt")
    if negative_node and negative_node in workflow:
        workflow[negative_node]["inputs"]["text"] = negative_prompt
    
    # 修改采样器参数
    sampler_node = Wan21_NODES.get("sampler")
    if sampler_node and sampler_node in workflow:
        workflow[sampler_node]["inputs"]["seed"] = seed
        workflow[sampler_node]["inputs"]["steps"] = steps
        workflow[sampler_node]["inputs"]["cfg"] = cfg_scale
        workflow[sampler_node]["inputs"]["sampler_name"] = kwargs.get(
            "sampler_name", Wan21_DEFAULT_PARAMS["sampler_name"]
        )
        workflow[sampler_node]["inputs"]["scheduler"] = kwargs.get(
            "scheduler", Wan21_DEFAULT_PARAMS["scheduler"]
        )
    
    # 修改图像尺寸
    size_node = Wan21_NODES.get("latent_image")
    if size_node and size_node in workflow:
        workflow[size_node]["inputs"]["width"] = width
        workflow[size_node]["inputs"]["height"] = height
    
    # 修改视频保存参数
    save_node = Wan21_NODES.get("video_saver")
    if save_node and save_node in workflow:
        workflow[save_node]["inputs"]["filename_prefix"] = f"wan21_video_{video_id}"
        workflow[save_node]["inputs"]["fps"] = fps
    
    return workflow
