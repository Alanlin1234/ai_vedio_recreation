from typing import Dict, List, Any, Optional
import os
import hashlib
from .video_utils import VideoUtils


class KeyframeManager:
    """统一的关键帧管理模块，负责关键帧的提取、缓存、复用和传递"""
    
    def __init__(self, config: Dict[str, Any]):
# 初始化关键帧管理模块
        self.config = config
        self.video_utils = VideoUtils()
        self.keyframe_cache = {}  # 关键帧缓存，键为视频路径+参数的哈希值
        self.default_num_keyframes = config.get('num_keyframes', 2)
        self.cache_expiry_time = config.get('cache_expiry_time', 3600)  # 缓存过期时间，单位秒
    
    def get_cache_key(self, video_path: str, num_keyframes: int = 2) -> str:
# 生成缓存键
        cache_data = f"{video_path}_{num_keyframes}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def get_keyframes(self, video_path: str, num_keyframes: Optional[int] = None) -> List[str]:
# 获取视频的关键帧，优先从缓存中获取
        if num_keyframes is None:
            num_keyframes = self.default_num_keyframes
        
        # 检查视频文件是否存在
        if not os.path.exists(video_path):
            return []
        
        # 生成缓存键
        cache_key = self.get_cache_key(video_path, num_keyframes)
        
        # 检查缓存中是否存在
        if cache_key in self.keyframe_cache:
            return self.keyframe_cache[cache_key]
        
        # 提取关键帧
        keyframes = self.video_utils.extract_keyframes(video_path, num_keyframes=num_keyframes)
        
        # 缓存关键帧
        self.keyframe_cache[cache_key] = keyframes
        
        return keyframes
    
    def cache_keyframes(self, video_path: str, keyframes: List[str], num_keyframes: Optional[int] = None) -> None:
# 缓存关键帧
        if num_keyframes is None:
            num_keyframes = len(keyframes)
        
        cache_key = self.get_cache_key(video_path, num_keyframes)
        self.keyframe_cache[cache_key] = keyframes
    
    def get_scene_keyframes(self, scene: Dict[str, Any], num_keyframes: Optional[int] = None) -> List[str]:
# 获取场景的关键帧，优先使用场景中已有的关键帧
        # 1. 优先使用场景中已有的关键帧
        if 'keyframes' in scene and scene['keyframes']:
            return scene['keyframes']
        
        # 2. 其次检查场景的场景关键帧
        if 'scene_keyframes' in scene and scene['scene_keyframes']:
            return scene['scene_keyframes']
        
        # 3. 最后从视频中提取
        video_path = scene.get('video_path')
        if video_path:
            return self.get_keyframes(video_path, num_keyframes)
        
        return []
    
    def get_previous_scene_keyframes(self, previous_scene: Dict[str, Any], num_keyframes: Optional[int] = None) -> List[str]:
# 获取上一个场景的关键帧
        if not previous_scene:
            return []
        
        return self.get_scene_keyframes(previous_scene, num_keyframes)
    
    def get_original_keyframes(self, scene: Dict[str, Any]) -> List[str]:
# 获取原视频切片的关键帧
        # 1. 优先使用场景中已有的原视频关键帧
        if 'original_keyframes' in scene and scene['original_keyframes']:
            return scene['original_keyframes']
        
        # 2. 检查场景的slice_data中是否有关键帧
        if 'slice_data' in scene and scene['slice_data']:
            slice_data = scene['slice_data']
            if 'keyframes' in slice_data and slice_data['keyframes']:
                return slice_data['keyframes']
        
        return []
    
    def extract_and_cache_multi_source_keyframes(self, scene: Dict[str, Any], previous_scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
# 从多个来源提取关键帧并缓存
        scene_info = scene.copy()
        
        # 1. 场景自身的关键帧
        scene_keyframes = self.get_scene_keyframes(scene)
        scene_info['scene_keyframes'] = scene_keyframes
        
        # 2. 原视频切片的关键帧
        original_keyframes = self.get_original_keyframes(scene)
        scene_info['original_keyframes'] = original_keyframes
        
        # 3. 上一个场景的关键帧
        if previous_scene:
            previous_keyframes = self.get_previous_scene_keyframes(previous_scene)
            scene_info['previous_keyframes'] = previous_keyframes
        
        # 4. 构建所有关键帧的列表
        all_keyframes = []
        all_keyframes.extend(scene_keyframes)
        all_keyframes.extend(original_keyframes)
        if previous_scene:
            all_keyframes.extend(previous_keyframes)
        
        scene_info['all_keyframes'] = all_keyframes
        
        # 5. 缓存关键帧
        video_path = scene.get('video_path')
        if video_path and scene_keyframes:
            self.cache_keyframes(video_path, scene_keyframes)
        
        return scene_info
    
    def clear_cache(self) -> None:
        """清除关键帧缓存"""
        self.keyframe_cache.clear()
    
    def clear_cache_for_video(self, video_path: str) -> None:
# 清除指定视频的关键帧缓存
        # 生成所有可能的缓存键并删除
        for num_keyframes in range(1, 10):  # 考虑1-9个关键帧的情况
            cache_key = self.get_cache_key(video_path, num_keyframes)
            if cache_key in self.keyframe_cache:
                del self.keyframe_cache[cache_key]
    
    def get_cache_stats(self) -> Dict[str, Any]:
# 获取缓存统计信息
        return {
            'cache_size': len(self.keyframe_cache),
            'default_num_keyframes': self.default_num_keyframes,
            'cache_expiry_time': self.cache_expiry_time
        }
    
    def validate_keyframes(self, keyframes: List[str]) -> List[str]:
# 验证关键帧是否存在，返回有效的关键帧列表
        valid_keyframes = []
        for keyframe in keyframes:
            if keyframe and os.path.exists(keyframe):
                valid_keyframes.append(keyframe)
        return valid_keyframes
    
    def select_representative_keyframes(self, keyframes: List[str], num_keyframes: int = 2) -> List[str]:
# 从关键帧列表中选择代表性的关键帧
        if not keyframes:
            return []
        
        # 如果关键帧数量不足，直接返回
        if len(keyframes) <= num_keyframes:
            return keyframes
        
        # 均匀选择关键帧
        step = len(keyframes) / num_keyframes
        selected_keyframes = []
        
        for i in range(num_keyframes):
            index = int(i * step)
            selected_keyframes.append(keyframes[index])
        
        return selected_keyframes

