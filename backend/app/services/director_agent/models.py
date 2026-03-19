from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class SceneAction(Enum):
    KEEP = "keep"
    MERGE = "merge"
    SPLIT = "split"
    REORGANIZE = "reorganize"


class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class NarrativeRole(Enum):
    INTRO = "intro"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    TRANSITION = "transition"
    CONCLUSION = "conclusion"


@dataclass
class DirectorDecision:
    action: str
    source_indices: List[int]
    target_count: int
    confidence: float
    reasoning: str
    target_durations: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'source_indices': self.source_indices,
            'target_count': self.target_count,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'target_durations': self.target_durations
        }


@dataclass
class ScenePlan:
    scene_id: int
    source_slices: List[int]
    source_keyframes: List[str]
    duration: float
    complexity: str
    narrative_role: str
    motion_intensity: float
    merge_type: str
    start_time: float = 0.0
    end_time: float = 0.0
    description: str = ""
    slice_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scene_id': self.scene_id,
            'source_slices': self.source_slices,
            'source_keyframes': self.source_keyframes,
            'duration': self.duration,
            'complexity': self.complexity,
            'narrative_role': self.narrative_role,
            'motion_intensity': self.motion_intensity,
            'merge_type': self.merge_type,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'description': self.description
        }


@dataclass
class DirectorPlan:
    original_slice_count: int
    final_scene_count: int
    scenes: List[ScenePlan]
    decisions: List[DirectorDecision]
    reasoning: str
    adjustment_ratio: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_slice_count': self.original_slice_count,
            'final_scene_count': self.final_scene_count,
            'scenes': [s.to_dict() for s in self.scenes],
            'decisions': [d.to_dict() for d in self.decisions],
            'reasoning': self.reasoning,
            'adjustment_ratio': self.adjustment_ratio
        }


@dataclass
class SliceAnalysis:
    slice_index: int
    motion_intensity: float
    visual_complexity: float
    color_variance: float
    keyframe_similarity: float
    has_scene_change: bool
    suggested_action: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'slice_index': self.slice_index,
            'motion_intensity': self.motion_intensity,
            'visual_complexity': self.visual_complexity,
            'color_variance': self.color_variance,
            'keyframe_similarity': self.keyframe_similarity,
            'has_scene_change': self.has_scene_change,
            'suggested_action': self.suggested_action,
            'confidence': self.confidence
        }


@dataclass
class NarrativeAnalysis:
    rhythm_pattern: str
    climax_positions: List[int]
    transition_positions: List[int]
    overall_pace: str
    scene_count_suggestion: int
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rhythm_pattern': self.rhythm_pattern,
            'climax_positions': self.climax_positions,
            'transition_positions': self.transition_positions,
            'overall_pace': self.overall_pace,
            'scene_count_suggestion': self.scene_count_suggestion,
            'reasoning': self.reasoning
        }
