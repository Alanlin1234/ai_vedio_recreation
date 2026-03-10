from typing import Dict, Any
from ..checkers.visual_checker import VisualChecker
from ..checkers.temporal_checker import TemporalChecker
from ..checkers.semantic_checker import SemanticChecker
from ..checkers.style_checker import StyleChecker

class AnalysisModule:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.visual_checker = VisualChecker(config)
        self.temporal_checker = TemporalChecker(config)
        self.semantic_checker = SemanticChecker(config)
        self.style_checker = StyleChecker(config)
    
    async def evaluate_consistency(self, current_scene: Dict[str, Any], prev_scene: Dict[str, Any], 
                                 check_dims: Dict[str, bool] = None) -> Dict[str, Any]:
        if not prev_scene:
            return {
                'passed': True,
                'visual_score': 1.0,
                'temporal_score': 1.0,
                'semantic_score': 1.0,
                'style_score': 1.0,
                'overall_score': 1.0,
                'issues': []
            }
        
        if check_dims is None:
            check_dims = {
                'visual_changed': True,
                'temporal_changed': True,
                'semantic_changed': True,
                'style_changed': True
            }
        
        import asyncio
        
        default_result = {'score': 1.0, 'passed': True, 'issues': []}
        
        tasks = []
        
        if check_dims.get('visual_changed', True):
            tasks.append(self.visual_checker.check_visual_consistency(current_scene, prev_scene))
        else:
            tasks.append(self._return_default_result(default_result))
        
        if check_dims.get('temporal_changed', True):
            tasks.append(self.temporal_checker.check_temporal_consistency(current_scene, prev_scene))
        else:
            tasks.append(self._return_default_result(default_result))
        
        if check_dims.get('semantic_changed', True):
            tasks.append(self.semantic_checker.check_semantic_consistency(current_scene, prev_scene))
        else:
            tasks.append(self._return_default_result(default_result))
        
        if check_dims.get('style_changed', True):
            tasks.append(self.style_checker.check_style_consistency(current_scene, prev_scene))
        else:
            tasks.append(self._return_default_result(default_result))
        
        visual_result, temporal_result, semantic_result, style_result = await asyncio.gather(*tasks)
        
        overall_score = self._calculate_overall_score(
            visual_result['score'],
            temporal_result['score'],
            semantic_result['score'],
            style_result['score']
        )
        
        all_issues = []
        for result in [visual_result, temporal_result, semantic_result, style_result]:
            if not result['passed']:
                all_issues.extend(result['issues'])
        
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
    
    async def _return_default_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """返回默认结果的异步方法"""
        return result
    
    def _calculate_overall_score(self, visual_score: float, temporal_score: float, semantic_score: float, style_score: float) -> float:
        weights = self.config.get('consistency_weights', {
            'visual': 0.3,
            'temporal': 0.2,
            'semantic': 0.3,
            'style': 0.2
        })
        
        overall = (
            visual_score * weights['visual'] +
            temporal_score * weights['temporal'] +
            semantic_score * weights['semantic'] +
            style_score * weights['style']
        )
        
        return overall

