from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class FramingType(Enum):
    EXTREME_LONG_SHOT = "Extreme Long Shot"
    LONG_SHOT = "Long Shot"
    FULL_SHOT = "Full Shot"
    MEDIUM_LONG_SHOT = "Medium Long Shot"
    MEDIUM_SHOT = "Medium Shot"
    MEDIUM_CLOSE_UP = "Medium Close-Up"
    CLOSE_UP = "Close-Up"
    EXTREME_CLOSE_UP = "Extreme Close-Up"


class CameraAngle(Enum):
    EYE_LEVEL = "Eye-level"
    LOW_ANGLE = "Low Angle"
    HIGH_ANGLE = "High Angle"
    BIRDS_EYE = "Bird's Eye View"
    WORMS_EYE = "Worm's Eye View"
    DUTCH_ANGLE = "Dutch Angle"


class CameraMovement(Enum):
    STATIC = "Static"
    PAN_LEFT = "Pan Left"
    PAN_RIGHT = "Pan Right"
    TILT_UP = "Tilt Up"
    TILT_DOWN = "Tilt Down"
    DOLLY_IN = "Dolly In (Push In)"
    DOLLY_OUT = "Dolly Out (Pull Out)"
    ZOOM_IN = "Zoom In"
    ZOOM_OUT = "Zoom Out"
    TRACKING = "Tracking Shot"
    CRANE_UP = "Crane Up"
    CRANE_DOWN = "Crane Down"
    HANDHELD = "Handheld"
    STEADICAM = "Steadicam"


class TransitionType(Enum):
    CUT = "Cut"
    CROSS_DISSOLVE = "Cross Dissolve"
    FADE_IN = "Fade In"
    FADE_OUT = "Fade Out"
    WIPE = "Wipe"
    MATCH_CUT = "Match Cut"
    JUMP_CUT = "Jump Cut"
    IRIS = "Iris"


@dataclass
class AudioInfo:
    dialogue: str = ""
    background_music: str = ""
    sound_effects: List[str] = field(default_factory=list)
    voice_tone: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'dialogue': self.dialogue,
            'background_music': self.background_music,
            'sound_effects': self.sound_effects,
            'voice_tone': self.voice_tone
        }


@dataclass
class VisualElements:
    characters: List[Dict[str, str]] = field(default_factory=list)
    environment: str = ""
    lighting: str = ""
    color_palette: List[str] = field(default_factory=list)
    mood: str = ""
    props: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'characters': self.characters,
            'environment': self.environment,
            'lighting': self.lighting,
            'color_palette': self.color_palette,
            'mood': self.mood,
            'props': self.props
        }


@dataclass
class ShotBreakdown:
    shot_number: int
    framing: str
    camera_angle: str
    camera_movement: str
    description: str
    audio: AudioInfo
    duration: str
    transition: str
    key_action: str = ""
    visual_focus: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'shot_number': self.shot_number,
            'framing': self.framing,
            'camera_angle': self.camera_angle,
            'camera_movement': self.camera_movement,
            'description': self.description,
            'audio': self.audio.to_dict() if isinstance(self.audio, AudioInfo) else self.audio,
            'duration': self.duration,
            'transition': self.transition,
            'key_action': self.key_action,
            'visual_focus': self.visual_focus
        }
    
    def to_table_row(self) -> str:
        return f"| {self.shot_number} | {self.framing} | {self.camera_angle} | {self.camera_movement} | {self.description[:50]}... | {self.duration} | {self.transition} |"


@dataclass
class TechnicalParams:
    aspect_ratio: str = "16:9"
    fps: int = 24
    resolution: str = "1920x1080"
    codec: str = "H.264"
    bitrate: str = "10Mbps"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'aspect_ratio': self.aspect_ratio,
            'fps': self.fps,
            'resolution': self.resolution,
            'codec': self.codec,
            'bitrate': self.bitrate
        }


@dataclass
class ScenePromptV2:
    scene_id: int
    shot_breakdown: ShotBreakdown
    visual_elements: VisualElements
    technical_params: TechnicalParams
    video_prompt: str = ""
    narrative_context: str = ""
    previous_scene_reference: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scene_id': self.scene_id,
            'shot_breakdown': self.shot_breakdown.to_dict() if isinstance(self.shot_breakdown, ShotBreakdown) else self.shot_breakdown,
            'visual_elements': self.visual_elements.to_dict() if isinstance(self.visual_elements, VisualElements) else self.visual_elements,
            'technical_params': self.technical_params.to_dict() if isinstance(self.technical_params, TechnicalParams) else self.technical_params,
            'video_prompt': self.video_prompt,
            'narrative_context': self.narrative_context,
            'previous_scene_reference': self.previous_scene_reference
        }
    
    def to_shot_breakdown_table(self) -> str:
        header = """
## Shot Breakdown Table

| Shot | Framing | Camera Angle | Camera Movement | Description | Duration | Transition |
|------|---------|--------------|-----------------|-------------|----------|------------|
"""
        rows = self.shot_breakdown.to_table_row() if isinstance(self.shot_breakdown, ShotBreakdown) else ""
        return header + rows


@dataclass
class CameraScript:
    scenes: List[ScenePromptV2]
    total_duration: float
    overall_style: str
    narrative_arc: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenes': [s.to_dict() for s in self.scenes],
            'total_duration': self.total_duration,
            'overall_style': self.overall_style,
            'narrative_arc': self.narrative_arc
        }
    
    def to_full_script(self) -> str:
        script = f"""
# Camera Script

## Overview
- **Total Duration**: {self.total_duration}s
- **Overall Style**: {self.overall_style}
- **Narrative Arc**: {self.narrative_arc}

## Scene Breakdowns

"""
        for scene in self.scenes:
            script += f"### Scene {scene.scene_id}\n\n"
            if isinstance(scene.shot_breakdown, ShotBreakdown):
                script += f"""
| Shot | Framing | Camera Angle | Camera Movement | Description | Duration | Transition |
|------|---------|--------------|-----------------|-------------|----------|------------|
| {scene.shot_breakdown.shot_number} | {scene.shot_breakdown.framing} | {scene.shot_breakdown.camera_angle} | {scene.shot_breakdown.camera_movement} | {scene.shot_breakdown.description[:80]} | {scene.shot_breakdown.duration} | {scene.shot_breakdown.transition} |

**Visual Elements:**
- Characters: {scene.visual_elements.characters if isinstance(scene.visual_elements, VisualElements) else scene.visual_elements.get('characters', [])}
- Environment: {scene.visual_elements.environment if isinstance(scene.visual_elements, VisualElements) else scene.visual_elements.get('environment', '')}
- Lighting: {scene.visual_elements.lighting if isinstance(scene.visual_elements, VisualElements) else scene.visual_elements.get('lighting', '')}
- Mood: {scene.visual_elements.mood if isinstance(scene.visual_elements, VisualElements) else scene.visual_elements.get('mood', '')}

**Video Prompt:**
{scene.video_prompt}

---
"""
        return script
