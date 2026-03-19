"""
无TTS视频生成测试流程
简化流程：输入视频 → 视频脚本 → 细化分镜 → 视频片段 → 质检片段 → 融合视频
不包含TTS语音合成功能
"""
import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.services.ffmpeg_service import FFmpegService
from app.services.qwen_vl_service import QwenVLService
from app.services.qwen_video_service import QwenVideoService
from app.services.scene_segmentation_service import SceneSegmentationService
from app.services.json_prompt_parser import JSONPromptParser
from app.services.frame_continuity_service import FrameContinuityService
from app.services.video_quality_assessment_service import VideoQualityAssessmentService
from app.services.video_analysis_agent import VideoAnalysisAgent
from app.services.director_agent import DirectorAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NoTTSVideoPipeline:
    """无TTS的视频生成流程 - 使用Seedance 2.0原生音频生成"""
    
    CHECKPOINT_FILE = "pipeline_checkpoint.json"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.output_dir = self.config.get(
            'output_dir', 
            f"downloads/no_tts_pipeline_{int(time.time())}"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.slice_count = self.config.get('slice_count', 5)
        self.slice_duration = self.config.get('slice_duration', 5)
        self.use_original_keyframes = self.config.get('use_original_keyframes', True)
        self.enable_native_audio = self.config.get('enable_native_audio', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.enable_smart_slice = self.config.get('enable_smart_slice', True)
        self.enable_transitions = self.config.get('enable_transitions', True)
        self.recreation_mode = self.config.get('recreation_mode', 'style')
        
        self._init_services()
        
        self.video_path = None
        self.video_slices = []
        self.video_script = None
        self.scene_prompts = []
        self.generated_videos = []
        self.quality_results = []
        self.final_video_path = None
        self.director_plan = None
        self.camera_script = None
        self.full_script_text = None
        
        self.character_voices = {}
        self.character_audio_registry = {}
        self.original_audio_path = None
        
        self.current_step = 0
        self.step_results = {}
        
    def _init_services(self):
        """初始化所有服务"""
        self.ffmpeg_service = FFmpegService()
        self.qwen_vl_service = QwenVLService()
        self.qwen_video_service = QwenVideoService()
        self.scene_segmentation_service = SceneSegmentationService()
        self.json_parser_service = JSONPromptParser()
        self.frame_continuity_service = FrameContinuityService()
        self.video_quality_service = VideoQualityAssessmentService(
            self.config.get('quality_config', {
                'min_resolution': (1280, 720),
                'min_fps': 24,
                'min_bitrate': 1000000
            })
        )
        self.video_analysis_service = VideoAnalysisAgent()
        
        self.director_agent_service = DirectorAgent(self.config.get('director_config', {
            'min_ratio': 0.5,
            'max_ratio': 2.0
        }))
        
        try:
            from video_consistency_agent.agent.consistency_agent import ConsistencyAgent
            consistency_config_path = self.config.get(
                'consistency_config_path',
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "video_consistency_agent/config/config.yaml")
            )
            self.consistency_agent_service = ConsistencyAgent(consistency_config_path)
        except Exception as e:
            logger.warning(f"ConsistencyAgent初始化失败: {e}")
            self.consistency_agent_service = None
    
    def get_previous_scene(self, current_order: int) -> Dict[str, Any]:
        """
        获取上一个场景的信息（用于一致性检查）
        
        Args:
            current_order: 当前场景的顺序号
            
        Returns:
            上一个场景的信息
        """
        if current_order <= 0 or current_order > len(self.generated_videos):
            return None
        
        previous_video = self.generated_videos[current_order - 1]
        return {
            'video_path': previous_video.get('video_path'),
            'keyframes': previous_video.get('keyframes', []),
            'order': current_order - 1,
            'scene_id': previous_video.get('scene_id'),
            'prompt_data': {
                'original_prompt': previous_video.get('prompt', ''),
                'generation_params': previous_video.get('technical_params', {})
            }
        }
    
    async def regenerate_scene(self, scene_order: int, optimized_prompt: str, 
                               adjusted_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        重新生成指定场景（用于一致性检查失败后的重试）
        
        Args:
            scene_order: 场景顺序号
            optimized_prompt: 优化后的提示词
            adjusted_params: 调整后的参数
            
        Returns:
            重新生成的结果
        """
        self.log("重新生成", f"场景{scene_order + 1}", "使用优化后的提示词")
        
        try:
            if scene_order < 0 or scene_order >= len(self.generated_videos):
                return {'success': False, 'error': '无效的场景顺序号'}
            
            old_video_info = self.generated_videos[scene_order]
            
            reference_keyframes = old_video_info.get('keyframes', [])
            
            previous_scene_last_frame = None
            if scene_order > 0:
                prev_video = self.generated_videos[scene_order - 1]
                prev_keyframes = prev_video.get('keyframes', [])
                if prev_keyframes:
                    previous_scene_last_frame = prev_keyframes[-1]
            
            video_result = self.qwen_video_service.generate_video_from_keyframes(
                reference_keyframes[:3] if reference_keyframes else [],
                {
                    "video_prompt": optimized_prompt,
                    "technical_params": adjusted_params or {
                        "frame_rate": 24,
                        "resolution": "1920x1080",
                        "duration": old_video_info.get('duration', 4)
                    },
                    "enable_native_audio": self.enable_native_audio,
                    "dialogues": old_video_info.get('dialogues', []),
                    "audio_refs": old_video_info.get('audio_refs', [])
                }
            )
            
            if video_result.get('success'):
                video_url = video_result.get('video_url')
                audio_url = video_result.get('audio_url')
                local_video_path = os.path.join(self.output_dir, f"scene_{scene_order + 1:02d}_regenerated.mp4")
                
                download_result = await self.download_media(video_url, local_video_path, "video", "重新生成")
                
                if download_result.get('success'):
                    last_frame_path = os.path.join(self.output_dir, f"scene_{scene_order + 1:02d}_last_frame_regenerated.jpg")
                    last_frame_result = await self.ffmpeg_service.extract_last_frame(local_video_path, last_frame_path)
                    
                    new_keyframes = reference_keyframes
                    if last_frame_result.get('success'):
                        new_keyframes = reference_keyframes + [last_frame_path]
                    
                    regenerated_info = {
                        'scene_id': scene_order + 1,
                        'scene_index': scene_order,
                        'video_path': local_video_path,
                        'audio_path': local_video_path.replace('.mp4', '_audio.mp3') if audio_url else None,
                        'keyframes': new_keyframes,
                        'prompt': optimized_prompt,
                        'dialogues': old_video_info.get('dialogues', []),
                        'duration': old_video_info.get('duration', 4),
                        'native_audio_enabled': self.enable_native_audio,
                        'regenerated': True,
                        'success': True
                    }
                    
                    self.generated_videos[scene_order] = regenerated_info
                    
                    return {
                        'success': True,
                        'scene_id': scene_order + 1,
                        'order': scene_order,
                        'keyframes': new_keyframes,
                        'video_path': local_video_path,
                        'prompt_data': {
                            'original_prompt': optimized_prompt,
                            'generation_params': adjusted_params or {}
                        }
                    }
                else:
                    return {'success': False, 'error': f"视频下载失败: {download_result.get('error')}"}
            else:
                return {'success': False, 'error': f"视频生成失败: {video_result.get('error')}"}
                
        except Exception as e:
            self.log("重新生成", f"场景{scene_order + 1}", f"异常: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def log(self, step: str, status: str, detail: str = ""):
        """记录日志"""
        timestamp = time.strftime('%H:%M:%S')
        message = f"[{timestamp}] [{step}] {status}"
        if detail:
            message += f" | {detail}"
        logger.info(message)
        print(message)
    
    async def download_media(self, url: str, local_path: str, media_type: str = "video", 
                            step_name: str = "下载") -> Dict[str, Any]:
        """
        统一的媒体下载方法
        
        Args:
            url: 媒体文件URL
            local_path: 本地保存路径
            media_type: 媒体类型 ("video" 或 "audio")
            step_name: 步骤名称，用于日志记录
            
        Returns:
            下载结果字典
        """
        try:
            result = await self.ffmpeg_service.download_video(url, local_path)
            
            # ffmpeg_service.download_video返回字符串（路径）或None，需要转换为字典
            if result and isinstance(result, str):
                # 下载成功，返回路径字符串
                self.log(step_name, media_type, f"下载成功: {local_path}")
                return {'success': True, 'path': result}
            elif isinstance(result, dict):
                # 如果已经是字典，直接使用
                if result.get('success'):
                    self.log(step_name, media_type, f"下载成功: {local_path}")
                else:
                    self.log(step_name, media_type, f"下载失败: {result.get('error', '未知错误')}")
                return result
            else:
                # 下载失败
                self.log(step_name, media_type, f"下载失败: 未知错误")
                return {'success': False, 'error': '下载失败'}
            
        except Exception as e:
            self.log(step_name, media_type, f"下载异常: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def step_0_input_video(self, video_path: str) -> Dict[str, Any]:
        """
        步骤0: 输入视频
        验证视频文件，获取基本信息
        """
        self.log("步骤0", "输入视频", f"视频路径: {video_path}")
        
        if not os.path.exists(video_path):
            return {'success': False, 'error': f'视频文件不存在: {video_path}'}
        
        self.video_path = video_path
        
        video_info = await self.ffmpeg_service.get_video_info(video_path)
        if not video_info:
            return {'success': False, 'error': '无法获取视频信息'}
        
        self.log("步骤0", "视频信息", 
                f"分辨率: {video_info.get('resolution')}, "
                f"时长: {video_info.get('duration'):.1f}s, "
                f"帧率: {video_info.get('fps')}fps")
        
        return {
            'success': True,
            'video_path': video_path,
            'video_info': video_info
        }
    
    async def step_1_output_video_script(self) -> Dict[str, Any]:
        """
        步骤1: 输出视频脚本
        分析视频内容，生成视频脚本
        """
        self.log("步骤1", "输出视频脚本", "开始分析视频内容")
        
        try:
            video_understanding = await self.video_analysis_service.understand_video_content_and_scenes(
                video_path=self.video_path,
                fps=5,
                slice_limit=self.slice_count
            )
            
            if not video_understanding.get('success'):
                return {'success': False, 'error': video_understanding.get('error', '视频理解失败')}
            
            self.video_script = video_understanding.get('content', '')
            self.log("步骤1", "脚本生成完成", f"脚本长度: {len(self.video_script)} 字符")
            
            slices = video_understanding.get('raw_slices', video_understanding.get('slices', []))
            self.video_slices = slices[:self.slice_count]
            
            self.log("步骤1", "切片信息", f"切片数量: {len(self.video_slices)}")
            
            for i, slice_info in enumerate(self.video_slices):
                if 'keyframes' in slice_info and slice_info['keyframes']:
                    self.log("步骤1", f"切片{i+1}关键帧", f"数量: {len(slice_info['keyframes'])}")
            
            if self.enable_native_audio:
                await self._extract_character_audio_samples()
            
            return {
                'success': True,
                'video_script': self.video_script,
                'slices': self.video_slices,
                'raw_result': video_understanding,
                'character_audio_registry': self.character_audio_registry
            }
            
        except Exception as e:
            self.log("步骤1", "失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def _extract_character_audio_samples(self) -> Dict[str, Any]:
        """
        从原视频中提取角色音频样本，用于Seedance 2.0的声音一致性
        """
        self.log("步骤1.5", "提取角色音频样本", "用于原生音频生成的声音一致性")
        
        try:
            audio_dir = os.path.join(self.output_dir, "character_audio")
            os.makedirs(audio_dir, exist_ok=True)
            
            if self.video_path:
                self.original_audio_path = os.path.join(audio_dir, "original_audio.mp3")
                extract_result = await self.ffmpeg_service.extract_audio(
                    self.video_path, self.original_audio_path
                )
                
                if extract_result.get('success'):
                    self.log("步骤1.5", "音频提取成功", self.original_audio_path)
                    
                    if self.video_slices:
                        for i, slice_info in enumerate(self.video_slices[:3]):
                            slice_audio_path = os.path.join(audio_dir, f"slice_{i+1}_audio.mp3")
                            start_time = slice_info.get('start_time', i * self.slice_duration)
                            duration = slice_info.get('duration', self.slice_duration)
                            
                            try:
                                slice_audio_result = await self.ffmpeg_service.extract_audio_segment(
                                    self.original_audio_path,
                                    slice_audio_path,
                                    start_time,
                                    duration
                                )
                                
                                if slice_audio_result.get('success'):
                                    self.character_audio_registry[f"character_{i+1}"] = slice_audio_path
                                    self.log("步骤1.5", f"切片{i+1}音频样本", slice_audio_path)
                            except Exception as e:
                                self.log("步骤1.5", f"切片{i+1}音频提取失败", str(e))
                else:
                    self.log("步骤1.5", "音频提取失败", extract_result.get('error', ''))
            
            self.log("步骤1.5", "角色音频注册完成", f"共 {len(self.character_audio_registry)} 个音频样本")
            
            return {
                'success': True,
                'character_audio_registry': self.character_audio_registry,
                'original_audio_path': self.original_audio_path
            }
            
        except Exception as e:
            self.log("步骤1.5", "角色音频提取失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def _extract_global_profile(self) -> Dict[str, Any]:
        """
        阶段1: 并行提取全局人物档案和风格信息
        这个阶段可以并行处理，不影响场景连贯性
        """
        self.log("步骤2.1", "提取全局档案", "开始并行分析所有切片")
        
        try:
            global_profile = {
                'characters': {},
                'style': None,
                'environment': None,
                'color_palette': None,
                'lighting_style': None
            }
            
            if not self.video_slices:
                return global_profile
            
            async def analyze_slice_keyframes(slice_info: Dict, index: int) -> Dict[str, Any]:
                """分析单个切片的关键帧"""
                keyframes = slice_info.get('keyframes', [])
                if not keyframes:
                    return {'index': index, 'data': None}
                
                analysis = {
                    'index': index,
                    'characters': [],
                    'style': None,
                    'environment': None,
                    'dominant_colors': [],
                    'lighting': None
                }
                
                if keyframes and self.qwen_vl_service:
                    try:
                        first_keyframe = keyframes[0] if isinstance(keyframes, list) else keyframes
                        if first_keyframe and os.path.exists(first_keyframe):
                            vl_result = self.qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                                [first_keyframe],
                                {"video_prompt": "分析这张图片的人物特征、视觉风格、环境元素和色彩"}
                            )
                            if vl_result.get('success'):
                                prompt_data = vl_result.get('prompt', '')
                                if isinstance(prompt_data, str):
                                    try:
                                        prompt_json = json.loads(prompt_data)
                                        analysis['characters'] = prompt_json.get('characters', [])
                                        analysis['style'] = prompt_json.get('visual_style', {})
                                        analysis['environment'] = prompt_json.get('environment', '')
                                        analysis['dominant_colors'] = prompt_json.get('color_palette', [])
                                        analysis['lighting'] = prompt_json.get('lighting', '')
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"切片{index+1} JSON解析失败: {str(e)}")
                                        pass
                    except Exception as e:
                        self.log("步骤2.1", f"切片{index+1}分析", f"警告: {str(e)}")
                
                return analysis
            
            tasks = [
                analyze_slice_keyframes(slice_info, i) 
                for i, slice_info in enumerate(self.video_slices)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            character_features = {}
            style_features = []
            environment_features = []
            color_features = []
            lighting_features = []
            
            for result in results:
                if isinstance(result, Exception):
                    continue
                if result:
                    if result.get('characters'):
                        for char in result['characters']:
                            char_key = char.get('name', char.get('id', 'unknown'))
                            if char_key not in character_features:
                                character_features[char_key] = char
                    if result.get('style'):
                        style_features.append(result['style'])
                    if result.get('environment'):
                        environment_features.append(result['environment'])
                    if result.get('dominant_colors'):
                        color_features.extend(result['dominant_colors'])
                    if result.get('lighting'):
                        lighting_features.append(result['lighting'])
            
            global_profile['characters'] = character_features
            if style_features:
                global_profile['style'] = style_features[0]
            if environment_features:
                global_profile['environment'] = environment_features[0]
            if color_features:
                unique_colors = list(set(color_features))[:5]
                global_profile['color_palette'] = unique_colors
            if lighting_features:
                global_profile['lighting_style'] = lighting_features[0]
            
            self.log("步骤2.1", "全局档案提取完成", 
                    f"人物: {len(global_profile['characters'])}个, "
                    f"风格: {global_profile['style'] or '未检测'}, "
                    f"环境: {global_profile['environment'] or '未检测'}")
            
            return global_profile
            
        except Exception as e:
            self.log("步骤2.1", "全局档案提取失败", str(e))
            return {
                'characters': {},
                'style': None,
                'environment': None,
                'color_palette': None,
                'lighting_style': None
            }
    
    def _build_enhanced_prompt_context(self, global_profile: Dict[str, Any], 
                                        scene_index: int, 
                                        previous_scene_info: Dict[str, Any] = None) -> str:
        """
        构建增强的提示词上下文，融合全局档案和场景连贯性信息
        """
        context_parts = []
        
        if global_profile.get('characters'):
            chars_desc = []
            for char_name, char_info in global_profile['characters'].items():
                if isinstance(char_info, dict):
                    desc = char_info.get('description', char_info.get('appearance', ''))
                    if desc:
                        chars_desc.append(f"{char_name}: {desc}")
            if chars_desc:
                context_parts.append(f"【全局人物档案 - 必须保持一致】\n" + "\n".join(chars_desc))
        
        if global_profile.get('style'):
            style = global_profile['style']
            if isinstance(style, dict):
                style_desc = style.get('description', style.get('name', str(style)))
            else:
                style_desc = str(style)
            context_parts.append(f"【全局视觉风格】\n{style_desc}")
        
        if global_profile.get('color_palette'):
            colors = global_profile['color_palette']
            context_parts.append(f"【全局色彩方案】\n{', '.join(colors)}")
        
        if global_profile.get('lighting_style'):
            context_parts.append(f"【全局光照风格】\n{global_profile['lighting_style']}")
        
        if previous_scene_info:
            context_parts.append(f"""
【上一场景连贯性信息 - 首尾帧连接】
上一场景内容: {previous_scene_info.get('video_prompt', '')[:200]}...
上一场景风格: {previous_scene_info.get('style_elements', {}).get('visual_style', '')}
上一场景环境: {previous_scene_info.get('style_elements', {}).get('environment', '')}

⚠️ 关键约束：当前场景的首帧必须与上一场景的尾帧无缝衔接！
""")
        
        return "\n\n".join(context_parts)
    
    def _generate_scene_dialogue(self, scene_index: int, global_profile: Dict[str, Any], 
                                  slice_info: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """
        为场景生成人物对话，用于Seedance 2.0原生音频生成
        
        Returns:
            对话列表，格式: [{"character": "角色名", "dialogue": "对话内容", "voice_ref": "音频参考路径"}]
        """
        dialogues = []
        
        characters = global_profile.get('characters', {})
        if not characters:
            return dialogues
        
        char_list = list(characters.keys())
        if not char_list:
            return dialogues
        
        audio_content = slice_info.get('audio_content', '') if slice_info else ''
        
        if audio_content:
            char_name = char_list[scene_index % len(char_list)]
            voice_ref = self.character_audio_registry.get(char_name, '')
            
            dialogues.append({
                'character': char_name,
                'dialogue': audio_content,
                'voice_ref': voice_ref,
                'emotion': 'neutral',
                'timing': 'normal'
            })
        else:
            char_name = char_list[scene_index % len(char_list)]
            voice_ref = self.character_audio_registry.get(f"character_{scene_index + 1}", '')
            
            dialogues.append({
                'character': char_name,
                'dialogue': '',
                'voice_ref': voice_ref,
                'emotion': 'neutral',
                'timing': 'normal'
            })
        
        return dialogues
    
    def _build_dialogue_prompt_section(self, dialogues: List[Dict[str, str]]) -> str:
        """
        构建对话部分的提示词，用于Seedance 2.0原生音频生成
        """
        if not dialogues:
            return ""
        
        dialogue_parts = ["【人物对话 - 用于原生音频生成】"]
        
        for i, d in enumerate(dialogues):
            char = d.get('character', 'Unknown')
            text = d.get('dialogue', '')
            voice_ref = d.get('voice_ref', '')
            emotion = d.get('emotion', 'neutral')
            
            dialogue_line = f"\n[角色{i+1}: {char}]"
            if text:
                dialogue_line += f"\n对话: \"{text}\""
            if voice_ref:
                dialogue_line += f"\n声音参考: {voice_ref}"
            dialogue_line += f"\n情绪: {emotion}"
            
            dialogue_parts.append(dialogue_line)
        
        dialogue_parts.append("\n⚠️ 音频生成要求：使用Seedance 2.0原生音频生成，保持角色声音一致性")
        
        return "\n".join(dialogue_parts)
    
    def _get_creative_direction(self, scene_index: int, narrative_role: str) -> str:
        """
        根据场景索引和叙事角色获取二创方向指导
        
        Args:
            scene_index: 场景索引
            narrative_role: 叙事角色
        
        Returns:
            二创方向指导文本
        """
        directions = {
            'intro': "Enhance the opening with more dramatic camera work and atmospheric lighting. Consider a slow reveal or establishing shot that draws viewers in.",
            'development': "Add visual interest through dynamic camera movements and creative framing. Enhance the storytelling with subtle visual metaphors.",
            'climax': "Maximize emotional impact with intense camera work, dramatic lighting, and powerful visual composition. Consider close-ups and dynamic movements.",
            'transition': "Create smooth visual flow with creative transition techniques. Use matching elements or visual bridges between scenes.",
            'conclusion': "Provide satisfying closure with composed framing and gentle camera movements. Consider pull-back shots or fade-out compositions."
        }
        
        base_direction = directions.get(narrative_role, "Enhance visual storytelling while maintaining narrative coherence.")
        
        creative_additions = [
            "Consider adding unique visual elements that weren't in the original.",
            "Explore creative camera angles that offer fresh perspectives.",
            "Enhance the mood through lighting and color adjustments.",
            "Add subtle visual details that reward attentive viewers."
        ]
        
        addition = creative_additions[scene_index % len(creative_additions)]
        
        return f"{base_direction} {addition}"
    
    async def step_2_refine_storyboard(self) -> Dict[str, Any]:
        """
        步骤2: 细化分镜（优化版 - 集成导演Agent和多模型分析）
        阶段1: qwen-omni-turbo分析切片内容
        阶段2: qwen3-vl-plus分析关键帧
        阶段3: 导演Agent根据分析结果规划场景（智能调整场景数量）
        阶段4: 并行提取全局档案（不影响连贯性）
        阶段5: 合并分析结果，串行生成提示词（保持首尾帧连贯）
        """
        self.log("步骤2", "细化分镜", "开始生成分镜描述")
        
        try:
            if not self.video_slices:
                self.log("步骤2", "失败", "没有可用的视频切片")
                return {'success': False, 'error': '没有可用的视频切片'}
            
            self.scene_prompts = []
            
            self.log("步骤2.1", "qwen-omni-turbo分析", f"分析{len(self.video_slices)}个切片内容")
            try:
                omni_analysis_results = await self.qwen_vl_service.analyze_video_content(
                    self.video_slices,
                    audio_contents=[]
                )
                
                if omni_analysis_results:
                    for i, result in enumerate(omni_analysis_results):
                        if i < len(self.video_slices):
                            self.video_slices[i]['omni_analysis'] = result
                            self.log("步骤2.1", f"切片{i+1}分析完成")
                    self.log("步骤2.1", "qwen-omni-turbo分析", "完成")
            except Exception as e:
                self.log("步骤2.1", "qwen-omni-turbo分析失败", str(e))
                logger.warning(f"qwen-omni-turbo分析失败: {str(e)}")
            
            self.log("步骤2.2", "qwen3-vl-plus关键帧分析", "开始")
            try:
                for i, slice_info in enumerate(self.video_slices):
                    keyframes = slice_info.get('keyframes', [])
                    if keyframes:
                        try:
                            vl_result = self.qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                                keyframes,
                                {
                                    "video_prompt": f"分析第{i+1}个场景的关键帧，生成详细的视频描述",
                                    "audio_content": slice_info.get('audio_content', '')
                                }
                            )
                            if vl_result.get('success'):
                                self.video_slices[i]['vl_analysis'] = vl_result
                                self.log("步骤2.2", f"切片{i+1}关键帧分析成功")
                            else:
                                self.log("步骤2.2", f"切片{i+1}关键帧分析失败")
                        except Exception as e:
                            self.log("步骤2.2", f"切片{i+1}关键帧分析异常", str(e))
                self.log("步骤2.2", "qwen3-vl-plus关键帧分析", "完成")
            except Exception as e:
                self.log("步骤2.2", "qwen3-vl-plus分析失败", str(e))
                logger.warning(f"qwen3-vl-plus分析失败: {str(e)}")
            
            self.log("步骤2.3", "导演Agent规划场景", "根据分析结果智能规划场景结构")
            director_plan = await self.director_agent_service.plan_scenes(
                video_script=self.video_script,
                original_slices=self.video_slices
            )
            
            if director_plan is None:
                self.log("步骤2.3", "导演规划失败", "返回空结果")
                return {'success': False, 'error': '导演Agent规划失败'}
            
            self.log("步骤2.3", "导演规划完成", 
                    f"原切片: {director_plan.original_slice_count} → "
                    f"新场景: {director_plan.final_scene_count} | "
                    f"调整比例: {director_plan.adjustment_ratio:.2f}")
            
            self.director_plan = director_plan
            
            global_profile = await self._extract_global_profile()
            
            self.log("步骤2.5", "串行生成提示词", "合并分析结果，按导演规划生成场景提示词")
            
            for scene_plan in director_plan.scenes:
                scene_id = scene_plan.scene_id
                self.log("步骤2.5", f"处理场景{scene_id + 1}", 
                        f"来源切片: {scene_plan.source_slices}, 时长: {scene_plan.duration:.1f}s")
                
                source_keyframes = list(scene_plan.source_keyframes)
                if not source_keyframes:
                    for slice_idx in scene_plan.source_slices:
                        if slice_idx < len(self.video_slices):
                            source_keyframes.extend(self.video_slices[slice_idx].get('keyframes', []))
                
                omni_analysis = None
                vl_analysis = None
                for slice_idx in scene_plan.source_slices:
                    if slice_idx < len(self.video_slices):
                        slice_info = self.video_slices[slice_idx]
                        if omni_analysis is None and slice_info.get('omni_analysis'):
                            omni_analysis = slice_info['omni_analysis']
                        if vl_analysis is None and slice_info.get('vl_analysis'):
                            vl_analysis = slice_info['vl_analysis']
                
                scene = {
                    'scene_id': scene_id,
                    'start_time': scene_plan.start_time,
                    'end_time': scene_plan.end_time,
                    'duration': scene_plan.duration,
                    'description': scene_plan.description,
                    'slice_data': scene_plan.slice_data,
                    'complexity': scene_plan.complexity,
                    'narrative_role': scene_plan.narrative_role,
                    'merge_type': scene_plan.merge_type,
                    'omni_analysis': omni_analysis,
                    'vl_analysis': vl_analysis
                }
                
                previous_scene_info = None
                if scene_id > 0 and self.scene_prompts:
                    previous_scene_info = {
                        'video_prompt': self.scene_prompts[-1].get('video_prompt', ''),
                        'style_elements': self.scene_prompts[-1].get('style_elements', {}),
                        'scene_info': self.scene_prompts[-1].get('scene_info', {})
                    }
                
                enhanced_context = self._build_enhanced_prompt_context(
                    global_profile, scene_id, previous_scene_info
                )
                
                if omni_analysis:
                    omni_prompt = omni_analysis.get('video_prompt', '') or omni_analysis.get('prompt', '')
                    if omni_prompt:
                        enhanced_context += f"\n\n【qwen-omni分析结果】\n{omni_prompt[:500]}"
                
                if vl_analysis:
                    vl_prompt = vl_analysis.get('prompt', '')
                    if vl_prompt:
                        enhanced_context += f"\n\n【qwen3-vl分析结果】\n{vl_prompt[:500]}"
                
                if scene_plan.merge_type == "merged":
                    enhanced_context += f"\n\n【场景合并说明】此场景由原切片 {scene_plan.source_slices} 合并而成，需要保持内容的连贯性和过渡的自然性。"
                elif scene_plan.merge_type == "split":
                    enhanced_context += f"\n\n【场景拆分说明】此场景由原切片 {scene_plan.source_slices[0] + 1} 拆分而来，需要突出该片段的独特内容。"
                
                dialogues = []
                if self.enable_native_audio:
                    first_slice_idx = scene_plan.source_slices[0] if scene_plan.source_slices else 0
                    slice_info = self.video_slices[first_slice_idx] if first_slice_idx < len(self.video_slices) else {}
                    dialogues = self._generate_scene_dialogue(scene_id, global_profile, slice_info)
                    dialogue_section = self._build_dialogue_prompt_section(dialogues)
                    enhanced_context += "\n\n" + dialogue_section
                    self.log("步骤2.5", f"场景{scene_id + 1}对话生成", f"角色数: {len(dialogues)}")
                
                prompt_result = self.scene_segmentation_service.generate_shot_breakdown_prompt(
                    scene=scene,
                    video_understanding=self.video_script + "\n\n" + enhanced_context,
                    audio_text='',
                    scene_index=scene_id,
                    previous_scene_info=previous_scene_info,
                    omni_analysis=omni_analysis,
                    vl_analysis=vl_analysis
                )
                
                if prompt_result.get('success'):
                    self.log("步骤2.5.1", f"场景{scene_id + 1}初步Shot Breakdown生成成功")
                    
                    from app.services.shot_breakdown_models import ScenePromptV2, ShotBreakdown, AudioInfo, VisualElements, TechnicalParams
                    
                    shot_data = prompt_result.get('shot_breakdown', {})
                    visual_data = prompt_result.get('visual_elements', {})
                    
                    audio_info = AudioInfo(
                        dialogue=shot_data.get('audio', {}).get('dialogue', ''),
                        background_music=shot_data.get('audio', {}).get('background_music', ''),
                        sound_effects=shot_data.get('audio', {}).get('sound_effects', []),
                        voice_tone=shot_data.get('audio', {}).get('voice_tone', '')
                    )
                    
                    visual_elements = VisualElements(
                        characters=visual_data.get('characters', []),
                        environment=visual_data.get('environment', ''),
                        lighting=visual_data.get('lighting', ''),
                        color_palette=visual_data.get('color_palette', []),
                        mood=visual_data.get('mood', ''),
                        props=visual_data.get('props', [])
                    )
                    
                    shot_breakdown = ShotBreakdown(
                        shot_number=shot_data.get('shot_number', scene_id + 1),
                        framing=shot_data.get('framing', 'Medium Shot'),
                        camera_angle=shot_data.get('camera_angle', 'Eye-level'),
                        camera_movement=shot_data.get('camera_movement', 'Static'),
                        description=shot_data.get('description', ''),
                        audio=audio_info,
                        duration=shot_data.get('duration', f"{scene['duration']}s"),
                        transition=shot_data.get('transition', 'Cut'),
                        key_action=shot_data.get('key_action', ''),
                        visual_focus=shot_data.get('visual_focus', '')
                    )
                    
                    technical_params = TechnicalParams()
                    
                    scene_prompt_v2 = ScenePromptV2(
                        scene_id=scene_id,
                        shot_breakdown=shot_breakdown,
                        visual_elements=visual_elements,
                        technical_params=technical_params,
                        video_prompt=prompt_result.get('video_prompt', ''),
                        narrative_context=scene.get('narrative_role', 'development'),
                        previous_scene_reference=''
                    )
                    
                    creative_direction = self._get_creative_direction(scene_id, scene.get('narrative_role', 'development'))
                    
                    from app.services.camera_script_generator import CameraScriptGenerator
                    camera_generator = CameraScriptGenerator()
                    
                    optimized_prompt = camera_generator.optimize_shot_breakdown(
                        scene_prompt=scene_prompt_v2,
                        creative_direction=creative_direction,
                        recreation_mode=self.recreation_mode
                    )
                    
                    self.log("步骤2.5.2", f"场景{scene_id + 1}二创优化完成", f"模式: {self.recreation_mode}")
                    
                    prompt_result['video_prompt'] = optimized_prompt.video_prompt
                    prompt_result['shot_breakdown'] = optimized_prompt.shot_breakdown.to_dict()
                    prompt_result['visual_elements'] = optimized_prompt.visual_elements.to_dict()
                    prompt_result['creative_enhancements'] = getattr(optimized_prompt, 'creative_enhancements', [])
                    
                    parsed_result = self.json_parser_service.parse_prompt(
                        json.dumps(prompt_result, ensure_ascii=False),
                        prompt_type="txt2img"
                    )
                    
                    if parsed_result.get('success'):
                        self.log("步骤2.5.3", f"场景{scene_id + 1}JSON解析成功")
                        prompt_result['parsed_prompt'] = parsed_result.get('prompt', prompt_result.get('video_prompt', ''))
                
                scene_prompt = {
                    'scene_id': scene_id,
                    'start_time': scene['start_time'],
                    'end_time': scene['end_time'],
                    'duration': scene['duration'],
                    'description': scene['description'],
                    'video_prompt': prompt_result.get('video_prompt', '') if prompt_result.get('success') else '',
                    'shot_breakdown': prompt_result.get('shot_breakdown', {}),
                    'visual_elements': prompt_result.get('visual_elements', {}),
                    'style_elements': prompt_result.get('style_elements', {}),
                    'technical_params': prompt_result.get('technical_params', {}),
                    'shot_breakdown_table': prompt_result.get('shot_breakdown_table', ''),
                    'creative_enhancements': prompt_result.get('creative_enhancements', []),
                    'parsed_prompt': prompt_result.get('parsed_prompt', ''),
                    'keyframes': source_keyframes,
                    'dialogues': dialogues,
                    'audio_refs': [d.get('voice_ref', '') for d in dialogues if d.get('voice_ref')],
                    'global_profile_applied': bool(global_profile.get('characters') or global_profile.get('style')),
                    'source_slices': scene_plan.source_slices,
                    'merge_type': scene_plan.merge_type,
                    'narrative_role': scene_plan.narrative_role,
                    'omni_analysis': omni_analysis,
                    'vl_analysis': vl_analysis,
                    'success': prompt_result.get('success', False)
                }
                
                if prompt_result.get('success'):
                    self.scene_prompts.append(scene_prompt)
                    shot_info = prompt_result.get('shot_breakdown', {})
                    self.log("步骤2.5", f"场景{scene_id + 1}提示词生成成功", 
                            f"景别: {shot_info.get('framing', 'N/A')}, "
                            f"角度: {shot_info.get('camera_angle', 'N/A')}, "
                            f"运动: {shot_info.get('camera_movement', 'N/A')}")
                else:
                    self.log("步骤2.5", f"场景{scene_id + 1}提示词生成失败，跳过此场景", prompt_result.get('error', ''))
            
            camera_script_result = self.scene_segmentation_service.generate_camera_script_for_scenes(
                scenes=[{
                    'scene_id': sp['scene_id'],
                    'start_time': sp['start_time'],
                    'end_time': sp['end_time'],
                    'duration': sp['duration'],
                    'description': sp['description'],
                    'narrative_role': sp.get('narrative_role', 'development'),
                    'merge_type': sp.get('merge_type', 'original')
                } for sp in self.scene_prompts],
                video_understanding=self.video_script,
                omni_analyses=[sp.get('omni_analysis') for sp in self.scene_prompts],
                vl_analyses=[sp.get('vl_analysis') for sp in self.scene_prompts]
            )
            
            self.camera_script = camera_script_result.get('camera_script', {})
            self.full_script_text = camera_script_result.get('full_script_text', '')
            
            self.log("步骤2", "分镜细化完成", 
                    f"共生成 {len(self.scene_prompts)} 个场景 "
                    f"(原切片: {len(self.video_slices)})")
            
            return {
                'success': True,
                'scene_prompts': self.scene_prompts,
                'global_profile': global_profile,
                'director_plan': director_plan.to_dict(),
                'camera_script': self.camera_script,
                'full_script_text': self.full_script_text
            }
            
        except Exception as e:
            self.log("步骤2", "失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def step_3_generate_video_clips(self) -> Dict[str, Any]:
        """
        步骤3: 输出视频片段
        根据分镜描述生成视频片段
        """
        self.log("步骤3", "输出视频片段", "开始生成视频片段")
        
        try:
            previous_scene_last_frame = None
            previous_keyframes = []
            
            for i, scene_prompt in enumerate(self.scene_prompts):
                self.log("步骤3", f"生成片段{i+1}", "开始")
                
                if not isinstance(scene_prompt, dict):
                    self.log("步骤3", f"片段{i+1}", f"跳过，scene_prompt类型错误: {type(scene_prompt)}")
                    continue
                
                video_prompt = scene_prompt.get('video_prompt', '')
                if not video_prompt:
                    self.log("步骤3", f"片段{i+1}", "跳过，提示词为空")
                    continue
                
                reference_keyframes = scene_prompt.get('keyframes', [])
                
                enhanced_prompt = video_prompt
                if i > 0 and previous_scene_last_frame:
                    self.log("步骤3", f"片段{i+1}", "使用上一场景最后一帧作为首帧")
                    enhanced_prompt = self.frame_continuity_service.build_contextual_prompt(
                        current_prompt=video_prompt,
                        previous_scene_info={
                            'prompt_data': {
                                'original_prompt': self.scene_prompts[i-1].get('video_prompt', '') if i > 0 and self.scene_prompts else '',
                                'generation_params': {
                                    'frame_rate': 24,
                                    'resolution': '1920x1080',
                                    'duration': scene_prompt.get('duration', 4)
                                }
                            },
                            'last_frame': previous_scene_last_frame
                        },
                        use_first_frame_constraint=True
                    )
                
                generated_keyframes = []
                
                if self.use_original_keyframes and reference_keyframes:
                    self.log("步骤3", f"片段{i+1}", f"使用原视频关键帧，数量: {len(reference_keyframes)}")
                    
                    if i > 0 and previous_scene_last_frame and os.path.exists(previous_scene_last_frame):
                        generated_keyframes = [previous_scene_last_frame] + reference_keyframes[:2]
                    else:
                        generated_keyframes = reference_keyframes[:3]
                        
                    formatted_keyframes = []
                    for kf in generated_keyframes:
                        if kf and isinstance(kf, str) and os.path.exists(kf):
                            formatted_keyframes.append(kf)
                    if formatted_keyframes:
                        generated_keyframes = formatted_keyframes
                    else:
                        self.log("步骤3", f"片段{i+1}", "警告: 没有有效的关键帧文件")
                else:
                    self.log("步骤3", f"片段{i+1}", "AI生成关键帧")
                    
                    keyframe_prompt = {
                        "video_prompt": enhanced_prompt,
                        "technical_params": {
                            "frame_rate": 24,
                            "resolution": "1920x1080"
                        }
                    }
                    
                    if previous_keyframes:
                        keyframe_prompt['previous_keyframes'] = previous_keyframes
                    
                    keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
                        keyframe_prompt,
                        reference_images=reference_keyframes if reference_keyframes else None,
                        num_keyframes=3,
                        previous_last_frame=previous_scene_last_frame
                    )
                    
                    if keyframe_result.get('success'):
                        generated_keyframes = keyframe_result.get('keyframes', [])
                        self.log("步骤3", f"片段{i+1}", f"关键帧生成成功，数量: {len(generated_keyframes)}")
                    else:
                        error_msg = keyframe_result.get('error', '未知错误')
                        self.log("步骤3", f"片段{i+1}", f"关键帧生成失败: {error_msg}，跳过此场景")
                        logger.error(f"片段{i+1}关键帧生成失败: {error_msg}")
                        continue
                
                video_result = self.qwen_video_service.generate_video_from_keyframes(
                    generated_keyframes,
                    {
                        "video_prompt": enhanced_prompt,
                        "technical_params": {
                            "frame_rate": 24,
                            "resolution": "1920x1080",
                            "duration": scene_prompt.get('duration', 4)
                        },
                        "enable_native_audio": self.enable_native_audio,
                        "dialogues": scene_prompt.get('dialogues', []),
                        "audio_refs": scene_prompt.get('audio_refs', [])
                    }
                )
                
                if video_result.get('success'):
                    video_url = video_result.get('video_url')
                    audio_url = video_result.get('audio_url')
                    local_video_path = os.path.join(self.output_dir, f"scene_{i+1:02d}.mp4")
                    local_audio_path = None
                    
                    download_result = await self.download_media(video_url, local_video_path, "video", f"步骤3-片段{i+1}")
                    
                    if download_result.get('success'):
                        if audio_url and self.enable_native_audio:
                            local_audio_path = os.path.join(self.output_dir, f"scene_{i+1:02d}_audio.mp3")
                            await self.download_media(audio_url, local_audio_path, "audio", f"步骤3-片段{i+1}")
                        
                        last_frame_path = os.path.join(self.output_dir, f"scene_{i+1:02d}_last_frame.jpg")
                        last_frame_result = await self.ffmpeg_service.extract_last_frame(
                            local_video_path, last_frame_path
                        )
                        
                        candidate_frame = None
                        if last_frame_result.get('success'):
                            candidate_frame = last_frame_result.get('frame_path', last_frame_path)
                            quality_result = self.video_quality_service.assess_video_quality(local_video_path)
                            quality_score = quality_result.get('overall_score', 0) if quality_result.get('success') else 0
                            
                            if quality_score >= 0.7:
                                previous_scene_last_frame = candidate_frame
                                self.log("步骤3", f"片段{i+1}", f"质量评分{quality_score:.2f}，采用最后一帧作为下一场景首帧参考")
                            else:
                                self.log("步骤3", f"片段{i+1}", f"质量评分{quality_score:.2f}低于0.7，尝试使用关键帧作为备选")
                                fallback_frame = generated_keyframes[-1] if generated_keyframes else None
                                if fallback_frame and isinstance(fallback_frame, str) and os.path.exists(fallback_frame):
                                    previous_scene_last_frame = fallback_frame
                                    self.log("步骤3", f"片段{i+1}", f"使用最后一个关键帧作为首帧参考")
                                else:
                                    previous_scene_last_frame = candidate_frame
                                    self.log("步骤3", f"片段{i+1}", f"无可用关键帧，仍使用提取的最后一帧（质量可能较低）")
                        else:
                            self.log("步骤3", f"片段{i+1}", f"提取最后一帧失败，尝试使用关键帧")
                            fallback_frame = generated_keyframes[-1] if generated_keyframes else None
                            if fallback_frame and isinstance(fallback_frame, str) and os.path.exists(fallback_frame):
                                previous_scene_last_frame = fallback_frame
                                self.log("步骤3", f"片段{i+1}", f"使用最后一个关键帧作为首帧参考")
                            else:
                                self.log("步骤3", f"片段{i+1}", "警告: 无法获取有效的首帧参考，保持上一帧不变")
                        
                        if previous_scene_last_frame:
                            self.frame_continuity_service.set_previous_scene_frame(previous_scene_last_frame)
                        
                        video_info = {
                            'scene_id': i + 1,
                            'scene_index': i,
                            'video_path': local_video_path,
                            'audio_path': local_audio_path if audio_url else None,
                            'keyframes': generated_keyframes,
                            'prompt': enhanced_prompt,
                            'dialogues': scene_prompt.get('dialogues', []),
                            'duration': scene_prompt.get('duration', 4),
                            'native_audio_enabled': self.enable_native_audio,
                            'success': True
                        }
                        
                        if self.consistency_agent_service and i > 0:
                            self.log("步骤3", f"片段{i+1}", "开始实时一致性检查")
                            scene_data = {
                                'order': i,
                                'scene_id': i + 1,
                                'video_path': local_video_path,
                                'keyframes': generated_keyframes,
                                'prompt_data': {
                                    'original_prompt': enhanced_prompt,
                                    'generation_params': {
                                        'frame_rate': 24,
                                        'resolution': '1920x1080',
                                        'duration': scene_prompt.get('duration', 4)
                                    }
                                }
                            }
                            
                            try:
                                consistency_result = await self.consistency_agent_service.run_check_loop(
                                    video_generation_pipeline=self,
                                    scene_data=scene_data,
                                    max_retries=self.max_retries
                                )
                                
                                if consistency_result.get('status') == 'success':
                                    retry_count = consistency_result.get('retry_count', 0)
                                    self.log("步骤3", f"片段{i+1}", f"一致性检查通过，重试次数: {retry_count}")
                                    
                                    if retry_count > 0:
                                        updated_scene = consistency_result.get('scene', {})
                                        video_info['video_path'] = updated_scene.get('video_path', local_video_path)
                                        video_info['keyframes'] = updated_scene.get('keyframes', generated_keyframes)
                                        video_info['prompt'] = updated_scene.get('prompt_data', {}).get('original_prompt', enhanced_prompt)
                                        video_info['regenerated'] = True
                                        
                                        if video_info['keyframes'] and isinstance(video_info['keyframes'][-1], str):
                                            previous_scene_last_frame = video_info['keyframes'][-1]
                                            self.log("步骤3", f"片段{i+1}", f"更新首帧参考为重新生成的最后一帧")
                                        else:
                                            self.log("步骤3", f"片段{i+1}", "警告: 重新生成的关键帧为空或无效，保持原首帧参考")
                                else:
                                    self.log("步骤3", f"片段{i+1}", f"一致性检查失败，已重试{consistency_result.get('retry_count', 0)}次")
                                    video_info['consistency_failed'] = True
                                
                                video_info['consistency'] = consistency_result
                                
                            except Exception as e:
                                self.log("步骤3", f"片段{i+1}", f"一致性检查异常: {str(e)}")
                                video_info['consistency'] = {
                                    'status': 'error',
                                    'error': str(e),
                                    'passed': False
                                }
                        
                        self.generated_videos.append(video_info)
                        
                        previous_keyframes = generated_keyframes
                    else:
                        self.log("步骤3", f"片段{i+1}", f"下载失败: {download_result.get('error')}")
                else:
                    self.log("步骤3", f"片段{i+1}", f"生成失败: {video_result.get('error')}")
            
            success_count = len([v for v in self.generated_videos if v['success']])
            self.log("步骤3", "视频片段生成完成", f"成功: {success_count}/{len(self.scene_prompts)}")
            
            return {
                'success': success_count > 0,
                'generated_videos': self.generated_videos
            }
            
        except Exception as e:
            self.log("步骤3", "失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def step_4_quality_check(self) -> Dict[str, Any]:
        """
        步骤4: 质检片段
        对每个生成的视频片段进行质量评估
        注意: 一致性检查已在步骤3中实时完成
        """
        self.log("步骤4", "质检片段", "开始质量评估")
        
        try:
            for i, video_info in enumerate(self.generated_videos):
                if not video_info.get('success'):
                    continue
                
                video_path = video_info.get('video_path')
                self.log("步骤4", f"评估片段{i+1}", f"路径: {video_path}")
                
                quality_result = self.video_quality_service.assess_video_quality(video_path)
                
                if quality_result.get('success'):
                    score = quality_result.get('overall_score', 0)
                    grade = quality_result.get('grade', 'unknown')
                    passed = quality_result.get('passed', False)
                    
                    self.log("步骤4", f"片段{i+1}评估结果", 
                            f"得分: {score:.2f}, 等级: {grade}, 通过: {'是' if passed else '否'}")
                    
                    video_info['quality'] = {
                        'score': score,
                        'grade': grade,
                        'passed': passed,
                        'details': quality_result.get('scores', {}),
                        'issues': quality_result.get('issues', [])
                    }
                    
                    if video_info.get('consistency'):
                        consistency_status = video_info['consistency'].get('status', 'unknown')
                        self.log("步骤4", f"片段{i+1}", f"一致性检查状态: {consistency_status} (已在步骤3完成)")
                    
                    self.quality_results.append(quality_result)
                else:
                    self.log("步骤4", f"片段{i+1}评估失败", quality_result.get('error', ''))
                    video_info['quality'] = {
                        'score': 0,
                        'grade': 'failed',
                        'passed': False,
                        'error': quality_result.get('error')
                    }
            
            passed_count = len([v for v in self.generated_videos if v.get('quality', {}).get('passed', False)])
            self.log("步骤4", "质检完成", f"通过: {passed_count}/{len(self.generated_videos)}")
            
            return {
                'success': True,
                'quality_results': self.quality_results,
                'passed_count': passed_count
            }
            
        except Exception as e:
            self.log("步骤4", "失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def step_5_merge_videos(self) -> Dict[str, Any]:
        """
        步骤5: 融合视频
        将所有通过质检的视频片段合并为最终视频
        如果启用了原生音频，则保留各片段的音频
        """
        self.log("步骤5", "融合视频", "开始合并视频片段")
        
        try:
            valid_videos = [
                v for v in self.generated_videos 
                if v.get('success') and v.get('quality', {}).get('passed', True)
            ]
            
            if not valid_videos:
                self.log("步骤5", "失败", "没有通过质检的视频片段")
                return {'success': False, 'error': '没有通过质检的视频片段'}
            
            video_paths = [v['video_path'] for v in valid_videos]
            self.log("步骤5", "待合并片段", f"数量: {len(video_paths)}")
            
            has_native_audio = any(v.get('native_audio_enabled') for v in valid_videos)
            
            self.final_video_path = os.path.join(self.output_dir, "final_video_no_tts.mp4")
            
            compose_result = await self.ffmpeg_service.compose_videos(
                video_paths,
                self.final_video_path
            )
            
            if compose_result.get('success'):
                self.log("步骤5", "视频融合完成", f"输出路径: {self.final_video_path}")
                
                if has_native_audio:
                    self.log("步骤5", "音频状态", "已保留原生音频")
                
                final_quality = self.video_quality_service.comprehensive_assessment(
                    self.final_video_path,
                    keyframes=[v.get('keyframes', []) for v in valid_videos],
                    original_video_path=self.video_path
                )
                
                if final_quality.get('success'):
                    tech_score = final_quality.get('technical_quality', {}).get('score', 0)
                    content_score = final_quality.get('content_consistency', {}).get('score', 0)
                    comp_score = final_quality.get('comprehensive_score', 0)
                    
                    self.log("步骤5", "最终视频综合评估", 
                            f"技术得分: {tech_score:.2f}, 内容得分: {content_score:.2f}, 综合得分: {comp_score:.2f}")
                
                if self.video_path:
                    comparison = self.video_quality_service.compare_with_original(
                        self.video_path,
                        self.final_video_path
                    )
                    if comparison.get('success'):
                        similarity = comparison.get('comparison', {}).get('similarity_score', 0)
                        self.log("步骤5", "与原视频对比", f"相似度: {similarity:.2f}")
                
                report_path = os.path.join(self.output_dir, "quality_report.md")
                self.video_quality_service.generate_quality_report(
                    self.final_video_path,
                    report_path
                )
                self.log("步骤5", "质量报告", f"已保存: {report_path}")
                
                character_audio_registry_path = os.path.join(self.output_dir, "character_audio_registry.json")
                with open(character_audio_registry_path, 'w', encoding='utf-8') as f:
                    json.dump(self.character_audio_registry, f, ensure_ascii=False, indent=2)
                self.log("步骤5", "角色音频注册表", f"已保存: {character_audio_registry_path}")
                
                return {
                    'success': True,
                    'final_video_path': self.final_video_path,
                    'final_quality': final_quality,
                    'native_audio_enabled': has_native_audio,
                    'character_audio_registry': self.character_audio_registry
                }
            else:
                self.log("步骤5", "失败", compose_result.get('error', '未知错误'))
                return {'success': False, 'error': compose_result.get('error', '未知错误')}
            
        except Exception as e:
            self.log("步骤5", "失败", str(e))
            return {'success': False, 'error': str(e)}
    
    async def run_full_pipeline(self, video_path: str) -> Dict[str, Any]:
        """
        运行完整流程
        
        Args:
            video_path: 输入视频路径
            
        Returns:
            完整流程结果
        """
        start_time = time.time()
        self.log("完整流程", "开始", f"输入视频: {video_path}")
        
        results = {}
        
        steps = [
            ("步骤0_输入视频", lambda: self.step_0_input_video(video_path)),
            ("步骤1_输出视频脚本", self.step_1_output_video_script),
            ("步骤2_细化分镜", self.step_2_refine_storyboard),
            ("步骤3_输出视频片段", self.step_3_generate_video_clips),
            ("步骤4_质检片段", self.step_4_quality_check),
            ("步骤5_融合视频", self.step_5_merge_videos),
        ]
        
        for step_name, step_func in steps:
            try:
                self.log("完整流程", f"执行 {step_name}")
                result = await step_func()
                results[step_name] = result
                
                if not result.get('success'):
                    self.log("完整流程", f"{step_name} 失败", result.get('error', '未知错误'))
                    break
                    
            except Exception as e:
                self.log("完整流程", f"{step_name} 异常", str(e))
                results[step_name] = {'success': False, 'error': str(e)}
                break
        
        total_time = time.time() - start_time
        
        summary = {
            'success': self.final_video_path is not None,
            'total_time': total_time,
            'output_dir': self.output_dir,
            'final_video_path': self.final_video_path,
            'video_slices_count': len(self.video_slices),
            'scene_prompts_count': len(self.scene_prompts),
            'generated_videos_count': len(self.generated_videos),
            'quality_passed_count': len([v for v in self.generated_videos if v.get('quality', {}).get('passed', False)]),
            'results': results
        }
        
        summary_path = os.path.join(self.output_dir, "pipeline_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
        
        self.log("完整流程", "完成", 
                f"总耗时: {total_time:.1f}s, "
                f"最终视频: {self.final_video_path or '无'}")
        
        return summary


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='无TTS视频生成测试流程 - 支持Seedance 2.0原生音频')
    parser.add_argument('--video', '-v', type=str, required=True, help='输入视频路径')
    parser.add_argument('--output', '-o', type=str, default=None, help='输出目录')
    parser.add_argument('--slice-count', '-n', type=int, default=5, help='切片数量')
    parser.add_argument('--slice-duration', '-d', type=int, default=5, help='切片时长(秒)')
    parser.add_argument('--use-original-keyframes', '-k', action='store_true', default=True,
                       help='使用原视频关键帧')
    parser.add_argument('--enable-native-audio', '-a', action='store_true', default=True,
                       help='启用Seedance 2.0原生音频生成（默认开启）')
    parser.add_argument('--disable-native-audio', action='store_true',
                       help='禁用原生音频生成')
    
    args = parser.parse_args()
    
    enable_native_audio = args.enable_native_audio and not args.disable_native_audio
    
    config = {
        'slice_count': args.slice_count,
        'slice_duration': args.slice_duration,
        'use_original_keyframes': args.use_original_keyframes,
        'enable_native_audio': enable_native_audio
    }
    
    if args.output:
        config['output_dir'] = args.output
    
    pipeline = NoTTSVideoPipeline(config)
    
    result = await pipeline.run_full_pipeline(args.video)
    
    print("\n" + "="*60)
    print("测试流程完成!")
    print("="*60)
    print(f"成功: {result['success']}")
    print(f"总耗时: {result['total_time']:.1f}秒")
    print(f"输出目录: {result['output_dir']}")
    print(f"最终视频: {result['final_video_path']}")
    print(f"生成片段: {result['generated_videos_count']}")
    print(f"质检通过: {result['quality_passed_count']}")
    print(f"原生音频: {'启用' if enable_native_audio else '禁用'}")


if __name__ == "__main__":
    asyncio.run(main())
