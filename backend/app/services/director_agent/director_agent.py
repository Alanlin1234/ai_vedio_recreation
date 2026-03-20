import os
import logging
from typing import List, Dict, Any
from .models import DirectorPlan, DirectorDecision, ScenePlan
from .rule_engine import DirectorRuleEngine
from .llm_decider import DirectorLLMDecider

logger = logging.getLogger(__name__)


class DirectorAgent:
    """导演Agent - 智能场景规划
    
    综合考虑内容复杂度、叙事节奏和视觉变化来调整场景数量。
    支持场景合并、拆分、重组等操作。
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.min_ratio = self.config.get('min_ratio', 0.5)
        self.max_ratio = self.config.get('max_ratio', 2.0)
        
        self.rule_engine = DirectorRuleEngine(self.config.get('rule_engine', {}))
        self.llm_decider = DirectorLLMDecider(self.config.get('llm_decider', {}))
        
        self.logger = logger

    async def plan_scenes(self,
                         video_script: str,
                         original_slices: List[Dict[str, Any]]) -> DirectorPlan:
        """
        主入口：规划场景
        
        Args:
            video_script: 视频脚本内容
            original_slices: 原始切片列表
            
        Returns:
            DirectorPlan: 包含最终场景列表和映射关系
        """
        self.logger.info(f"导演Agent开始规划场景，原始切片数: {len(original_slices)}")
        
        initial_suggestion = self.rule_engine.get_initial_suggestion(original_slices)
        self.logger.info(f"规则引擎初筛完成，建议场景数: {initial_suggestion.get('suggested_scene_count')}")
        
        narrative_analysis = await self.llm_decider.analyze_narrative_rhythm(
            video_script, original_slices, initial_suggestion
        )
        self.logger.info(f"叙事分析完成，节奏模式: {narrative_analysis.rhythm_pattern}")
        
        constraints = {
            'min_scenes': max(1, int(len(original_slices) * self.min_ratio)),
            'max_scenes': int(len(original_slices) * self.max_ratio),
            'original_count': len(original_slices)
        }
        
        decisions = await self.llm_decider.make_scene_decision(
            initial_suggestion, narrative_analysis, constraints
        )
        
        scenes = self._build_scene_plans(
            decisions, original_slices, narrative_analysis, initial_suggestion
        )
        
        final_count = len(scenes)
        final_count = self._apply_constraints(final_count, len(original_slices))
        
        if len(scenes) != final_count:
            scenes = self._adjust_scene_count(scenes, final_count, decisions)
        
        adjustment_ratio = final_count / len(original_slices) if original_slices else 1.0
        
        reasoning = self._generate_reasoning(
            initial_suggestion, narrative_analysis, decisions, final_count
        )
        
        plan = DirectorPlan(
            original_slice_count=len(original_slices),
            final_scene_count=final_count,
            scenes=scenes,
            decisions=decisions,
            reasoning=reasoning,
            adjustment_ratio=adjustment_ratio,
            narrative_analysis=narrative_analysis
        )
        
        self.logger.info(f"导演规划完成，最终场景数: {final_count}，调整比例: {adjustment_ratio:.2f}")
        
        return plan

    def _apply_constraints(self, scene_count: int, original_count: int) -> int:
        """应用场景数量约束"""
        min_scenes = max(1, int(original_count * self.min_ratio))
        max_scenes = max(min_scenes, int(original_count * self.max_ratio))
        
        constrained_count = max(min_scenes, min(scene_count, max_scenes))
        
        if constrained_count != scene_count:
            self.logger.info(f"场景数量被约束: {scene_count} -> {constrained_count}")
        
        return constrained_count

    def _build_scene_plans(self,
                          decisions: List[DirectorDecision],
                          original_slices: List[Dict[str, Any]],
                          narrative_analysis,
                          initial_suggestion: Dict[str, Any]) -> List[ScenePlan]:
        """构建场景规划列表"""
        scenes = []
        scene_id = 0
        current_time = 0.0
        
        analyses = initial_suggestion.get('analyses', [])
        
        for decision in decisions:
            source_slices_data = [original_slices[i] for i in decision.source_indices if i < len(original_slices)]
            
            all_keyframes = []
            for s in source_slices_data:
                all_keyframes.extend(s.get('keyframes', []))
            
            if decision.action == "merge":
                duration = sum(s.get('duration', 5) for s in source_slices_data) * 0.9
                complexity = "medium"
                motion_intensity = sum(
                    analyses[i].get('motion_intensity', 0) for i in decision.source_indices if i < len(analyses)
                ) / len(decision.source_indices) if decision.source_indices else 0
            elif decision.action == "split":
                base_duration = source_slices_data[0].get('duration', 5) if source_slices_data else 5
                duration = base_duration / 2
                complexity = "complex"
                motion_intensity = analyses[decision.source_indices[0]].get('motion_intensity', 0) if decision.source_indices and decision.source_indices[0] < len(analyses) else 0
                
                for split_idx in range(decision.target_count):
                    narrative_role = self.llm_decider.determine_narrative_role(
                        scene_id, len(decisions) * decision.target_count, narrative_analysis
                    )
                    
                    scene = ScenePlan(
                        scene_id=scene_id,
                        source_slices=decision.source_indices,
                        source_keyframes=all_keyframes,
                        duration=duration,
                        complexity=complexity,
                        narrative_role=narrative_role,
                        motion_intensity=motion_intensity,
                        merge_type="split",
                        start_time=current_time,
                        end_time=current_time + duration,
                        description=f"场景{scene_id + 1} (拆分自切片{decision.source_indices[0] + 1})",
                        slice_data=source_slices_data[0] if source_slices_data else {}
                    )
                    scenes.append(scene)
                    scene_id += 1
                    current_time += duration
                
                continue
            else:
                duration = source_slices_data[0].get('duration', 5) if source_slices_data else 5
                complexity = self.llm_decider.evaluate_content_complexity(source_slices_data[0]) if source_slices_data else "simple"
                motion_intensity = analyses[decision.source_indices[0]].get('motion_intensity', 0) if decision.source_indices and decision.source_indices[0] < len(analyses) else 0
            
            narrative_role = self.llm_decider.determine_narrative_role(
                scene_id, len(decisions), narrative_analysis
            )
            
            scene = ScenePlan(
                scene_id=scene_id,
                source_slices=decision.source_indices,
                source_keyframes=all_keyframes,
                duration=duration,
                complexity=complexity,
                narrative_role=narrative_role,
                motion_intensity=motion_intensity,
                merge_type=decision.action,
                start_time=current_time,
                end_time=current_time + duration,
                description=f"场景{scene_id + 1}" + (f" (合并自切片{', '.join(str(i+1) for i in decision.source_indices)})" if decision.action == "merge" else ""),
                slice_data=source_slices_data[0] if len(source_slices_data) == 1 else {'merged_sources': source_slices_data}
            )
            scenes.append(scene)
            scene_id += 1
            current_time += duration
        
        return scenes

    def _adjust_scene_count(self, scenes: List[ScenePlan], target_count: int,
                           decisions: List[DirectorDecision]) -> List[ScenePlan]:
        """调整场景数量以符合约束"""
        current_count = len(scenes)
        
        if current_count == target_count:
            return scenes
        
        if current_count > target_count:
            return self._merge_scenes(scenes, current_count - target_count)
        else:
            return self._split_scenes(scenes, target_count - current_count)

    def _merge_scenes(self, scenes: List[ScenePlan], merge_count: int) -> List[ScenePlan]:
        """合并场景"""
        if merge_count <= 0:
            return scenes
        
        merged_scenes = []
        i = 0
        
        while i < len(scenes):
            if merge_count > 0 and i + 1 < len(scenes):
                current = scenes[i]
                next_scene = scenes[i + 1]
                
                merged_scene = ScenePlan(
                    scene_id=len(merged_scenes),
                    source_slices=current.source_slices + next_scene.source_slices,
                    source_keyframes=current.source_keyframes + next_scene.source_keyframes,
                    duration=current.duration + next_scene.duration,
                    complexity="medium",
                    narrative_role=current.narrative_role,
                    motion_intensity=(current.motion_intensity + next_scene.motion_intensity) / 2,
                    merge_type="merged",
                    start_time=current.start_time,
                    end_time=next_scene.end_time,
                    description=f"场景{len(merged_scenes) + 1} (合并场景)",
                    slice_data={'merged_sources': [current.slice_data, next_scene.slice_data]}
                )
                
                merged_scenes.append(merged_scene)
                i += 2
                merge_count -= 1
            else:
                scene = scenes[i]
                scene.scene_id = len(merged_scenes)
                merged_scenes.append(scene)
                i += 1
        
        return merged_scenes

    def _split_scenes(self, scenes: List[ScenePlan], split_count: int) -> List[ScenePlan]:
        """拆分场景"""
        if split_count <= 0:
            return scenes
        
        result_scenes = []
        
        for scene in scenes:
            if split_count > 0 and scene.motion_intensity > 0.3:
                half_duration = scene.duration / 2
                
                scene1 = ScenePlan(
                    scene_id=len(result_scenes),
                    source_slices=scene.source_slices,
                    source_keyframes=scene.source_keyframes[:len(scene.source_keyframes)//2] if scene.source_keyframes else [],
                    duration=half_duration,
                    complexity=scene.complexity,
                    narrative_role=scene.narrative_role,
                    motion_intensity=scene.motion_intensity,
                    merge_type="split",
                    start_time=scene.start_time,
                    end_time=scene.start_time + half_duration,
                    description=f"场景{len(result_scenes) + 1}A (拆分)",
                    slice_data=scene.slice_data
                )
                
                scene2 = ScenePlan(
                    scene_id=len(result_scenes) + 1,
                    source_slices=scene.source_slices,
                    source_keyframes=scene.source_keyframes[len(scene.source_keyframes)//2:] if scene.source_keyframes else [],
                    duration=half_duration,
                    complexity=scene.complexity,
                    narrative_role=scene.narrative_role,
                    motion_intensity=scene.motion_intensity,
                    merge_type="split",
                    start_time=scene.start_time + half_duration,
                    end_time=scene.end_time,
                    description=f"场景{len(result_scenes) + 1}B (拆分)",
                    slice_data=scene.slice_data
                )
                
                result_scenes.append(scene1)
                result_scenes.append(scene2)
                split_count -= 1
            else:
                scene.scene_id = len(result_scenes)
                result_scenes.append(scene)
        
        return result_scenes

    def _generate_reasoning(self,
                           initial_suggestion: Dict[str, Any],
                           narrative_analysis,
                           decisions: List[DirectorDecision],
                           final_count: int) -> str:
        """生成决策理由"""
        merge_count = sum(1 for d in decisions if d.action == "merge")
        split_count = sum(1 for d in decisions if d.action == "split")
        keep_count = sum(1 for d in decisions if d.action == "keep")
        
        reasoning_parts = [
            f"原始切片数: {initial_suggestion.get('original_count', 0)}",
            f"最终场景数: {final_count}",
            f"叙事节奏: {narrative_analysis.rhythm_pattern}",
            f"整体节奏: {narrative_analysis.overall_pace}",
            f"合并场景数: {merge_count}",
            f"拆分场景数: {split_count}",
            f"保持不变: {keep_count}"
        ]
        
        if narrative_analysis.reasoning:
            reasoning_parts.append(f"LLM分析: {narrative_analysis.reasoning}")
        
        return " | ".join(reasoning_parts)

    def get_scene_mapping(self, plan: DirectorPlan) -> Dict[int, List[int]]:
        """获取场景到原始切片的映射"""
        mapping = {}
        for scene in plan.scenes:
            mapping[scene.scene_id] = scene.source_slices
        return mapping

    def get_slice_to_scene_mapping(self, plan: DirectorPlan) -> Dict[int, int]:
        """获取原始切片到场景的映射"""
        mapping = {}
        for scene in plan.scenes:
            for slice_idx in scene.source_slices:
                mapping[slice_idx] = scene.scene_id
        return mapping
