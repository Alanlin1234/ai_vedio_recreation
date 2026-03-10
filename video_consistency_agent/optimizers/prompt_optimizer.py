from typing import Dict, Any, List
from ..models.llm_client import LLMClient

class PromptOptimizer:
    def __init__(self, config: Dict[str, Any]):
# 初始化提示词优化器
        self.config = config
        self.llm_client = LLMClient(config)
    
    async def optimize(self, original_prompt: str, consistency_issues: List[str], generation_params: Dict[str, Any]) -> Dict[str, Any]:
# 根据一致性问题优化提示词
        if not consistency_issues:
            # 没有一致性问题，无需优化
            return {
                'original_prompt': original_prompt,
                'optimized_prompt': original_prompt,
                'optimization_reason': '无一致性问题，无需优化',
                'success': True
            }
        
        try:
            # 1. 添加上下文约束
            optimized_prompt = self._add_context_constraints(original_prompt, consistency_issues)
            
            # 2. 明确风格要求
            optimized_prompt = self._specify_style_requirements(optimized_prompt, consistency_issues)
            
            # 3. 强化主体元素一致性
            optimized_prompt = self._enhance_subject_consistency(optimized_prompt, consistency_issues)
            
            # 4. 调用LLM生成更优化的提示词
            llm_result = await self.llm_client.generate_optimized_prompt(original_prompt, consistency_issues)
            optimized_prompt = llm_result.get('optimized_prompt', optimized_prompt)
            
            return {
                'original_prompt': original_prompt,
                'optimized_prompt': optimized_prompt,
                'consistency_issues': consistency_issues,
                'optimization_reason': '根据一致性问题优化了提示词',
                'llm_optimization': llm_result.get('optimization_reasoning', ''),
                'success': True
            }
        except Exception as e:
            return {
                'original_prompt': original_prompt,
                'optimized_prompt': original_prompt,
                'consistency_issues': consistency_issues,
                'optimization_reason': f'提示词优化失败: {str(e)}',
                'success': False,
                'error': str(e)
            }
    
    def _add_context_constraints(self, prompt: str, issues: List[str]) -> str:
# 添加上下文约束
        if '时序' in str(issues):
            prompt += '\n\n请确保场景之间的时序关系合理，动作流畅自然，符合逻辑发展。'
        
        return prompt
    
    def _specify_style_requirements(self, prompt: str, issues: List[str]) -> str:
# 明确风格要求
        if '风格' in str(issues):
            prompt += '\n\n请保持与前一场景相同的艺术风格、色彩调色板和视觉效果。'
        
        return prompt
    
    def _enhance_subject_consistency(self, prompt: str, issues: List[str]) -> str:
# 强化主体元素一致性
        if '主体' in str(issues):
            prompt += '\n\n请确保主体元素在场景间保持一致，包括人物、物体和环境。'
        
        return prompt

