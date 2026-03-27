from typing import Dict, Any, List

from ..optimizers.prompt_optimizer import PromptOptimizer
from ..optimizers.param_optimizer import ParamOptimizer

class FeedbackModule:
    def __init__(self, config: Dict[str, Any]):
# 初始化反馈优化模块
        self.config = config
        self.prompt_optimizer = PromptOptimizer(config)
        self.param_optimizer = ParamOptimizer(config)
    
    async def generate_optimization_feedback(self, consistency_results: Dict[str, Any], original_prompt: str, generation_params: Dict[str, Any]) -> Dict[str, Any]:
# 生成优化反馈
        # 1. 生成优化后的prompt
        optimized_prompt = await self.optimize_prompt(original_prompt, consistency_results)
        
        # 2. 生成优化后的参数
        optimized_params = self.optimize_params(generation_params, consistency_results)
        
        # 3. 生成具体的优化建议
        optimization_suggestions = self.generate_optimization_suggestions(consistency_results)
        
        return {
            'original_prompt': original_prompt,
            'optimized_prompt': optimized_prompt,
            'original_params': generation_params,
            'optimized_params': optimized_params,
            'suggestions': optimization_suggestions,
            'consistency_results': consistency_results
        }
    
    async def optimize_prompt(self, original_prompt: str, consistency_results: Dict[str, Any]) -> str:
# 优化提示词
        issues = consistency_results.get('issues', [])
        
        if not issues:
            return original_prompt
        
        # 调用提示词优化器
        optimization_result = await self.prompt_optimizer.optimize(
            original_prompt=original_prompt,
            consistency_issues=issues,
            generation_params={}
        )
        
        return optimization_result.get('optimized_prompt', original_prompt)
    
    def optimize_params(self, generation_params: Dict[str, Any], consistency_results: Dict[str, Any]) -> Dict[str, Any]:
# 优化生成参数
        issues = consistency_results.get('issues', [])
        
        if not issues:
            return generation_params
        
        # 将问题转换为优化器期望的格式
        formatted_issues = []
        for issue in issues:
            issue_type = self._determine_issue_type(issue)
            formatted_issues.append({'type': issue_type, 'description': issue})
        
        # 调用参数优化器
        return self.param_optimizer.adjust_generation_params(
            original_params=generation_params,
            consistency_issues=formatted_issues
        )
    
    def generate_optimization_suggestions(self, consistency_results: Dict[str, Any]) -> List[str]:
# 生成优化建议
        issues = consistency_results.get('issues', [])
        if not issues:
            return ['一致性检查通过，无需优化']
        
        suggestions = []
        for issue in issues:
            if any(keyword in issue for keyword in ['视觉', '关键帧', '分辨率', '色彩', '光照']):
                suggestions.append(self._generate_visual_suggestions(issue))
            elif any(keyword in issue for keyword in ['时序', '动作', '流畅', '逻辑']):
                suggestions.append(self._generate_temporal_suggestions(issue))
            elif any(keyword in issue for keyword in ['语义', '内容', '主体', '关系']):
                suggestions.append(self._generate_semantic_suggestions(issue))
            elif any(keyword in issue for keyword in ['风格', '色调', '风格', '艺术']):
                suggestions.append(self._generate_style_suggestions(issue))
        
        return suggestions
    
    def _generate_visual_suggestions(self, issue: str) -> str:
# 生成视觉优化建议
        if '关键帧' in issue:
            return "建议增加关键帧权重，确保前后场景的关键帧保持连续"
        elif '分辨率' in issue:
            return "建议确保所有场景使用相同的分辨率"
        elif '色彩' in issue:
            return "建议调整色彩参数，确保前后场景的色彩风格一致"
        elif '光照' in issue:
            return "建议保持一致的光照方向和强度"
        else:
            return "建议优化视觉参数，提高前后场景的视觉一致性"
    
    def _generate_temporal_suggestions(self, issue: str) -> str:
# 生成时序优化建议
        if '动作' in issue:
            return "建议增加动作流畅度参数，确保动作自然衔接"
        elif '时序' in issue:
            return "建议调整时序参数，确保场景间的时间线连贯"
        elif '逻辑' in issue:
            return "建议优化场景的逻辑结构，确保事件发展符合逻辑"
        else:
            return "建议优化时序参数，提高场景间的流畅度"
    
    def _generate_semantic_suggestions(self, issue: str) -> str:
# 生成语义优化建议
        if '主体' in issue:
            return "建议确保前后场景的主体元素保持一致"
        elif '内容' in issue:
            return "建议优化场景内容，确保前后场景的主题统一"
        elif '关系' in issue:
            return "建议明确主体间的关系，确保前后场景的关系一致"
        else:
            return "建议优化语义参数，提高场景间的内容连贯性"
    
    def _generate_style_suggestions(self, issue: str) -> str:
# 生成风格优化建议
        if '风格' in issue:
            return "建议增加风格强度参数，确保前后场景的艺术风格统一"
        elif '色调' in issue:
            return "建议调整色调参数，确保前后场景的色彩风格一致"
        else:
            return "建议优化风格参数，提高场景间的风格一致性"
    
    def _determine_issue_type(self, issue: str) -> str:
# 确定问题类型
        if any(keyword in issue for keyword in ['视觉', '关键帧', '分辨率', '色彩', '光照']):
            return 'visual'
        elif any(keyword in issue for keyword in ['时序', '动作', '流畅', '逻辑']):
            return 'temporal'
        elif any(keyword in issue for keyword in ['语义', '内容', '主体', '关系']):
            return 'semantic'
        elif any(keyword in issue for keyword in ['风格', '色调', '风格', '艺术']):
            return 'style'
        else:
            return 'other'

