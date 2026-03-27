from typing import Dict, Any
import hashlib
import json

class ChangeDetector:
    """
    变化检测器，用于检测场景间的变化，实现增量检查
    """
    
    def __init__(self):
        """
        初始化变化检测器
        """
        pass
    
    def calculate_scene_hash(self, scene: Dict[str, Any]) -> str:
        """
        计算场景的哈希值，用于快速比较场景是否变化
        
        Args:
            scene: 场景信息
            
        Returns:
            场景的哈希值
        """
        if not scene:
            return ""
        
        # 提取场景的关键信息用于哈希计算
        key_info = {
            'scene_id': scene.get('scene_id', ''),
            'video_path': scene.get('video_path', ''),
            'keyframes': scene.get('keyframes', []),
            'video_info': scene.get('video_info', {}),
            'duration': scene.get('duration', 0)
        }
        
        # 转换为JSON字符串并计算哈希
        key_str = json.dumps(key_info, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def detect_changes(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any], 
                      cached_scene: Dict[str, Any] = None) -> Dict[str, bool]:
        """
        检测当前场景与缓存场景之间的变化
        
        Args:
            current_scene: 当前场景信息
            previous_scene: 上一个场景信息
            cached_scene: 缓存的场景信息
            
        Returns:
            变化检测结果，包含四个维度的变化状态
        """
        if not cached_scene:
            # 没有缓存场景，需要全量检查
            return {
                'visual_changed': True,
                'temporal_changed': True,
                'semantic_changed': True,
                'style_changed': True
            }
        
        # 计算哈希值比较
        current_hash = self.calculate_scene_hash(current_scene)
        cached_hash = self.calculate_scene_hash(cached_scene)
        
        if current_hash == cached_hash:
            # 场景没有变化，不需要检查
            return {
                'visual_changed': False,
                'temporal_changed': False,
                'semantic_changed': False,
                'style_changed': False
            }
        
        # 场景发生变化，检测具体哪些维度需要检查
        changes = {
            'visual_changed': self._detect_visual_changes(current_scene, cached_scene),
            'temporal_changed': self._detect_temporal_changes(current_scene, cached_scene),
            'semantic_changed': self._detect_semantic_changes(current_scene, cached_scene),
            'style_changed': self._detect_style_changes(current_scene, cached_scene)
        }
        
        return changes
    
    def _detect_visual_changes(self, current_scene: Dict[str, Any], cached_scene: Dict[str, Any]) -> bool:
        """
        检测视觉维度的变化
        """
        # 检查关键帧是否变化
        current_keyframes = current_scene.get('keyframes', [])
        cached_keyframes = cached_scene.get('keyframes', [])
        if len(current_keyframes) != len(cached_keyframes):
            return True
        
        # 检查视频分辨率是否变化
        current_video_info = current_scene.get('video_info', {})
        cached_video_info = cached_scene.get('video_info', {})
        if current_video_info.get('width') != cached_video_info.get('width') or \
           current_video_info.get('height') != cached_video_info.get('height'):
            return True
        
        return False
    
    def _detect_temporal_changes(self, current_scene: Dict[str, Any], cached_scene: Dict[str, Any]) -> bool:
        """
        检测时序维度的变化
        """
        # 检查视频帧率是否变化
        current_video_info = current_scene.get('video_info', {})
        cached_video_info = cached_scene.get('video_info', {})
        if current_video_info.get('fps') != cached_video_info.get('fps'):
            return True
        
        # 检查视频时长是否变化
        if current_scene.get('duration') != cached_scene.get('duration'):
            return True
        
        return False
    
    def _detect_semantic_changes(self, current_scene: Dict[str, Any], cached_scene: Dict[str, Any]) -> bool:
        """
        检测语义维度的变化
        """
        # 检查场景描述是否变化
        current_desc = current_scene.get('description', '')
        cached_desc = cached_scene.get('description', '')
        if current_desc != cached_desc:
            return True
        
        # 检查场景ID是否变化
        if current_scene.get('scene_id') != cached_scene.get('scene_id'):
            return True
        
        return False
    
    def _detect_style_changes(self, current_scene: Dict[str, Any], cached_scene: Dict[str, Any]) -> bool:
        """
        检测风格维度的变化
        """
        # 检查风格元素是否变化
        current_style = current_scene.get('style_elements', {})
        cached_style = cached_scene.get('style_elements', {})
        if current_style != cached_style:
            return True
        
        # 检查技术参数是否变化
        current_tech = current_scene.get('technical_params', {})
        cached_tech = cached_scene.get('technical_params', {})
        if current_tech != cached_tech:
            return True
        
        return False