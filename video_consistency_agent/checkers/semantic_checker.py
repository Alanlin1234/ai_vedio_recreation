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
# 检查语义一致性
        if not previous_scene:
            # 第一个场景，无需检查一致性
            return {
                'success': True,
                'score': 1.0,
                'issues': [],
                'passed': True
            }
        
        try:
            # 分析内容连贯性
            coherence_result = await self.llm_client.analyze_content_coherence(
                previous_scene.get('description', ''),
                current_scene.get('description', '')
            )
            
            overall_score = coherence_result.get('overall_score', 0.0) / 100  # 转换为0-1范围
            
            # 收集问题
            issues = coherence_result.get('suggestions', [])
            
            passed = overall_score >= self.threshold
            
            return {
                'success': True,
                'score': overall_score,
                'issues': issues,
                'passed': passed
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'score': 0.0,
                'issues': [f"语义一致性检查失败: {str(e)}"],
                'passed': False
            }

