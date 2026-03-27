"""
视频二创任务目录（pipeline combine 等使用 create_task_directory）
"""

import os
from typing import Any, Dict


class VideoRecreationService:
    """最小实现：仅提供与 pipeline 兼容的目录创建。"""

    def create_task_directory(self, recreation_id: int, base_video_path: str) -> str:
        video_dir = os.path.dirname(os.path.abspath(base_video_path))
        task_dir = os.path.join(video_dir, f'recreation_{recreation_id}')
        for sub in ('audio', 'scripts', 'tts', 'videos', 'final'):
            os.makedirs(os.path.join(task_dir, sub), exist_ok=True)
        return task_dir
