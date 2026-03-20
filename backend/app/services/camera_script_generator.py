import json
import logging
from typing import List, Dict, Any, Optional
import dashscope

from .shot_breakdown_models import (
    ShotBreakdown, AudioInfo, VisualElements, TechnicalParams,
    ScenePromptV2, CameraScript, FramingType, CameraAngle, 
    CameraMovement, TransitionType
)

logger = logging.getLogger(__name__)


class CameraScriptGenerator:
    """镜头脚本生成服务 - 生成专业的Shot Breakdown格式"""
    
    def __init__(self, api_key: str = None):
        self.api_keys = [
            "sk-a48e659d43af4009b4dbaa5ae878f473"
        ]
        self.current_key_index = 0
        if api_key:
            dashscope.api_key = api_key
        else:
            dashscope.api_key = self.api_keys[0]
    
    def generate_shot_breakdown(self, 
                               scene_info: Dict[str, Any],
                               video_understanding: str,
                               previous_scene: Dict[str, Any] = None,
                               omni_analysis: Dict[str, Any] = None,
                               vl_analysis: Dict[str, Any] = None) -> ScenePromptV2:
        """生成单个场景的Shot Breakdown"""
        
        prompt = self._build_shot_breakdown_prompt(
            scene_info, video_understanding, previous_scene, omni_analysis, vl_analysis
        )
        
        try:
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are a professional cinematographer and video director. Your expertise includes:
1. Shot composition and framing (Extreme Long Shot to Extreme Close-Up)
2. Camera angles (Eye-level, Low Angle, High Angle, Bird's Eye, etc.)
3. Camera movements (Pan, Tilt, Dolly, Zoom, Tracking, Crane, etc.)
4. Professional film terminology and techniques
5. Visual storytelling and narrative pacing

Generate professional Shot Breakdown in JSON format following the schema exactly.

IMPORTANT: All descriptions and prompts MUST be in Chinese (中文). Use Chinese for:
- Scene descriptions
- Character actions
- Visual elements
- Video prompts
- All narrative content

Only technical terms (like shot types, camera angles) can be in English."""
                    },
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=2000
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                return self._parse_shot_breakdown_response(result_text, scene_info)
            else:
                logger.warning(f"Shot Breakdown生成失败: {response.status_code}")
                return self._create_default_shot_breakdown(scene_info)
                
        except Exception as e:
            logger.error(f"Shot Breakdown生成异常: {e}")
            return self._create_default_shot_breakdown(scene_info)
    
    def _build_shot_breakdown_prompt(self, 
                                    scene_info: Dict[str, Any],
                                    video_understanding: str,
                                    previous_scene: Dict[str, Any],
                                    omni_analysis: Dict[str, Any],
                                    vl_analysis: Dict[str, Any]) -> str:
        """构建Shot Breakdown生成提示词"""
        
        previous_context = ""
        if previous_scene:
            previous_context = f"""
[Previous Scene Reference]
- Previous Framing: {previous_scene.get('shot_breakdown', {}).get('framing', 'N/A')}
- Previous Camera Angle: {previous_scene.get('shot_breakdown', {}).get('camera_angle', 'N/A')}
- Previous Camera Movement: {previous_scene.get('shot_breakdown', {}).get('camera_movement', 'N/A')}
- Previous Visual Focus: {previous_scene.get('shot_breakdown', {}).get('visual_focus', 'N/A')}
- Previous Dialogue: {previous_scene.get('shot_breakdown', {}).get('audio', {}).get('dialogue', 'N/A')}
- Previous Key Action: {previous_scene.get('shot_breakdown', {}).get('key_action', 'N/A')}
- Transition from previous: Must maintain visual continuity

⚠️ STORY CONTINUITY CHECK:
- If previous scene ended with "到家了", "结束了", "下次再玩", "再见", current scene should NOT show "出发", "开始", "上路"
- If previous scene showed characters arriving/leaving, current scene must logically follow
- Maintain the story timeline - don't reset or restart the narrative
"""
        
        story_state_context = ""
        story_state = scene_info.get('story_state', {})
        if story_state:
            prohibited = story_state.get('prohibited_actions', [])
            prohibited_str = ', '.join(prohibited) if prohibited else '出发, 开始, 上路'
            required = story_state.get('required_transitions', [])
            required_str = ', '.join(required) if required else '无特定要求'
            story_state_context = f"""
[Story State Tracking]
- Current Location: {story_state.get('location', 'Unknown')}
- Current Action: {story_state.get('action', 'Unknown')}
- Time of Day: {story_state.get('time_of_day', 'Unknown')}
- Character States: {story_state.get('character_states', {})}
- Story Phase: {story_state.get('story_phase', 'development')}
- Is Ending Scene: {story_state.get('is_ending_scene', False)}
- Prohibited Actions (MUST AVOID): {prohibited_str}
- Required Transitions: {required_str}
- Logical Next: {story_state.get('logical_next', 'Continue the story')}

⚠️ CRITICAL STORY CONTINUITY RULES:

1. FORBIDDEN Combinations:
   If previous scene ended with: "到家了", "到了", "结束", "下次再玩", "再见", "拜拜"
   Then current scene CANNOT start with: "出发", "开始", "上路", "启程", "再出发"
   
   If previous scene ended with: "睡觉了", "休息了", "晚安"
   Then current scene CANNOT start with: "继续工作", "继续活动", "出发", "开始"

2. Time Progression:
   - Time can progress: 上午→下午→傍晚→夜晚
   - Time CANNOT regress: 傍晚→上午 (without transition)
   - Same scene maintains consistent lighting/time

3. Location Rules:
   - Location changes require transition actions (walking, driving)
   - NO teleportation without transition
   - After "到家了", next scene should be indoor or farewell related

4. Character State Continuity:
   - Clothes, items, emotions must be consistent
   - State changes require logical transition
   - If character was sitting, next scene cannot show jumping without transition

5. Dialogue Logic:
   - Responses must match previous dialogue
   - "谢谢" should be followed by "不客气"
   - "再见" cannot be followed by "你好"

6. Physical Realism:
   - NO floating, flying, or anti-gravity actions (unless in vehicle/supernatural context)
   - Human actions must be anatomically possible
   - Objects must have proper support
"""
        
        omni_context = ""
        if omni_analysis:
            omni_context = f"""
[Content Analysis (qwen-omni)]
{json.dumps(omni_analysis, ensure_ascii=False, indent=2)[:500]}
"""
        
        vl_context = ""
        if vl_analysis:
            vl_context = f"""
[Visual Analysis (qwen3-vl)]
{json.dumps(vl_analysis, ensure_ascii=False, indent=2)[:500]}
"""
        
        return f"""
Generate a professional Shot Breakdown for this video scene.

[Scene Info]
- Scene ID: {scene_info.get('scene_id', 1)}
- Duration: {scene_info.get('duration', 5.0)}s
- Description: {scene_info.get('description', '')}
- Narrative Role: {scene_info.get('narrative_role', 'development')}
- Merge Type: {scene_info.get('merge_type', 'original')}

[Video Understanding]
{video_understanding[:1500]}

{previous_context}
{story_state_context}
{omni_context}
{vl_context}

[Output Schema - JSON]
Generate a JSON object with this exact structure:

{{
  "shot_breakdown": {{
    "shot_number": 1,
    "framing": "Medium Shot | Long Shot | Close-Up | etc.",
    "camera_angle": "Eye-level | Low Angle | High Angle | etc.",
    "camera_movement": {{
      "type": "Static | Dolly In | Pan Right | Tracking | Handheld | Crane | etc.",
      "speed": "slow (0.3m/s) | medium (0.6m/s) | fast (1.2m/s)",
      "rhythm": "steady | accelerating | decelerating | smooth | jerky",
      "duration": "e.g., 2s dolly in, then 3s hold"
    }},
    "description": "Detailed visual description of the shot",
    "audio": {{
      "dialogue": "What characters say",
      "background_music": "Music style/mood",
      "sound_effects": ["effect1", "effect2"],
      "voice_tone": "emotional tone"
    }},
    "duration": "{scene_info.get('duration', 5.0)}s",
    "transition": "Cut | Cross Dissolve | Fade | etc.",
    "key_action": "Main action in this shot",
    "visual_focus": "What the viewer should focus on"
  }},
  "visual_elements": {{
    "characters": [
      {{
        "name": "Character name",
        "appearance": "detailed physical description (height, build, hair, clothing, distinctive features)",
        "action": {{
          "main_action": "primary movement or activity",
          "secondary_action": "secondary movements (gestures, expressions)",
          "body_language": "posture, stance, body orientation",
          "facial_expression": "emotional expression on face",
          "movement_speed": "stationary | slow | normal | fast",
          "interaction_with_props": "how they interact with objects"
        }},
        "position_in_frame": "center-left | center | center-right | foreground | background"
      }}
    ],
    "environment": "Setting description",
    "lighting": "Lighting setup (key light direction, intensity, mood)",
    "color_palette": ["#color1", "#color2"],
    "mood": "Emotional atmosphere",
    "props": ["prop1", "prop2"]
  }},
  "video_prompt": "A single, dense Chinese prompt for video generation model (150-250 words), combining all visual elements, camera work, action, and DIALOGUE CONTENT. 必须使用中文描述，包含详细的视觉元素、镜头运动（含速度和节奏）、人物动作（含表情和肢体语言）、动作描述，以及人物对话内容（如果有对话的话）。格式：[视觉描述] + [镜头运动（速度+节奏）] + [人物动作（表情+肢体语言）] + [对话内容：xxx]"
}}

[Guidelines]
1. Framing: Choose appropriate shot size based on narrative importance
   - Extreme Long Shot: Establishing location
   - Long Shot: Full body + environment
   - Medium Shot: Waist up, dialogue scenes
   - Close-Up: Emotional moments, details
   
2. Camera Movement: Match the scene's energy
   - Static: Calm, dialogue
   - Dolly In/Out: Reveal or emphasize
   - Tracking: Following action
   - Handheld: Dynamic, energetic
   
3. Transition: Consider narrative flow
   - Cut: Quick, energetic
   - Cross Dissolve: Time passage, dreamy
   - Match Cut: Visual continuity

4. Maintain continuity with previous scene's framing and angle

5. CRITICAL - Physical Realism Constraints:
   - All characters and objects MUST obey physics and gravity
   - NO flying characters unless explicitly in a flying vehicle or supernatural context
   - NO floating objects without proper support
   - Characters must walk, run, or move naturally on ground
   - Vehicles must stay on roads/surfaces unless jumping (with proper physics)
   - Objects fall down, not up (unless thrown)
   - Human actions must be anatomically possible
   - If a character is near a car, they should be standing, sitting, or walking normally

6. Style Consistency Requirements:
   - Maintain consistent visual style across all scenes
   - Keep similar color grading and lighting style
   - Preserve character appearances from scene to scene
   - Match the overall aesthetic of the original video
   - Avoid dramatic style shifts between consecutive scenes

7. Video Prompt Generation Rules:
   - Include explicit physical constraints in the prompt
   - Add "realistic physics", "natural movement", "grounded in reality"
   - Specify character positions relative to objects (e.g., "standing beside the car", not "floating near car")
   - Include style consistency markers like "maintaining consistent visual style"
   - Keep prompts grounded and realistic unless fantasy/supernatural is intended

Output ONLY the JSON, no explanations.
"""
    
    def _parse_shot_breakdown_response(self, response_text: str, scene_info: Dict[str, Any]) -> ScenePromptV2:
        """解析Shot Breakdown响应"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end+1]
                data = json.loads(json_str)
                
                shot_data = data.get('shot_breakdown', {})
                audio_data = shot_data.get('audio', {})
                visual_data = data.get('visual_elements', {})
                
                audio_info = AudioInfo(
                    dialogue=audio_data.get('dialogue', ''),
                    background_music=audio_data.get('background_music', ''),
                    sound_effects=audio_data.get('sound_effects', []),
                    voice_tone=audio_data.get('voice_tone', '')
                )
                
                # 处理characters数据，支持新的action结构
                characters_data = visual_data.get('characters', [])
                processed_characters = []
                for char in characters_data:
                    if isinstance(char, dict):
                        # 如果action是字典，保持结构；如果是字符串，转换为简单格式
                        action_data = char.get('action', {})
                        if isinstance(action_data, dict):
                            # 新格式：action是字典
                            processed_characters.append(char)
                        else:
                            # 旧格式：action是字符串，转换为字典格式
                            char['action'] = {
                                'main_action': action_data if isinstance(action_data, str) else '',
                                'secondary_action': '',
                                'body_language': '',
                                'facial_expression': '',
                                'movement_speed': 'normal',
                                'interaction_with_props': ''
                            }
                            processed_characters.append(char)
                    else:
                        processed_characters.append(char)
                
                visual_elements = VisualElements(
                    characters=processed_characters,
                    environment=visual_data.get('environment', ''),
                    lighting=visual_data.get('lighting', ''),
                    color_palette=visual_data.get('color_palette', []),
                    mood=visual_data.get('mood', ''),
                    props=visual_data.get('props', [])
                )
                
                # 处理camera_movement数据，支持新的结构
                camera_movement_data = shot_data.get('camera_movement', 'Static')
                if isinstance(camera_movement_data, dict):
                    # 新格式：camera_movement是字典
                    camera_movement_str = f"{camera_movement_data.get('type', 'Static')}"
                    speed = camera_movement_data.get('speed', '')
                    rhythm = camera_movement_data.get('rhythm', '')
                    movement_duration = camera_movement_data.get('duration', '')
                    
                    if speed or rhythm or movement_duration:
                        camera_movement_str += f" ({speed}, {rhythm}, {movement_duration})"
                else:
                    # 旧格式：camera_movement是字符串
                    camera_movement_str = camera_movement_data
                
                shot_breakdown = ShotBreakdown(
                    shot_number=shot_data.get('shot_number', scene_info.get('scene_id', 1)),
                    framing=shot_data.get('framing', 'Medium Shot'),
                    camera_angle=shot_data.get('camera_angle', 'Eye-level'),
                    camera_movement=camera_movement_str,
                    description=shot_data.get('description', ''),
                    audio=audio_info,
                    duration=shot_data.get('duration', f"{scene_info.get('duration', 5.0)}s"),
                    transition=shot_data.get('transition', 'Cut'),
                    key_action=shot_data.get('key_action', ''),
                    visual_focus=shot_data.get('visual_focus', '')
                )
                
                technical_params = TechnicalParams(
                    aspect_ratio="16:9",
                    fps=24,
                    resolution="1920x1080"
                )
                
                video_prompt = self._validate_and_fix_prompt(
                    data.get('video_prompt', ''), 
                    visual_data, 
                    scene_info
                )
                
                # 如果有对话内容，确保添加到video_prompt中
                dialogue = audio_info.dialogue if audio_info and audio_info.dialogue else None
                if dialogue and dialogue not in video_prompt:
                    # 在video_prompt末尾添加对话内容
                    video_prompt = video_prompt.rstrip('。') + f"，对话内容：{dialogue}"
                
                return ScenePromptV2(
                    scene_id=scene_info.get('scene_id', 1),
                    shot_breakdown=shot_breakdown,
                    visual_elements=visual_elements,
                    technical_params=technical_params,
                    video_prompt=video_prompt,
                    narrative_context=scene_info.get('narrative_role', ''),
                    previous_scene_reference=''
                )
        except Exception as e:
            logger.error(f"解析Shot Breakdown响应失败: {e}")
        
        return self._create_default_shot_breakdown(scene_info)
    
    def _validate_and_fix_prompt(self, video_prompt: str, visual_data: Dict[str, Any], 
                                 scene_info: Dict[str, Any]) -> str:
        """
        验证并修复视频提示词，确保物理真实性和风格一致性
        
        Args:
            video_prompt: 原始视频提示词
            visual_data: 视觉元素数据
            scene_info: 场景信息
            
        Returns:
            修复后的视频提示词
        """
        if not video_prompt:
            return video_prompt
        
        prompt_lower = video_prompt.lower()
        fixes = []
        
        # 检测并修复物理不真实的内容
        unrealistic_patterns = [
            ('flying', 'standing or walking naturally'),
            ('floating', 'positioned naturally on the ground'),
            ('hovering', 'standing firmly'),
            ('levitating', 'on the ground'),
            ('defying gravity', 'with realistic physics'),
        ]
        
        for pattern, replacement in unrealistic_patterns:
            if pattern in prompt_lower:
                # 检查是否是合理的飞行场景（飞机、鸟类等）
                if not any(allow_word in prompt_lower for allow_word in 
                          ['airplane', 'helicopter', 'drone', 'bird', 'superhero', 'magic', 'flying vehicle']):
                    fixes.append(f"Note: Changed '{pattern}' to '{replacement}' for physical realism")
        
        # 检测人物位置描述
        if 'car' in prompt_lower or 'vehicle' in prompt_lower:
            if any(word in prompt_lower for word in ['beside', 'next to', 'near']):
                # 确保人物是站立或坐着，而不是飞
                if 'standing' not in prompt_lower and 'sitting' not in prompt_lower and 'walking' not in prompt_lower:
                    fixes.append("Added 'standing naturally' for character position near vehicle")
        
        # 构建增强的提示词
        enhanced_prompt = video_prompt
        
        # 添加物理约束前缀（中文）
        physics_prefix = "具有真实物理效果的视频，"
        if not prompt_lower.startswith('realistic') and not prompt_lower.startswith('natural') and not prompt_lower.startswith('具有'):
            enhanced_prompt = physics_prefix + enhanced_prompt
        
        # 添加风格一致性后缀（中文）
        style_suffix = "，保持一致的视觉风格和真实的物理效果"
        if 'consistent' not in prompt_lower and 'realistic physics' not in prompt_lower and '一致' not in prompt_lower:
            enhanced_prompt = enhanced_prompt.rstrip('。') + style_suffix
        
        # 添加人物动作约束（中文）
        characters = visual_data.get('characters', [])
        if characters:
            # 提取人物动作详细信息
            action_details = []
            for char in characters:
                if isinstance(char, dict):
                    action_data = char.get('action', {})
                    if isinstance(action_data, dict):
                        # 新格式：action是字典
                        main_action = action_data.get('main_action', '')
                        facial_expr = action_data.get('facial_expression', '')
                        body_lang = action_data.get('body_language', '')
                        movement_speed = action_data.get('movement_speed', 'normal')
                        
                        if main_action:
                            action_details.append(main_action)
                        if facial_expr:
                            action_details.append(f"表情{facial_expr}")
                        if body_lang:
                            action_details.append(f"肢体语言{body_lang}")
                        if movement_speed and movement_speed != 'normal':
                            action_details.append(f"动作速度{movement_speed}")
            
            if action_details:
                character_constraint = f"，人物{'，'.join(action_details)}"
                if '自然' not in prompt_lower and 'realistic' not in prompt_lower:
                    enhanced_prompt = enhanced_prompt.rstrip('。') + character_constraint
            else:
                character_constraint = "，人物动作自然流畅，符合人体力学"
                if 'natural' not in prompt_lower and 'realistic' not in prompt_lower and '自然' not in prompt_lower:
                    enhanced_prompt = enhanced_prompt.rstrip('。') + character_constraint
        
        # 记录修复日志
        if fixes:
            logger.info(f"Prompt validation fixes for scene {scene_info.get('scene_id', 1)}:")
            for fix in fixes:
                logger.info(f"  - {fix}")
        
        return enhanced_prompt
    
    def _create_default_shot_breakdown(self, scene_info: Dict[str, Any]) -> ScenePromptV2:
        """创建默认的Shot Breakdown"""
        audio_info = AudioInfo()
        visual_elements = VisualElements()
        
        shot_breakdown = ShotBreakdown(
            shot_number=scene_info.get('scene_id', 1),
            framing="Medium Shot",
            camera_angle="Eye-level",
            camera_movement="Static",
            description=scene_info.get('description', ''),
            audio=audio_info,
            duration=f"{scene_info.get('duration', 5.0)}s",
            transition="Cut",
            key_action="",
            visual_focus=""
        )
        
        technical_params = TechnicalParams()
        
        return ScenePromptV2(
            scene_id=scene_info.get('scene_id', 1),
            shot_breakdown=shot_breakdown,
            visual_elements=visual_elements,
            technical_params=technical_params,
            video_prompt=scene_info.get('description', ''),
            narrative_context=scene_info.get('narrative_role', ''),
            previous_scene_reference=''
        )
    
    def generate_camera_script(self, 
                               scenes: List[Dict[str, Any]],
                               video_understanding: str,
                               omni_analyses: List[Dict[str, Any]] = None,
                               vl_analyses: List[Dict[str, Any]] = None) -> CameraScript:
        """生成完整的镜头脚本"""
        
        scene_prompts = []
        previous_scene = None
        
        for i, scene_info in enumerate(scenes):
            omni_analysis = omni_analyses[i] if omni_analyses and i < len(omni_analyses) else None
            vl_analysis = vl_analyses[i] if vl_analyses and i < len(vl_analyses) else None
            
            scene_prompt = self.generate_shot_breakdown(
                scene_info=scene_info,
                video_understanding=video_understanding,
                previous_scene=previous_scene,
                omni_analysis=omni_analysis,
                vl_analysis=vl_analysis
            )
            
            if previous_scene:
                scene_prompt.previous_scene_reference = f"Scene {previous_scene.get('scene_id', i)}"
            
            scene_prompts.append(scene_prompt)
            previous_scene = scene_prompt.to_dict()
        
        total_duration = sum(s.get('duration', 5.0) for s in scenes)
        
        return CameraScript(
            scenes=scene_prompts,
            total_duration=total_duration,
            overall_style="Cinematic",
            narrative_arc="Development"
        )
    
    def plan_framing_variety(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """规划景别变化，确保视觉多样性"""
        framing_sequence = []
        total_scenes = len(scenes)
        
        if total_scenes == 0:
            return framing_sequence
        
        framing_sequence.append("Long Shot")
        
        for i in range(1, total_scenes - 1):
            progress = i / (total_scenes - 1) if total_scenes > 1 else 0
            
            if progress < 0.3:
                framing_sequence.append("Medium Shot")
            elif progress < 0.6:
                framing_sequence.append("Medium Close-Up")
            else:
                framing_sequence.append("Close-Up")
        
        if total_scenes > 1:
            framing_sequence.append("Medium Shot")
        
        return framing_sequence
    
    def suggest_transitions(self, scenes: List[Dict[str, Any]]) -> List[str]:
        """建议转场类型"""
        transitions = []
        
        for i, scene in enumerate(scenes):
            narrative_role = scene.get('narrative_role', 'development')
            
            if i == 0:
                transitions.append("Fade In")
            elif i == len(scenes) - 1:
                transitions.append("Fade Out")
            elif narrative_role == 'transition':
                transitions.append("Cross Dissolve")
            elif narrative_role == 'climax':
                transitions.append("Cut")
            else:
                transitions.append("Cut")
        
        return transitions
    
    def optimize_shot_breakdown(self, scene_prompt: ScenePromptV2, 
                                creative_direction: str = "",
                                recreation_mode: str = "style") -> ScenePromptV2:
        """
        使用qwen-plus对Shot Breakdown进行二创优化
        
        Args:
            scene_prompt: 原始场景提示词
            creative_direction: 二创方向指导
            recreation_mode: 二创模式
                - "style": 风格优化模式 - 保持故事不变，优化视觉风格
                - "story": 故事改编模式 - 允许改编故事情节
        
        Returns:
            优化后的场景提示词
        """
        try:
            prompt = self._build_optimization_prompt(scene_prompt, creative_direction, recreation_mode)
            
            system_content = self._get_system_content(recreation_mode)
            
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system", 
                        "content": system_content
                    },
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.8 if recreation_mode == "story" else 0.6,
                max_tokens=2000
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                return self._parse_optimized_response(result_text, scene_prompt)
            else:
                logger.warning(f"二创优化失败: {response.status_code}")
                return scene_prompt
                
        except Exception as e:
            logger.error(f"二创优化异常: {e}")
            return scene_prompt
    
    def _get_system_content(self, recreation_mode: str) -> str:
        """根据二创模式获取系统提示词"""
        if recreation_mode == "story":
            return """You are a professional video creative director specializing in video recreation and story adaptation. Your expertise includes:

1. Creative reinterpretation and adaptation of existing video content
2. Reimagining story elements while maintaining the core theme
3. Creating new narrative perspectives and plot twists
4. Developing alternative storylines that offer fresh experiences
5. Maintaining character consistency while exploring new scenarios

Your task is to ADAPT the Shot Breakdown for video recreation (视频二创), creating a NEW story interpretation while keeping the essential theme and characters. You are encouraged to:
- Add new plot elements or twists
- Change the narrative perspective
- Introduce new scenarios or settings
- Modify the emotional journey
- Create surprising or engaging story developments

Make the video a CREATIVE REINTERPRETATION, not just a style copy."""
        else:
            return """You are a professional video creative director specializing in visual style enhancement. Your expertise includes:

1. Enhancing visual aesthetics while preserving the original story
2. Optimizing shot composition and camera work
3. Improving lighting, color, and mood
4. Adding cinematic techniques and visual polish
5. Maintaining complete narrative consistency

Your task is to ENHANCE the Shot Breakdown for video recreation (视频二创), improving the VISUAL QUALITY while keeping the EXACT SAME story. You should:
- Keep all plot points and story elements unchanged
- Only enhance visual descriptions and camera work
- Improve lighting and color descriptions
- Add cinematic polish and professional terminology
- Maintain the same emotional beats and narrative flow

The story must remain IDENTICAL, only the visual presentation should be enhanced."""
    
    def _build_optimization_prompt(self, scene_prompt: ScenePromptV2, 
                                   creative_direction: str,
                                   recreation_mode: str = "style") -> str:
        """构建二创优化提示词"""
        
        shot_breakdown = scene_prompt.shot_breakdown
        visual_elements = scene_prompt.visual_elements
        
        if recreation_mode == "story":
            mode_instruction = """
[RECREATION MODE: STORY ADAPTATION]
You are creating a CREATIVE REINTERPRETATION of this scene. You may:
- Modify or add plot elements
- Change the scenario or setting
- Introduce new actions or reactions
- Create alternative narrative outcomes
- Add creative twists or surprises

The new version should be recognizably related to the original but offer a FRESH story experience.
"""
        else:
            mode_instruction = """
[RECREATION MODE: STYLE ENHANCEMENT]
You are ENHANCING the visual style of this scene. You must:
- Keep the EXACT SAME story and plot
- Only improve visual descriptions
- Enhance camera work and composition
- Polish lighting and color descriptions
- Add cinematic terminology

The story content must remain IDENTICAL to the original.
"""
        
        return f"""
You are optimizing a Shot Breakdown for video recreation (视频二创).
{mode_instruction}
[Original Shot Breakdown]
Shot Number: {shot_breakdown.shot_number}
Framing: {shot_breakdown.framing}
Camera Angle: {shot_breakdown.camera_angle}
Camera Movement: {shot_breakdown.camera_movement}
Description: {shot_breakdown.description}
Duration: {shot_breakdown.duration}
Transition: {shot_breakdown.transition}
Key Action: {shot_breakdown.key_action}

[Visual Elements]
Characters: {visual_elements.characters}
Environment: {visual_elements.environment}
Lighting: {visual_elements.lighting}
Color Palette: {visual_elements.color_palette}
Mood: {visual_elements.mood}
Props: {visual_elements.props}

[Current Video Prompt]
{scene_prompt.video_prompt}

[Creative Direction]
{creative_direction if creative_direction else "Enhance the visual storytelling and make it more engaging."}

[Output Schema - JSON]
Return the {"recreation_mode": "style" if recreation_mode == "style" else "adapted"} Shot Breakdown in this exact format:

{{
  "shot_breakdown": {{
    "shot_number": {shot_breakdown.shot_number},
    "framing": "Enhanced framing choice",
    "camera_angle": "Enhanced camera angle",
    "camera_movement": "Enhanced camera movement",
    "description": "Enhanced description",
    "duration": "{shot_breakdown.duration}",
    "transition": "Enhanced transition type",
    "key_action": "Enhanced key action",
    "visual_focus": "What should the viewer focus on"
  }},
  "visual_elements": {{
    "characters": [...],
    "environment": "Enhanced environment description",
    "lighting": "Enhanced lighting setup",
    "color_palette": ["#color1", "#color2"],
    "mood": "Enhanced emotional atmosphere",
    "props": [...]
  }},
  "video_prompt": "Enhanced English video prompt (150-250 words)",
  "creative_changes": [
    "List of enhancements made",
    "Why these changes improve the video"
  ]
}}

Output ONLY the JSON, no explanations.
"""
    
    def _parse_optimized_response(self, response_text: str, 
                                  original_prompt: ScenePromptV2) -> ScenePromptV2:
        """解析优化后的响应"""
        try:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end+1]
                data = json.loads(json_str)
                
                shot_data = data.get('shot_breakdown', {})
                audio_data = shot_data.get('audio', {})
                visual_data = data.get('visual_elements', {})
                
                audio_info = AudioInfo(
                    dialogue=audio_data.get('dialogue', original_prompt.shot_breakdown.audio.dialogue),
                    background_music=audio_data.get('background_music', original_prompt.shot_breakdown.audio.background_music),
                    sound_effects=audio_data.get('sound_effects', original_prompt.shot_breakdown.audio.sound_effects),
                    voice_tone=audio_data.get('voice_tone', original_prompt.shot_breakdown.audio.voice_tone)
                )
                
                visual_elements = VisualElements(
                    characters=visual_data.get('characters', original_prompt.visual_elements.characters),
                    environment=visual_data.get('environment', original_prompt.visual_elements.environment),
                    lighting=visual_data.get('lighting', original_prompt.visual_elements.lighting),
                    color_palette=visual_data.get('color_palette', original_prompt.visual_elements.color_palette),
                    mood=visual_data.get('mood', original_prompt.visual_elements.mood),
                    props=visual_data.get('props', original_prompt.visual_elements.props)
                )
                
                shot_breakdown = ShotBreakdown(
                    shot_number=shot_data.get('shot_number', original_prompt.shot_breakdown.shot_number),
                    framing=shot_data.get('framing', original_prompt.shot_breakdown.framing),
                    camera_angle=shot_data.get('camera_angle', original_prompt.shot_breakdown.camera_angle),
                    camera_movement=shot_data.get('camera_movement', original_prompt.shot_breakdown.camera_movement),
                    description=shot_data.get('description', original_prompt.shot_breakdown.description),
                    audio=audio_info,
                    duration=shot_data.get('duration', original_prompt.shot_breakdown.duration),
                    transition=shot_data.get('transition', original_prompt.shot_breakdown.transition),
                    key_action=shot_data.get('key_action', original_prompt.shot_breakdown.key_action),
                    visual_focus=shot_data.get('visual_focus', original_prompt.shot_breakdown.visual_focus)
                )
                
                return ScenePromptV2(
                    scene_id=original_prompt.scene_id,
                    shot_breakdown=shot_breakdown,
                    visual_elements=visual_elements,
                    technical_params=original_prompt.technical_params,
                    video_prompt=data.get('video_prompt', original_prompt.video_prompt),
                    narrative_context=original_prompt.narrative_context,
                    previous_scene_reference=original_prompt.previous_scene_reference
                )
        except Exception as e:
            logger.error(f"解析优化响应失败: {e}")
        
        return original_prompt
    
    def generate_storyboard_with_high_consistency(
        self, 
        story_content: str, 
        scene_count: int = 6
    ) -> Dict[str, Any]:
        try:
            scenes = []
            
            for i in range(scene_count):
                scene_prompt = f"""请基于以下故事内容，生成第{i+1}/{scene_count}个分镜场景：

故事内容：
{story_content}

要求：
1. 每个场景要有清晰的描述
2. 保持场景之间的视觉一致性
3. 人物形象、环境风格要统一
4. 每个场景生成一个详细的提示词

请用JSON格式返回，包含：
- "description": 场景描述
- "prompt": 视频生成提示词
- "scene_number": 场景序号
"""
                
                response = dashscope.Generation.call(
                    model="qwen-plus-latest",
                    messages=[
                        {
                            "role": "system",
                            "content": "你是一个专业的分镜设计师，擅长创作一致性极高的分镜图。请确保所有场景的人物形象、环境风格、色彩搭配保持高度一致。"
                        },
                        {"role": "user", "content": scene_prompt}
                    ],
                    result_format='message',
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if response.status_code == 200 and response.output and response.output.choices:
                    result_text = response.output.choices[0].message.content
                    
                    try:
                        json_start = result_text.find('{')
                        json_end = result_text.rfind('}')
                        if json_start != -1 and json_end != -1:
                            json_str = result_text[json_start:json_end+1]
                            scene_data = json.loads(json_str)
                            scenes.append({
                                'scene_number': i + 1,
                                'description': scene_data.get('description', f'场景{i+1}'),
                                'prompt': scene_data.get('prompt', story_content[:200])
                            })
                        else:
                            scenes.append({
                                'scene_number': i + 1,
                                'description': f'场景{i+1}',
                                'prompt': story_content[:200]
                            })
                    except:
                        scenes.append({
                            'scene_number': i + 1,
                            'description': f'场景{i+1}',
                            'prompt': story_content[:200]
                        })
                else:
                    scenes.append({
                        'scene_number': i + 1,
                        'description': f'场景{i+1}',
                        'prompt': story_content[:200]
                    })
            
            return {
                'success': True,
                'scenes': scenes,
                'total_scenes': len(scenes)
            }
        except Exception as e:
            logger.error(f"生成分镜图失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'scenes': []
            }
