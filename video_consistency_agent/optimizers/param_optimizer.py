from typing import Dict, Any, List

class ParamOptimizer:
    def __init__(self, config: Dict[str, Any]):
# 初始化参数优化器
        self.config = config
        self.style_strength_adjustment = config.get('style_strength_adjustment', 0.1)
        self.keyframe_weight_adjustment = config.get('keyframe_weight_adjustment', 0.2)
    
    def adjust_generation_params(self, original_params: Dict[str, Any], consistency_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
# 根据一致性问题调整视频生成参数
        if not consistency_issues:
            return original_params
        
        # 分析一致性问题类型
        issue_types = set(issue['type'] for issue in consistency_issues)
        
        # 根据问题类型调整参数
        adjusted_params = original_params.copy()
        
        for issue_type in issue_types:
            if issue_type in ['visual', 'style']:
                adjusted_params = self.adjust_style_strength(adjusted_params, consistency_issues)
                adjusted_params = self.adjust_keyframe_weight(adjusted_params, consistency_issues)
            elif issue_type == 'temporal':
                adjusted_params = self.adjust_temporal_params(adjusted_params, consistency_issues)
            elif issue_type == 'semantic':
                adjusted_params = self.adjust_semantic_params(adjusted_params, consistency_issues)
        
        return adjusted_params
    
    def adjust_style_strength(self, params: Dict[str, Any], consistency_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
# 调整风格强度
        adjusted_params = params.copy()
        
        # 查找风格相关问题
        style_issues = [issue for issue in consistency_issues if issue['type'] in ['visual', 'style']]
        
        if style_issues:
            # 增加风格强度，提高风格一致性
            current_strength = params.get('style_strength', 0.5)
            adjusted_params['style_strength'] = min(current_strength + self.style_strength_adjustment, 1.0)
        
        return adjusted_params
    
    def adjust_keyframe_weight(self, params: Dict[str, Any], consistency_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
# 调整关键帧权重
        adjusted_params = params.copy()
        
        # 查找关键帧相关问题
        keyframe_issues = [issue for issue in consistency_issues if 'keyframe' in issue.get('description', '').lower()]
        
        if keyframe_issues:
            # 增加关键帧权重，提高关键帧一致性
            current_weight = params.get('keyframe_weight', 0.5)
            adjusted_params['keyframe_weight'] = min(current_weight + self.keyframe_weight_adjustment, 1.0)
        
        return adjusted_params
    
    def adjust_temporal_params(self, params: Dict[str, Any], consistency_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
# 调整时序相关参数
        adjusted_params = params.copy()
        
        # 调整时序相关参数，提高动作连贯性
        adjusted_params['motion_blur'] = params.get('motion_blur', 0.3) + 0.1
        adjusted_params['frame_interpolation_quality'] = params.get('frame_interpolation_quality', 'medium')
        
        return adjusted_params
    
    def adjust_semantic_params(self, params: Dict[str, Any], consistency_issues: List[Dict[str, Any]]) -> Dict[str, Any]:
# 调整语义相关参数
        adjusted_params = params.copy()
        
        # 调整语义相关参数，提高内容一致性
        adjusted_params['content_weight'] = params.get('content_weight', 0.5) + 0.1
        adjusted_params['context_weight'] = params.get('context_weight', 0.3) + 0.2
        
        return adjusted_params
    
    def reset_params_for_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
# 重置参数以进行重试
        reset_params = params.copy()
        
        # 重置关键参数，提高生成多样性
        reset_params['random_seed'] = None  # 使用新的随机种子
        reset_params['style_strength'] = params.get('style_strength', 0.5)  # 重置风格强度
        reset_params['keyframe_weight'] = params.get('keyframe_weight', 0.5)  # 重置关键帧权重
        
        return reset_params
    
    def optimize_params_for_coherence(self, params: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
# 根据场景上下文优化参数以提高连贯性
        optimized_params = params.copy()
        
        # 如果有前一场景信息，调整参数以提高连贯性
        if scene_context.get('previous_scene'):
            optimized_params['context_weight'] = 0.8  # 增加上下文权重
            optimized_params['style_strength'] = 0.7  # 确保风格一致性
            optimized_params['keyframe_weight'] = 0.9  # 强化关键帧约束
        
        return optimized_params

