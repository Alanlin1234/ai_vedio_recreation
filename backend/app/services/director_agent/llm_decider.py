import os
import json
import logging
from typing import List, Dict, Any
from .models import NarrativeAnalysis, DirectorDecision, StoryProgress

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
            audio_content = s.get('audio_content', '')
            if audio_content:
                desc += f" [对话/旁白: {audio_content[:100]}]"
            slice_descriptions.append(f"切片{i+1}: {desc} ({duration}秒)")

        return f"""你是一个专业的视频导演，请分析以下视频内容的叙事节奏和故事逻辑进展，并给出场景调整建议。

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
    "reasoning": "决策理由",
    "story_progress": {{
        "current_location": "故事发生的当前地点",
        "current_action": "当前正在进行的动作",
        "characters_state": {{"角色名": "当前状态描述"}},
        "story_phase": "故事阶段：beginning/development/climax/resolution/ending",
        "key_events": ["关键事件1", "关键事件2"]
    }},
    "scene_story_states": [
        {{
            "scene_index": 0,
            "location": "该场景地点",
            "action": "该场景动作",
            "time_of_day": "上午/下午/傍晚/夜晚/不确定",
            "character_states": {{"角色名": "当前状态(如穿着、情绪、持有物品)"}},
            "story_phase": "该场景的故事阶段",
            "is_ending_scene": false,
            "prohibited_actions": ["禁止的下一场景动作列表"],
            "required_transitions": ["必须的过渡动作"],
            "logical_next": "下一个场景应该是什么（用于验证逻辑连贯性）"
        }}
    ],
    "logic_conflicts": [
        {{
            "type": "冲突类型：ending_restart/time_regression/location_jump/state_inconsistency",
            "description": "冲突描述",
            "affected_scenes": [受影响的场景索引列表],
            "severity": "high/medium/low"
        }}
    ]
}}

## 故事逻辑规则（必须严格遵守）:

### 1. 禁止的结束-开始组合
如果上一场景包含以下结束关键词，当前场景不能以这些动作开始：

| 上一场景结束关键词 | 禁止的当前场景开始动作 |
|------------------|---------------------|
| "到家了"、"到了"、"结束"、"下次再玩"、"再见"、"拜拜" | "出发"、"开始"、"上路"、"启程"、"再出发" |
| "睡觉了"、"休息了"、"晚安"、"休息一下" | "继续工作"、"继续活动"、"出发"、"开始" |
| "到达了"、"抵达"、"到了"、"终于到了" | "刚出发"、"刚开始"、"在去的路上"、"准备出发" |
| "回家了"、"回去休息了" | "继续前进"、"继续上路"、"去下一个地方" |

### 2. 时间逻辑规则
- 时间可以向前推进：上午→下午→傍晚→夜晚
- 时间禁止倒退：傍晚→上午（除非有过渡说明）
- 同一场景内时间必须一致
- 禁止时间突变而无过渡

### 3. 地点逻辑规则
- 地点变更必须有过渡动作（走路、开车等）
- 禁止无过渡的瞬移
- "到家了"后下一场景只能是室内或告别相关

### 4. 角色状态规则
- 角色状态必须保持连贯（服装、物品、情绪）
- 状态变更必须有逻辑过渡
- 禁止无原因的角色状态突变

### 5. 对话逻辑规则
- 对话必须回应上一场景
- "谢谢"后应是"不客气"
- "再见"后不能是"你好"
- 对话内容必须与场景状态匹配

### 6. 物理逻辑规则
- 禁止无重力、飘浮等违反物理规律的动作
- 禁止违反人体力学的动作
- 禁止物体无支撑的悬浮

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
            
            story_progress_data = data.get('story_progress', {})
            story_progress = None
            if story_progress_data:
                story_progress = StoryProgress(
                    current_location=story_progress_data.get('current_location', ''),
                    current_action=story_progress_data.get('current_action', ''),
                    characters_state=story_progress_data.get('characters_state', {}),
                    story_phase=story_progress_data.get('story_phase', ''),
                    key_events=story_progress_data.get('key_events', [])
                )
            
            return NarrativeAnalysis(
                rhythm_pattern=data.get('rhythm_pattern', '未知'),
                climax_positions=data.get('climax_positions', []),
                transition_positions=data.get('transition_positions', []),
                overall_pace=data.get('overall_pace', '适中'),
                scene_count_suggestion=data.get('scene_count_suggestion', 5),
                reasoning=data.get('reasoning', ''),
                story_progress=story_progress,
                scene_story_states=data.get('scene_story_states', [])
            )
        except Exception as e:
            logger.warning(f"解析叙事分析结果失败: {e}")
            return NarrativeAnalysis(
                rhythm_pattern='未知',
                climax_positions=[],
                transition_positions=[],
                overall_pace='适中',
                scene_count_suggestion=5,
                reasoning='解析失败',
                story_progress=None,
                scene_story_states=[]
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
