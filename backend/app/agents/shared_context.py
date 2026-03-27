"""
共享上下文模块
存储所有Agent的输入输出数据
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ReviewStatus(Enum):
    """审核状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class ErrorInfo:
    """错误信息"""
    def __init__(self, agent_name: str, error: str, timestamp: float):
        self.agent_name = agent_name
        self.error = error
        self.timestamp = timestamp


@dataclass
class Scene:
    """场景数据类"""
    scene_number: int
    shot_type: str
    description: str
    plot: str
    dialogue: str
    prompt: str
    duration: int
    image: Optional[str] = None
    image_generation_success: bool = False


@dataclass
class SharedContext:
    """共享上下文数据类"""
    # 原始数据
    video_path: str = ""                          # 视频文件路径
    video_analysis: str = ""                       # 视频理解结果

    # 审核结果
    review_status: ReviewStatus = ReviewStatus.PENDING  # pending/passed/failed
    review_feedback: str = ""                      # 审核意见

    # 教育分析结果
    highlights: List[str] = None                    # 故事亮点
    educational_meaning: str = ""                 # 教育意义

    # 剧本结果
    original_script: str = ""                     # 原始剧本
    enhanced_script: str = ""                     # 增强后剧本

    # 分镜结果
    storyboard: List[Scene] = None                  # 分镜列表

    # 视频生成结果
    generated_videos: List[str] = None              # 生成的视频路径列表

    # 最终结果
    final_video: str = ""                          # 最终视频路径

    # 元数据
    current_agent: str = ""                        # 当前执行的Agent
    error_history: List[ErrorInfo] = None           # 错误历史
    retry_count: Dict[str, int] = None              # 各Agent重试次数
    
    def __post_init__(self):
        if self.highlights is None:
            self.highlights = []
        if self.storyboard is None:
            self.storyboard = []
        if self.generated_videos is None:
            self.generated_videos = []
        if self.error_history is None:
            self.error_history = []
        if self.retry_count is None:
            self.retry_count = {}
