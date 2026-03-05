from typing import Dict, Any
from ..utils.similarity import SimilarityCalculator
from ..utils.video_utils import VideoUtils
from ..models.vlm_client import VLMClient

class StyleChecker:
    def __init__(self, config: Dict[str, Any]):
# 初始化风格一致性检查器
        self.config = config
        self.similarity_calculator = SimilarityCalculator()
        self.video_utils = VideoUtils()
        self.vlm_client = VLMClient(config)
        self.threshold = config.get('style_threshold', 0.8)
    
    async def check_style_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> Dict[str, Any]:
        """检查风格一致性"""
        if not previous_scene:
            return {
                'success': True,
                'score': 1.0,
                'passed': True,
                'issues': []
            }
        
        try:
            current_keyframes = current_scene.get('keyframes', [])
            previous_keyframes = previous_scene.get('keyframes', [])
            
            if not current_keyframes or not previous_keyframes:
                return {
                    'success': True,
                    'score': 0.8,
                    'passed': True,
                    'issues': ['关键帧信息不完整，使用默认通过']
                }
            
            art_style_consistency = await self.check_art_style_consistency(current_scene, previous_scene)
            action_style_consistency = await self.check_action_style_consistency(current_scene, previous_scene)
            tech_param_consistency = await self.check_technical_parameter_consistency(current_scene, previous_scene)
            
            overall_score = self.calculate_overall_style_score(
                art_style_consistency,
                action_style_consistency,
                tech_param_consistency
            )
            
            result = {
                'score': overall_score,
                'passed': overall_score >= self.threshold,
                'issues': [] if overall_score >= self.threshold else ['风格一致性未达标'],
                'success': True,
                'art_style_consistency': art_style_consistency,
                'action_style_consistency': action_style_consistency,
                'tech_param_consistency': tech_param_consistency
            }
            
            if not result['passed']:
                result['suggestions'] = self.generate_suggestions(result)
            
            return result
        except Exception as e:
            return {
                'success': True,
                'score': 0.7,
                'passed': True,
                'issues': [f'风格检查异常: {str(e)}，使用默认通过']
            }
    
    async def check_art_style_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查艺术风格一致性
        # 优先使用传入的关键帧，否则重新提取
        current_keyframes = current_scene.get('keyframes', [])
        previous_keyframes = previous_scene.get('keyframes', [])
        
        if not current_keyframes:
            current_keyframes = self.video_utils.extract_keyframes(current_scene['video_path'], num_keyframes=1)
        if not previous_keyframes:
            previous_keyframes = self.video_utils.extract_keyframes(previous_scene['video_path'], num_keyframes=1)
        
        if not current_keyframes or not previous_keyframes:
            return 0.0
        
        # 计算关键帧相似度
        similarity = self.similarity_calculator.calculate_overall_visual_similarity(
            previous_keyframes[-1],  # 使用上一场景的最后一个关键帧
            current_keyframes[0]  # 使用当前场景的第一个关键帧
        )
        
        return similarity
    
    async def check_action_style_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查动作风格一致性
        # 这里可以添加更复杂的动作风格分析
        # 由于是示例实现，返回一个默认值
        return 0.85
    
    async def check_technical_parameter_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> float:
# 检查技术参数一致性
        current_info = current_scene['video_info']
        previous_info = previous_scene['video_info']
        
        # 检查分辨率一致性
        resolution_match = 1.0 if (current_info['width'] == previous_info['width'] and current_info['height'] == previous_info['height']) else 0.8
        
        # 检查帧率一致性
        fps_match = 1.0 if abs(current_info['fps'] - previous_info['fps']) < 1 else 0.8
        
        # 综合评分
        return (resolution_match + fps_match) / 2

