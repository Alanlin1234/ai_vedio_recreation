import os
import json
import logging
from typing import List, Dict, Any
from .models import NarrativeAnalysis, DirectorDecision

logger = logging.getLogger(__name__)


class DirectorLLMDecider:
    """LLM决策器 - 精调决策，基于语义理解"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.llm_service = None
        self._init_llm_service()

    def _init_llm_service(self):
        """初始化LLM服务"""
        try:
            from app.services.qwen_video_service import QwenVideoService
            self.llm_service = QwenVideoService()
        except Exception as e:
            logger.warning(f"LLM服务初始化失败: {e}")
            self.llm_service = None

    async def analyze_narrative_rhythm(self, video_script: str, 
                                       slices: List[Dict[str, Any]],
                                       rule_suggestion: Dict[str, Any]) -> NarrativeAnalysis:
        """分析叙事节奏"""
        if not self.llm_service:
            return self._default_narrative_analysis(len(slices))
        
        try:
            prompt = self._build_narrative_prompt(video_script, slices, rule_suggestion)
            
            result = self.llm_service.optimize_prompt_with_qwen_plus_latest(
                prompt,
                {"output_format": "json"}
            )
            
            if result.get('success'):
                return self._parse_narrative_result(result.get('optimized_prompt', ''))
            
            return self._default_narrative_analysis(len(slices))
            
        except Exception as e:
            logger.warning(f"叙事节奏分析失败: {e}")
            return self._default_narrative_analysis(len(slices))

    def _build_narrative_prompt(self, video_script: str, 
                                slices: List[Dict[str, Any]],
                                rule_suggestion: Dict[str, Any]) -> str:
        """构建叙事分析提示词"""
        slice_descriptions = []
        for i, s in enumerate(slices):
            desc = s.get('description', f'切片{i+1}')
            duration = s.get('duration', 5)
            slice_descriptions.append(f"切片{i+1}: {desc} ({duration}秒)")
        
        return f"""你是一个专业的视频导演，请分析以下视频内容的叙事节奏，并给出场景调整建议。

## 视频脚本摘要
{video_script[:2000]}

## 原始切片信息
{chr(10).join(slice_descriptions)}

## 规则引擎初步分析
- 建议合并的切片对: {rule_suggestion.get('merge_pairs', [])}
- 建议拆分的切片: {rule_suggestion.get('split_indices', [])}
- 建议场景数量: {rule_suggestion.get('suggested_scene_count', len(slices))}

## 请分析并返回JSON格式结果
{{
    "rhythm_pattern": "节奏模式，如'快-慢-快'或'渐进式'",
    "climax_positions": [高潮位置索引列表],
    "transition_positions": [转场位置索引列表],
    "overall_pace": "整体节奏，如'紧凑'、'舒缓'、'适中'",
    "scene_count_suggestion": 建议的场景数量,
    "reasoning": "决策理由"
}}

