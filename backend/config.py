import os

class Config:
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 限制100MB
    VIDEO_TO_TEXT_API = "http://127.0.0.1:9977/api"
    DIFY_API_KEY = 'app-YDlvFczyggam1JKATZTjAKww'
    DIFY_WORKFLOW_URL = 'http://localhost/v1/workflows/run'
    
    # 添加DashScope API密钥配置
    DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', 'sk-d433c2f93eff433583a88e3bdb37289f')
    
    # SQLAlchemy配置 - 使用SQLite数据库
    SQLALCHEMY_DATABASE_URI = 'sqlite:///video_agent.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'echo': False  # 设为True可以看到SQL语句
    }
    
    
    # SiliconFlow API配置
    SILICONFLOW_API_KEY = os.getenv('SILICONFLOW_API_KEY', 'sk-jqfbsqxrbkgenlxcqecaewfyruosfadxrdfjgdzppbnitflj')  # 已填充新API密钥
    SILICONFLOW_BASE_URL = 'https://api.siliconflow.cn/v1'
    
    
    # Additional API Keys
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # ComfyUI配置
    COMFYUI_URL = os.getenv('COMFYUI_URL', 'http://127.0.0.1:8188')
    COMFYUI_OUTPUT_DIR = 'output/comfyui'
    
    # Agent系统配置
    AGENT_OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output/videos')
    AGENT_REFERENCE_LIBRARY = 'references'
    AGENT_CONSISTENCY_THRESHOLD = float(os.getenv('CONSISTENCY_THRESHOLD', '0.85'))  # 场景一致性阈值
    AGENT_MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))  # 最大重试次数
    AGENT_TIMEOUT = int(os.getenv('TIMEOUT', '300'))
    
    # 抖音 API 配置
    DOUYIN_API_KEY = os.getenv('DOUYIN_API_KEY', '')
    DOUYIN_API_SECRET = os.getenv('DOUYIN_API_SECRET', '')
    DOUYIN_API_ENDPOINT = os.getenv('DOUYIN_API_ENDPOINT', '')
    
    # 大模型 API 配置
    LLM_API_KEY = os.getenv('LLM_API_KEY', 'sk-198a7f0f22c749adae5aef316b517e28')
    LLM_API_ENDPOINT = os.getenv('LLM_API_ENDPOINT', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
    LLM_MODEL = os.getenv('LLM_MODEL', 'qwen-omni-turbo-latest')
    
    # 图像搜索 API 配置
    IMAGE_SEARCH_API_KEY = os.getenv('IMAGE_SEARCH_API_KEY', 'sk-198a7f0f22c749adae5aef316b517e28')
    IMAGE_SEARCH_API_ENDPOINT = os.getenv('IMAGE_SEARCH_API_ENDPOINT', '')
    
    # 本地参考图库路径
    LOCAL_LIBRARY_PATH = os.getenv('LOCAL_LIBRARY_PATH', 'data/reference_images')
    
    # 图像分析 API 配置
    VISION_API_KEY = os.getenv('VISION_API_KEY', 'sk-198a7f0f22c749adae5aef316b517e28')
    VISION_API_ENDPOINT = os.getenv('VISION_API_ENDPOINT', '')
    
    # 人脸识别 API 配置
    FACE_API_KEY = os.getenv('FACE_API_KEY', 'sk-198a7f0f22c749adae5aef316b517e28')
    FACE_API_ENDPOINT = os.getenv('FACE_API_ENDPOINT', '')
    
    # 图像质量评估 API 配置
    QUALITY_API_KEY = os.getenv('QUALITY_API_KEY', 'sk-198a7f0f22c749adae5aef316b517e28')
    QUALITY_API_ENDPOINT = os.getenv('QUALITY_API_ENDPOINT', '')
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/agent_system.log')
    
    @classmethod
    def get_agent_config(cls) -> dict:
        """获取Agent系统配置"""
        return {
            'comfyui_url': cls.COMFYUI_URL,
            'output_dir': cls.AGENT_OUTPUT_DIR,
            'consistency_threshold': cls.AGENT_CONSISTENCY_THRESHOLD,
            'max_retries': cls.AGENT_MAX_RETRIES,
            'timeout': cls.AGENT_TIMEOUT,
            'douyin_api_key': cls.DOUYIN_API_KEY,
            'douyin_api_secret': cls.DOUYIN_API_SECRET,
            'douyin_api_endpoint': cls.DOUYIN_API_ENDPOINT,
            'llm_api_key': cls.LLM_API_KEY,
            'llm_api_endpoint': cls.LLM_API_ENDPOINT,
            'llm_model': cls.LLM_MODEL,
            'image_search_api_key': cls.IMAGE_SEARCH_API_KEY,
            'image_search_api_endpoint': cls.IMAGE_SEARCH_API_ENDPOINT,
            'local_library_path': cls.LOCAL_LIBRARY_PATH,
            'vision_api_key': cls.VISION_API_KEY,
            'vision_api_endpoint': cls.VISION_API_ENDPOINT,
            'face_api_key': cls.FACE_API_KEY,
            'face_api_endpoint': cls.FACE_API_ENDPOINT,
            'quality_api_key': cls.QUALITY_API_KEY,
            'quality_api_endpoint': cls.QUALITY_API_ENDPOINT,
        }

# ComfyUI 配置字典（用于 Agent）
COMFYUI_CONFIG = {
    'comfyui_url': Config.COMFYUI_URL,
    'output_dir': Config.COMFYUI_OUTPUT_DIR,
}

# 一致性检查配置
CONSISTENCY_CONFIG = {
    'threshold': Config.AGENT_CONSISTENCY_THRESHOLD,
    'max_retries': Config.AGENT_MAX_RETRIES,
    'vision_api_key': Config.VISION_API_KEY,
    'vision_api_endpoint': Config.VISION_API_ENDPOINT,
    'face_api_key': Config.FACE_API_KEY,
    'face_api_endpoint': Config.FACE_API_ENDPOINT,
    'quality_api_key': Config.QUALITY_API_KEY,
    'quality_api_endpoint': Config.QUALITY_API_ENDPOINT,
}

# Flux 工作流默认配置
FLUX_DEFAULT_CONFIG = {
    'type': 'flux',
    'width': 1280,
    'height': 720,
    'steps': 20,
    'cfg_scale': 4.0,
    'sampler_name': 'euler',  
    'scheduler': 'simple',
    'style_prefix': 'cinematic, high quality, detailed, professional lighting',
    'negative_prompt': 'low quality, blurry, distorted, inconsistent style, watermark, text',
    'use_controlnet': False,
    'style_lora': None,
    'style_lora_strength': 0.8,
}

# Wan2.1 工作流默认配置
Wan21_DEFAULT_CONFIG = {
    'type': 'wan21',
    'width': 1280,
    'height': 720,
    'steps': 20,
    'cfg_scale': 5.0,
    'sampler_name': 'euler',
    'scheduler': 'simple',
    'negative_prompt': 'low quality, blurry, distorted, watermark, text, bad anatomy',
    'fps': 30,
    'video_length': 8,
    'lossless': False,
    'quality': 80,
}

config = Config()
__all__ = ['config', 'COMFYUI_CONFIG', 'CONSISTENCY_CONFIG', 'FLUX_DEFAULT_CONFIG', 'Wan21_DEFAULT_CONFIG']
