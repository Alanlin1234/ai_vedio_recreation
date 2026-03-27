"""
分镜到 Shot Breakdown 转换服务
将分镜数据转换为专业的 Shot Breakdown 格式
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _clip(text: str, max_len: int = 500) -> str:
    if not text:
        return ''
    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + '…'


class ShotBreakdownGenerator:
    """分镜到 Shot Breakdown 转换器"""

    def __init__(self):
        self.shot_type_mapping = {
            "主观镜头": "Medium Close-up",
            "近景": "Close-up",
            "中景": "Medium Shot",
            "双人镜头": "Medium Wide",
            "大全景": "Wide Shot",
            "特写": "Extreme Close-up",
            "远景": "Extreme Wide"
        }

    def generate_shot_breakdown(self, scene_data: Dict[str, Any], scene_index: int) -> Dict[str, Any]:
        """
        将分镜数据转换为 Shot Breakdown 格式

        Args:
            scene_data: 分镜数据，包含 shot_type, description, plot, dialogue
            scene_index: 场景索引

        Returns:
            Shot Breakdown 格式的数据
        """
        shot_number = scene_index + 1
        shot_type = scene_data.get('shot_type', '')

        framing = self._map_shot_type(shot_type)
        angle = "Eye Level"
        movement = "Static"

        shot_description = self._build_shot_description(scene_data)
        audio = self._build_audio_info(scene_data)
        duration = float(scene_data.get('duration', 5) or 5)

        return {
            "shot_number": shot_number,
            "framing": framing,
            "angle": angle,
            "movement": movement,
            "shot_description": shot_description,
            "audio": audio,
            "duration": duration
        }

    def format_for_video_generation(
        self,
        shot_breakdown: Dict[str, Any],
        narrative_context: Optional[Dict[str, Any]] = None,
        visual_lock: Optional[str] = None,
    ) -> str:
        """
        将 Shot Breakdown 格式化为视频生成提示词；可注入全片与相邻分镜上下文以保证叙事连贯。
        visual_lock：全片共用的画面风格锁定句，每一镜必须原样附带，保证跨镜一致。
        """
        parts: List[str] = []

        vl = (visual_lock or '').strip()
        if vl:
            parts.append(
                "[VISUAL_LOCK — identical in every shot; copy verbatim; style/character/costume/lighting]\n"
                + vl
            )

        if narrative_context:
            idx = int(narrative_context.get('shot_index', 1))
            total = int(narrative_context.get('total_shots', 1))
            spine = _clip(narrative_context.get('story_summary') or '', 900)
            parts.append(
                f"[Series] One continuous short film. Shot {idx} of {total}. "
                f"Story spine (same narrative throughout all shots): {spine}"
            )
            if idx > 1 and narrative_context.get('previous_plot'):
                parts.append(
                    f"[Previous shot summary] {_clip(narrative_context['previous_plot'], 450)}"
                )
                if narrative_context.get('previous_dialogue'):
                    parts.append(
                        f"[Previous dialogue tone] {_clip(narrative_context['previous_dialogue'], 200)}"
                    )
            else:
                parts.append("[Previous shot] Opening shot; establish world and characters.")

            if narrative_context.get('next_plot') and idx < total:
                parts.append(
                    f"[Next beat (hint only — do not show yet)] {_clip(narrative_context['next_plot'], 280)}"
                )

            parts.append(
                "[Continuity] This clip must follow logically after the previous shot in story time; "
                "keep characters, costumes, and world rules consistent unless the script explicitly jumps. "
                "Advance the plot one step; no random unrelated montage."
            )

        parts.append(
            f"Shot {shot_breakdown['shot_number']}: [Camera] {shot_breakdown['framing']} / "
            f"{shot_breakdown['angle']} / {shot_breakdown['movement']}"
        )
        parts.append(f"[Action] {shot_breakdown['shot_description']}")

        audio = shot_breakdown.get('audio', {})
        if audio.get('narration'):
            parts.append(f"[Dialogue] {audio['narration']}")
        if audio.get('bgm'):
            parts.append(f"[BGM] {audio['bgm']}")
        if audio.get('sfx'):
            parts.append(f"[SFX] {audio['sfx']}")

        parts.append(f"[Duration] {shot_breakdown['duration']}s")

        return "\n".join(parts)

    def _map_shot_type(self, shot_type: str) -> str:
        """
        将中文景别映射为英文专业术语

        Args:
            shot_type: 中文景别

        Returns:
            英文专业术语
        """
        if not shot_type:
            return "Medium Shot"

        for chinese, english in self.shot_type_mapping.items():
            if chinese in shot_type:
                return english

        return "Medium Shot"

    def _build_shot_description(self, scene_data: Dict[str, Any]) -> str:
        """
        构建画面描述

        Args:
            scene_data: 分镜数据

        Returns:
            画面描述
        """
        description = scene_data.get('description', '')
        plot = scene_data.get('plot', '')

        if description and plot:
            return f"{description}。{plot}"
        elif description:
            return description
        elif plot:
            return plot
        else:
            return "场景画面描述"

    def _build_audio_info(self, scene_data: Dict[str, Any]) -> Dict[str, str]:
        """
        构建音频信息

        Args:
            scene_data: 分镜数据

        Returns:
            包含 bgm, sfx, narration 的字典
        """
        dialogue = scene_data.get('dialogue', '')
        plot = scene_data.get('plot', '')

        audio_info = {
            "bgm": "",
            "sfx": "",
            "narration": dialogue
        }

        return audio_info
