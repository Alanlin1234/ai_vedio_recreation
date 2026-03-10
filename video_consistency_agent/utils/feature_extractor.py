import cv2
import numpy as np
import os
from typing import Dict, Any

class FeatureExtractor:
    def __init__(self):
        """初始化特征提取器"""
        pass
    
    def extract_keyframe_features(self, keyframe_path: str) -> Dict[str, Any]:
# 提取关键帧特征
        if not os.path.exists(keyframe_path):
            raise FileNotFoundError(f"关键帧文件不存在: {keyframe_path}")
        
        # 读取图像
        image = cv2.imread(keyframe_path)
        if image is None:
            raise ValueError(f"无法读取图像: {keyframe_path}")
        
        # 调整图像大小以提高处理速度
        resized_image = cv2.resize(image, (256, 256))
        
        # 提取色彩直方图
        hist_b = self.extract_color_histogram(image, channel=0)
        hist_g = self.extract_color_histogram(image, channel=1)
        hist_r = self.extract_color_histogram(image, channel=2)
        
        # 提取边缘特征
        edges = self.extract_edge_features(resized_image)
        
        return {
            'color_histograms': {
                'blue': hist_b,
                'green': hist_g,
                'red': hist_r
            },
            'edges': edges,
            'shape': image.shape
        }
    
    def extract_color_histogram(self, image: np.ndarray, channel: int = 0, bins: int = 256) -> np.ndarray:
# 提取色彩直方图
        # 计算直方图
        hist = cv2.calcHist([image], [channel], None, [bins], [0, 256])
        # 归一化直方图
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def extract_edge_features(self, image: np.ndarray) -> np.ndarray:
# 提取边缘特征
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # 使用 Canny 边缘检测
        edges = cv2.Canny(gray, 100, 200)
        return edges
    
    def extract_video_info(self, video_path: str) -> Dict[str, Any]:
# 获取视频基本信息
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频: {video_path}")
        
        # 获取视频信息
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            'width': width,
            'height': height,
            'fps': fps,
            'frame_count': frame_count,
            'duration': duration
        }

