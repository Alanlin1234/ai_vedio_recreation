# 路由蓝图初始化文件
from .video_routes import video_bp
from .author_routes import author_bp
from .douyin_routes import douyin_bp
from .video_recreation_routes import video_recreation_bp

__all__ = ['video_bp', 'author_bp', 'douyin_bp', 'video_recreation_bp']
