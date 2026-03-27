from typing import Dict, Any, List
from ..models.model_manager import ModelManager

class ContentChecker:
    def __init__(self, config: Dict[str, Any], model_manager: ModelManager):
# 初始化内容一致性检查器
        self.config = config
        self.content_threshold = config.get('content_threshold', 0.8)
        self.model_manager = model_manager
    
    async def check(self, current_scene: Dict[str, Any], previous_scene: Dict[str, Any]) -> Dict[str, Any]:
# 检查内容一致性
        if not previous_scene:
            # 第一个场景，无需检查一致性
            return {
                'success': True,
                'content_consistency_score': 1.0,
                'issues': [],
                'passed': True
            }
        
        try:
            # 获取视频路径
            current_video_path = current_scene.get('video_path')
            previous_video_path = previous_scene.get('video_path')
            
            if not current_video_path or not previous_video_path:
                raise ValueError("场景缺少视频路径")
            
            # 使用VLM分析两个场景的内容
            vlm_client = self.model_manager.get_vlm_client()
            current_content = await vlm_client.analyze_video_content(current_video_path)
            previous_content = await vlm_client.analyze_video_content(previous_video_path)
            
            # 使用LLM分析内容连贯性
            llm_client = self.model_manager.get_llm_client()
            coherence_result = await llm_client.analyze_content_coherence(
                previous_content['description'],
                current_content['description']
            )
            
            # 检查角色一致性
            character_consistency = self._check_character_consistency(previous_content, current_content)
            
            # 检查背景一致性
            background_consistency = self._check_background_consistency(previous_content, current_content)
            
            # 检查主题一致性
            theme_consistency = self._check_theme_consistency(previous_content, current_content)
            
            # 收集问题
            issues = []
            
            if coherence_result['score'] < self.content_threshold * 100:
                issues.extend(coherence_result.get('suggestions', []))
            
            if not character_consistency:
                issues.append("角色不一致")
            
            if not background_consistency:
                issues.append("背景不一致")
            
            if not theme_consistency:
                issues.append("主题不一致")
            
            # 综合评分（将LLM评分转换为0-1范围）
            overall_score = coherence_result['score'] / 100.0
            
            passed = overall_score >= self.content_threshold and character_consistency and background_consistency and theme_consistency
            
            return {
                'success': True,
                'content_consistency_score': overall_score,
                'coherence_analysis': coherence_result,
                'character_consistency': character_consistency,
                'background_consistency': background_consistency,
                'theme_consistency': theme_consistency,
                'issues': issues,
                'passed': passed
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'content_consistency_score': 0.0,
                'issues': [f"内容一致性检查失败: {str(e)}"],
                'passed': False
            }
    
    def _check_character_consistency(self, previous_content: Dict[str, Any], current_content: Dict[str, Any]) -> bool:
# 检查角色一致性
        prev_characters = set(previous_content.get('subjects', []))
        curr_characters = set(current_content.get('subjects', []))
        
        # 如果前一场景没有角色信息，认为一致
        if not prev_characters:
            return True
        
        # 检查当前场景是否包含前一场景的主要角色
        return len(prev_characters.intersection(curr_characters)) > 0
    
    def _check_background_consistency(self, previous_content: Dict[str, Any], current_content: Dict[str, Any]) -> bool:
# 检查背景一致性
        prev_background = previous_content.get('description', '')
        curr_background = current_content.get('description', '')
        
        # 如果前一场景没有背景信息，认为一致
        if not prev_background:
            return True
        
        # 简单的背景相似性检查，实际应用中可以使用更复杂的算法
        # 检查当前场景背景是否包含前一场景的主要背景元素
        return any(keyword in curr_background for keyword in ['公园', '城市', '森林', '室内'])
    
    def _check_theme_consistency(self, previous_content: Dict[str, Any], current_content: Dict[str, Any]) -> bool:
# 检查主题一致性
        prev_style = previous_content.get('style', '')
        curr_style = current_content.get('style', '')
        
        # 检查风格是否一致
        return prev_style == curr_style


