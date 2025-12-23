# 视频创意重构系统配置文件

from typing import Dict, Any
import os
from datetime import datetime


class VideoReconstructionConfig:
    """视频创意重构系统配置类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "system": {
                "name": "视频创意重构系统",
                "version": "1.0.0",
                "description": "基于AI的视频创意重构系统，支持视频获取、内容分析、故事重构、图像/视频生成和最终合成",
                "log_level": "INFO",
                "output_dir": os.path.join(os.getcwd(), "output"),
                "temp_dir": os.path.join(os.getcwd(), "temp"),
                "max_workers": 4
            },
            "douyin": {
                "crawler_base_url": "http://localhost:88",
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 5,
                "download_dir": os.path.join(os.getcwd(), "videos", "douyin")
            },
            "ffmpeg": {
                "ffmpeg_path": "",  # 自动查找
                "timeout": 600,
                "default_slice_duration": 8,  # 默认切片时长8秒
                "video_quality": "high",
                "audio_quality": "high"
            },
            "comfyui": {
                "base_url": "http://localhost:8188",
                "timeout": 600,
                "max_retries": 3,
                "retry_delay": 5,
                "models": {
                    "txt2img": "SDXL",
                    "img2img": "SDXL",
                    "img2video": "AnimateDiff"
                },
                "default_params": {
                    "txt2img": {
                        "steps": 25,
                        "cfg_scale": 7.0,
                        "width": 1024,
                        "height": 1024,
                        "sampler_name": "euler_a",
                        "scheduler": "normal"
                    },
                    "img2img": {
                        "steps": 20,
                        "cfg_scale": 7.0,
                        "denoising_strength": 0.75,
                        "sampler_name": "euler_a",
                        "scheduler": "normal"
                    },
                    "img2video": {
                        "steps": 25,
                        "cfg_scale": 7.0,
                        "width": 512,
                        "height": 512,
                        "length": 16,
                        "fps": 8,
                        "sampler_name": "euler_a",
                        "scheduler": "normal"
                    }
                }
            },
            "qwen_vl": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
                "timeout": 120,
                "model": "qwen-omni-turbo",
                "api_key": "sk-ecf2ffd7751b4b959ae454112753b35b",
                "default_params": {
                    "temperature": 0.8,
                    "top_p": 0.9,
                    "max_new_tokens": 4096,
                    "system_prompt": "你是一个专业的故事内容分析师，能够从完整的图片序列中解析故事的分镜结构和脚本内容。请系统性分析视觉元素、场景转换及叙事逻辑，生成符合故事原意的分镜描述和脚本文本。请以结构化的JSON格式输出结果，包含分镜结构和脚本内容。"
                }
            },
            "qwen_72b": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode",
                "timeout": 120,
                "model": "qwen-plus",
                "api_key": "sk-09888bd521f143baa39870a1a648d830",
                "default_params": {
                    "temperature": 0.9,
                    "top_p": 0.95,
                    "max_new_tokens": 4096,
                    "system_prompt": "你是一个专业的故事创作大师，能够根据视频内容分析结果，生成吸引人的故事线，包括详细的场景描述、角色设定、情节发展等。请确保故事逻辑连贯、情感丰富、富有创意。"
                }
            },
            "hotspot": {
                "enabled": True,
                "keywords": ["AI", "科技", "创意", "生活"],
                "count": 10,
                "category": "热点",
                "download_videos": True
            }
        }
        
        # 合并配置
        self.config = default_config
        if config:
            self._merge_configs(self.config, config)
        
        # 初始化输出目录
        self._init_directories()
        
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """递归合并配置字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
        return base
    
    def _init_directories(self):
        """初始化系统目录"""
        # 创建输出目录
        output_dir = self.config["system"]["output_dir"]
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 创建临时目录
        temp_dir = self.config["system"]["temp_dir"]
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
        
        # 创建抖音视频下载目录
        douyin_dir = self.config["douyin"]["download_dir"]
        if not os.path.exists(douyin_dir):
            os.makedirs(douyin_dir, exist_ok=True)
        
        # 创建生成图像目录
        generated_images_dir = os.path.join(output_dir, "generated_images")
        if not os.path.exists(generated_images_dir):
            os.makedirs(generated_images_dir, exist_ok=True)
        
        # 创建生成视频目录
        generated_videos_dir = os.path.join(output_dir, "generated_videos")
        if not os.path.exists(generated_videos_dir):
            os.makedirs(generated_videos_dir, exist_ok=True)
    
    def get(self, key_path: str, default: Any = None) -> Any:
# 根据键路径获取配置值
        keys = key_path.split(".")
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
# 根据键路径设置配置值
        keys = key_path.split(".")
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, file_path: str):
        """保存配置到文件"""
        import json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> "VideoReconstructionConfig":
        """从文件加载配置"""
        import json
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return cls(config)
        return cls()
    
    def get_douyin_config(self) -> Dict[str, Any]:
        """获取抖音配置"""
        return self.config["douyin"]
    
    def get_ffmpeg_config(self) -> Dict[str, Any]:
        """获取FFmpeg配置"""
        return self.config["ffmpeg"]
    
    def get_comfyui_config(self) -> Dict[str, Any]:
        """获取ComfyUI配置"""
        return self.config["comfyui"]
    
    def get_qwen_vl_config(self) -> Dict[str, Any]:
        """获取Qwen-VL配置"""
        return self.config["qwen_vl"]
    
    def get_qwen_72b_config(self) -> Dict[str, Any]:
        """获取Qwen-72B配置"""
        return self.config["qwen_72b"]
    
    def get_hotspot_config(self) -> Dict[str, Any]:
        """获取热点配置"""
        return self.config["hotspot"]
    
    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config["system"]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.config.copy()
    
    def __str__(self) -> str:
        """字符串表示"""
        import json
        return json.dumps(self.config, ensure_ascii=False, indent=2)


# 创建全局配置实例
config = VideoReconstructionConfig()

# 导出配置实例
def get_config() -> VideoReconstructionConfig:
    """获取全局配置实例"""
    return config

# 加载配置文件
def load_config(file_path: str) -> VideoReconstructionConfig:
    """从文件加载配置"""
    global config
    config = VideoReconstructionConfig.load(file_path)
    return config

# 保存配置文件
def save_config(file_path: str):
    """保存配置到文件"""
    global config
    config.save(file_path)
