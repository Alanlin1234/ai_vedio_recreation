from typing import Dict, Any, Optional
import os

from ..utils.video_utils import VideoUtils
from ..utils.keyframe_manager import KeyframeManager

class PerceptionModule:
    def __init__(self, config: Dict[str, Any]):
# 初始化感知模块
        self.config = config
        self.video_utils = VideoUtils()
        # 初始化关键帧管理器
        self.keyframe_manager = KeyframeManager(config)
    
    def get_scene_info(self, scene: Dict[str, Any]) -> Dict[str, Any]:
# 获取场景信息
        scene_info = scene.copy()
        
        # 提取视频信息
        video_path = scene.get('video_path')
        if video_path and os.path.exists(video_path):
            video_info = self.video_utils.get_video_info(video_path)
            scene_info.update(video_info)
        
        # 提取关键帧 - 优先使用已有的关键帧，否则重新提取
        num_keyframes = self.config.get('num_keyframes', 2)
        if 'keyframes' in scene and scene['keyframes']:
            # 使用已有的关键帧
            keyframes = scene['keyframes']
            scene_info['keyframes'] = keyframes
            scene_info['first_frame'] = keyframes[0] if keyframes else None
            scene_info['last_frame'] = keyframes[-1] if keyframes else None
        elif video_path and os.path.exists(video_path):
            # 重新提取关键帧
            keyframes = self.video_utils.extract_keyframes(video_path, num_keyframes=num_keyframes)
            scene_info['keyframes'] = keyframes
            scene_info['first_frame'] = keyframes[0] if keyframes else None
            scene_info['last_frame'] = keyframes[-1] if keyframes else None
        
        return scene_info
    
    def extract_keyframes(self, scene: Dict[str, Any]) -> Dict[str, Any]:
# 提取场景关键帧
        # 优先使用已有的关键帧
        if 'keyframes' in scene and scene['keyframes']:
            scene['first_frame'] = scene['keyframes'][0] if scene['keyframes'] else None
            scene['last_frame'] = scene['keyframes'][-1] if scene['keyframes'] else None
            return scene
        
        # 否则重新提取关键帧
        video_path = scene.get('video_path')
        if not video_path or not os.path.exists(video_path):
            return scene
        
        num_keyframes = self.config.get('num_keyframes', 2)
        keyframes = self.video_utils.extract_keyframes(video_path, num_keyframes=num_keyframes)
        
        scene['keyframes'] = keyframes
        scene['first_frame'] = keyframes[0] if keyframes else None
        scene['last_frame'] = keyframes[-1] if keyframes else None
        
        return scene
    
    def parse_prompt_info(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析prompt中的关键信息"""
        main_elements = []
        style_info = {}
        
        original_prompt = prompt_data.get('original_prompt', '') or prompt_data.get('description', '')
        generation_params = prompt_data.get('generation_params', {})
        
        if original_prompt:
            if '人物' in original_prompt or '角色' in original_prompt or 'person' in original_prompt.lower():
                main_elements.append('人物')
            if '场景' in original_prompt or '背景' in original_prompt or 'scene' in original_prompt.lower():
                main_elements.append('场景')
            if '风格' in original_prompt or '画风' in original_prompt or 'style' in original_prompt.lower():
                style_info['type'] = 'art'
            if '动作' in original_prompt or 'action' in original_prompt.lower():
                main_elements.append('动作')
            if '表情' in original_prompt or 'emotion' in original_prompt.lower():
                main_elements.append('表情')
        
        return {
            'main_elements': main_elements,
            'style_info': style_info,
            'raw_prompt': prompt_data,
            'original_prompt': original_prompt,
            'generation_params': generation_params
        }
    
    def get_prev_scene_info(self, previous_scene: Dict[str, Any]) -> Dict[str, Any]:
# 获取上一场景的关键信息，用于一致性检查
        if not previous_scene:
            return None
        
        prev_scene_info = {
            'video_path': previous_scene.get('video_path'),
            'video_info': previous_scene.get('video_info', {}),
            'scene_index': previous_scene.get('scene_index'),
            'scene_id': previous_scene.get('scene_id'),
        }
        
        # 优先使用已有的关键帧，否则提取
        if 'keyframes' in previous_scene and previous_scene['keyframes']:
            prev_scene_info['keyframes'] = previous_scene['keyframes']
            prev_scene_info['first_frame'] = previous_scene['keyframes'][0] if previous_scene['keyframes'] else None
            prev_scene_info['last_frame'] = previous_scene['keyframes'][-1] if previous_scene['keyframes'] else None
        elif previous_scene.get('video_path'):
            # 只在需要时提取关键帧
            num_keyframes = self.config.get('num_keyframes', 2)
            keyframes = self.video_utils.extract_keyframes(previous_scene['video_path'], num_keyframes=num_keyframes)
            prev_scene_info['keyframes'] = keyframes
            prev_scene_info['first_frame'] = keyframes[0] if keyframes else None
            prev_scene_info['last_frame'] = keyframes[-1] if keyframes else None
        
        return prev_scene_info
    
    def extract_multi_source_keyframes(self, scene: Dict[str, Any], previous_scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
# 从多个来源提取关键帧，增强场景理解
        # 使用关键帧管理器来提取和管理多源关键帧
        return self.keyframe_manager.extract_and_cache_multi_source_keyframes(scene, previous_scene)