请只返回JSON，不要有其他内容。"""

    def _parse_narrative_result(self, result: str) -> NarrativeAnalysis:
        """解析叙事分析结果"""
        try:
            json_str = result
            if '```json' in result:
                json_str = result.split('```json')[1].split('```')[0]
            elif '```' in result:
                json_str = result.split('```')[1].split('```')[0]
            
            data = json.loads(json_str.strip())
            
            return NarrativeAnalysis(
                rhythm_pattern=data.get('rhythm_pattern', '未知'),
                climax_positions=data.get('climax_positions', []),
                transition_positions=data.get('transition_positions', []),
                overall_pace=data.get('overall_pace', '适中'),
                scene_count_suggestion=data.get('scene_count_suggestion', 5),
                reasoning=data.get('reasoning', '')
            )
        except Exception as e:
            logger.warning(f"解析叙事分析结果失败: {e}")
            return NarrativeAnalysis(
                rhythm_pattern='未知',
                climax_positions=[],
                transition_positions=[],
                overall_pace='适中',
                scene_count_suggestion=5,
                reasoning='解析失败'
            )

    def _default_narrative_analysis(self, slice_count: int) -> NarrativeAnalysis:
        """默认叙事分析"""
        return NarrativeAnalysis(
            rhythm_pattern='未知',
            climax_positions=[],
            transition_positions=[],
            overall_pace='适中',
            scene_count_suggestion=slice_count,
            reasoning='LLM服务不可用，使用默认分析'
        )

    def evaluate_content_complexity(self, slice_info: Dict[str, Any]) -> str:
        """评估内容复杂度"""
        keyframes = slice_info.get('keyframes', [])
        description = slice_info.get('description', '')
        
        complexity_score = 0
        
        if len(keyframes) > 3:
            complexity_score += 1
        
        complex_keywords = ['复杂', '多个', '变化', '转换', '冲突', '高潮']
        for kw in complex_keywords:
            if kw in description:
                complexity_score += 1
        
        if complexity_score >= 2:
            return "complex"
        elif complexity_score >= 1:
            return "medium"
        else:
            return "simple"

    async def make_scene_decision(self,
                                  initial_suggestion: Dict[str, Any],
                                  narrative_analysis: NarrativeAnalysis,
                                  constraints: Dict[str, Any]) -> List[DirectorDecision]:
        """做出最终场景决策"""
        decisions = []
        
        original_count = initial_suggestion.get('original_count', 5)
        merge_pairs = initial_suggestion.get('merge_pairs', [])
        split_indices = initial_suggestion.get('split_indices', [])
        
        merged_indices = set()
        
        for pair in merge_pairs:
            i, j = pair
            if i not in merged_indices and j not in merged_indices:
                decisions.append(DirectorDecision(
                    action="merge",
                    source_indices=[i, j],
                    target_count=1,
                    confidence=0.7,
                    reasoning=f"切片{i+1}和{j+1}视觉相似度高，建议合并",
                    target_durations=[initial_suggestion.get('analyses', [])[i].get('duration', 5) * 2 if i < len(initial_suggestion.get('analyses', [])) else 10]
                ))
                merged_indices.add(i)
                merged_indices.add(j)
        
        for idx in split_indices:
            if idx not in merged_indices:
                decisions.append(DirectorDecision(
                    action="split",
                    source_indices=[idx],
                    target_count=2,
                    confidence=0.6,
                    reasoning=f"切片{idx+1}运动强度高或存在场景变化，建议拆分",
                    target_durations=[2.5, 2.5]
                ))
        
        for i in range(original_count):
            if i not in merged_indices and i not in split_indices:
                decisions.append(DirectorDecision(
                    action="keep",
                    source_indices=[i],
                    target_count=1,
                    confidence=0.8,
                    reasoning=f"切片{i+1}保持不变",
                    target_durations=[5.0]
                ))
        
        return decisions

    def determine_narrative_role(self, scene_index: int, total_scenes: int,
                                narrative_analysis: NarrativeAnalysis) -> str:
        """确定场景的叙事角色"""
        if scene_index == 0:
            return "intro"
        elif scene_index == total_scenes - 1:
            return "conclusion"
        elif scene_index in narrative_analysis.climax_positions:
            return "climax"
        elif scene_index in narrative_analysis.transition_positions:
            return "transition"
        else:
            return "development"

    def calculate_scene_duration(self, source_slices: List[Dict], 
                                action: str,
                                narrative_role: str) -> float:
        """计算场景时长"""
        if action == "merge":
            total_duration = sum(s.get('duration', 5) for s in source_slices)
            return total_duration * 0.9
        elif action == "split":
            base_duration = source_slices[0].get('duration', 5) if source_slices else 5
            return base_duration / 2
        else:
            base_duration = source_slices[0].get('duration', 5) if source_slices else 5
            
            role_multipliers = {
                'intro': 0.8,
                'development': 1.0,
                'climax': 1.2,
                'transition': 0.7,
                'conclusion': 0.9
            }
            
            multiplier = role_multipliers.get(narrative_role, 1.0)
            return base_duration * multiplier
