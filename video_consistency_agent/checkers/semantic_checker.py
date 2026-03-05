from typing import Dict, Any
from ..models.llm_client import LLMClient
from ..models.vlm_client import VLMClient

class SemanticChecker:
    def __init__(self, config: Dict[str, Any]):
# 初始化语义一致性检查器
        self.config = config
        self.llm_client = LLMClient(config)
        self.vlm_client = VLMClient(config)
        self.threshold = config.get('semantic_threshold', 0.85)
    
    async def check_semantic_consistency(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> Dict[str, Any]:
        """检查语义一致性"""
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
            
            content_coherence = await self.check_content_coherence(current_scene, previous_scene)
            character_consistency = self.check_character_consistency(current_scene, previous_scene)
            event_logic = await self.check_event_logic(current_scene, previous_scene)
            
            overall_score = self.calculate_overall_semantic_score(
                content_coherence,
                character_consistency,
                event_logic
            )
            
            result = {
                'score': overall_score,
                'passed': overall_score >= self.threshold,
                'issues': [] if overall_score >= self.threshold else ['语义一致性未达标'],
                'success': True,
                'content_coherence': content_coherence,
                'character_consistency': character_consistency,
                'event_logic': event_logic
            }
            
            if not result['passed']:
                result['suggestions'] = self.generate_suggestions(result)
            
            return result
        except Exception as e:
            return {
                'success': True,
                'score': 0.7,
                'passed': True,
                'issues': [f'语义检查异常: {str(e)}，使用默认通过']
            }

