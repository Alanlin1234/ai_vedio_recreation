from typing import Dict, Any
from ..checkers.visual_checker import VisualChecker
from ..checkers.temporal_checker import TemporalChecker
from ..checkers.semantic_checker import SemanticChecker
from ..checkers.style_checker import StyleChecker

class AnalysisModule:
    def __init__(self, config: Dict[str, Any]):
# 初始化分析模块
        self.config = config
        self.visual_checker = VisualChecker(config)
        self.temporal_checker = TemporalChecker(config)
        self.semantic_checker = SemanticChecker(config)
        self.style_checker = StyleChecker(config)
    
    async def evaluate_consistency(self, current_scene: Dict[str, Any], prev_scene: Dict[str, Any]) -> Dict[str, Any]:
# 评估场景一致性
        if not prev_scene:
            # 第一个场景，不需要检查一致性
            return {
                'passed': True,
                'visual_score': 1.0,
                'temporal_score': 1.0,
                'semantic_score': 1.0,
                'style_score': 1.0,
                'overall_score': 1.0,
                'issues': []
            }
        
        # 1. 视觉一致性检查
        visual_result = await self.visual_checker.check_visual_consistency(current_scene, prev_scene)
        
        # 2. 时序一致性检查
        temporal_result = await self.temporal_checker.check_temporal_consistency(current_scene, prev_scene)
        
        # 3. 语义一致性检查
        semantic_result = await self.semantic_checker.check_semantic_consistency(current_scene, prev_scene)
        
        # 4. 风格一致性检查
        style_result = await self.style_checker.check_style_consistency(current_scene, prev_scene)
        
        # 5. 整合结果
        overall_score = self._calculate_overall_score(
            visual_result['score'],
            temporal_result['score'],
            semantic_result['score'],
            style_result['score']
        )
        
        # 6. 收集所有问题
        all_issues = []
        for result in [visual_result, temporal_result, semantic_result, style_result]:
            if not result['passed']:
                all_issues.extend(result['issues'])
        
        # 7. 检查是否通过
        passed = overall_score >= self.config.get('consistency_threshold', 0.85)
        
        return {
            'passed': passed,
            'visual_score': visual_result['score'],
            'temporal_score': temporal_result['score'],
            'semantic_score': semantic_result['score'],
            'style_score': style_result['score'],
            'overall_score': overall_score,
            'issues': all_issues,
            'visual_result': visual_result,
            'temporal_result': temporal_result,
            'semantic_result': semantic_result,
            'style_result': style_result
        }
    
    def _calculate_overall_score(self, visual_score: float, temporal_score: float, semantic_score: float, style_score: float) -> float:
# 计算整体一致性分数
        # 权重配置
        weights = self.config.get('consistency_weights', {
            'visual': 0.3,
            'temporal': 0.2,
            'semantic': 0.3,
            'style': 0.2
        })
        
        # 计算加权平均分
        overall = (
            visual_score * weights['visual'] +
            temporal_score * weights['temporal'] +
            semantic_score * weights['semantic'] +
            style_score * weights['style']
        )
        
        return overall

