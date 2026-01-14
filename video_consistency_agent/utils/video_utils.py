import os
import subprocess
import tempfile
from typing import List, Dict, Any
import cv2
import numpy as np

class VideoUtils:
    def __init__(self):
        """初始化视频处理工具"""
        pass
    
    def extract_keyframes(self, video_path: str, num_keyframes: int = 2) -> List[str]:
# 提取视频关键帧
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 获取视频信息
        video_info = self.get_video_info(video_path)
        duration = video_info['duration']
        
        keyframe_paths = []
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 计算关键帧提取时间点
            if num_keyframes == 1:
                # 只提取中间帧
                timestamps = [duration / 2]
            elif num_keyframes == 2:
                # 提取开始和结束帧
                timestamps = [1, duration]
            else:
                # 均匀分布提取
                timestamps = [i * duration / (num_keyframes + 1) for i in range(1, num_keyframes + 1)]
            
            for i, timestamp in enumerate(timestamps):
                # 生成关键帧路径
                keyframe_path = os.path.join(temp_dir, f"keyframe_{i+1}.jpg")
                
                # 使用FFmpeg提取关键帧
                self._extract_frame_at_timestamp(video_path, timestamp, keyframe_path)
                
                if os.path.exists(keyframe_path) and os.path.getsize(keyframe_path) > 0:
                    keyframe_paths.append(keyframe_path)
                else:
                    raise RuntimeError(f"关键帧提取失败: {keyframe_path}")
            
            return keyframe_paths
        except Exception as e:
            # 清理临时文件
            self._cleanup_temp_files(temp_dir)
            raise e
    
    def get_video_info(self, video_path: str) -> Dict[str, Any]:
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
            'duration': duration,
            'path': video_path
        }
    
    def get_last_frame(self, video_path: str) -> str:
# 获取视频最后一帧
        video_info = self.get_video_info(video_path)
        duration = video_info['duration']
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        last_frame_path = os.path.join(temp_dir, "last_frame.jpg")
        
        try:
            # 提取真正的最后一帧（使用视频总时长作为时间戳）
            # 对于极短视频，确保时间戳不为负数
            timestamp = max(0, duration)
            self._extract_frame_at_timestamp(video_path, timestamp, last_frame_path)
            
            if os.path.exists(last_frame_path) and os.path.getsize(last_frame_path) > 0:
                return last_frame_path
            else:
                # 如果提取失败，尝试使用视频结束前0.1秒作为备选
                fallback_timestamp = max(0, duration - 0.1)
                self._extract_frame_at_timestamp(video_path, fallback_timestamp, last_frame_path)
                
                if os.path.exists(last_frame_path) and os.path.getsize(last_frame_path) > 0:
                    return last_frame_path
                else:
                    raise RuntimeError(f"最后一帧提取失败: {last_frame_path}")
        except Exception as e:
            # 清理临时文件
            self._cleanup_temp_files(temp_dir)
            raise e
    
    def _extract_frame_at_timestamp(self, video_path: str, timestamp: float, output_path: str) -> None:
# 在指定时间戳提取视频帧
        # 构建FFmpeg命令
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(timestamp),
            '-vframes', '1',
            '-q:v', '2',  # 高质量
            '-y',  # 覆盖现有文件
            output_path
        ]
        
        # 执行FFmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg命令执行失败: {result.stderr}")
    
    def _cleanup_temp_files(self, temp_dir: str) -> None:
# 清理临时文件
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    def extract_audio(self, video_path: str) -> str:
# 提取视频中的音频
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        try:
            # 构建FFmpeg命令
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # 只提取音频
                '-ac', '2',  # 双声道
                '-ar', '44100',  # 采样率
                '-ab', '192k',  # 比特率
                '-y',  # 覆盖现有文件
                audio_path
            ]
            
            # 执行FFmpeg命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg命令执行失败: {result.stderr}")
            
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                return audio_path
            else:
                raise RuntimeError(f"音频提取失败: {audio_path}")
        except Exception as e:
            # 清理临时文件
            self._cleanup_temp_files(temp_dir)
            raise e
    
    def get_first_frame(self, video_path: str) -> str:
# 获取视频第一帧
        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        first_frame_path = os.path.join(temp_dir, "first_frame.jpg")
        
        try:
            # 提取第一帧（从1秒处提取，避免黑屏）
            self._extract_frame_at_timestamp(video_path, 1, first_frame_path)
            
            if os.path.exists(first_frame_path) and os.path.getsize(first_frame_path) > 0:
                return first_frame_path
            else:
                raise RuntimeError(f"第一帧提取失败: {first_frame_path}")
        except Exception as e:
            # 清理临时文件
            self._cleanup_temp_files(temp_dir)
            raise e

