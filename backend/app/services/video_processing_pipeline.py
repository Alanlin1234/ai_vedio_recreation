"""
视频处理流程服务
整合视频切片、分析、生成、音频合成、最终合成等完整流程
"""
import os
import sys
import time
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.ffmpeg_service import FFmpegService
from app.services.qwen_vl_service import QwenVLService
from app.services.qwen_video_service import QwenVideoService
from app.services.scene_segmentation_service import SceneSegmentationService
from app.services.json_prompt_parser import JSONPromptParser
from app.services.frame_continuity_service import FrameContinuityService
from app.services.speaker_voice_service import SpeakerVoiceService
from app.services.speaker_tts_integration import SpeakerTTSIntegration
from app.services.video_quality_assessment_service import VideoQualityAssessmentService

logger = logging.getLogger(__name__)


class VideoProcessingPipeline:
    """视频处理完整流程服务"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', f"downloads/pipeline_{int(time.time())}")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.use_original_keyframes = self.config.get('use_original_keyframes', True)
        self.slice_count = self.config.get('slice_count', 5)
        self.slice_duration = self.config.get('slice_duration', 5)
        
        self._init_services()
        
        self.video_slices = []
        self.scene_prompts = []
        self.generated_videos = []
        self.consistency_results = []
        self.speaker_info = None
        self.video_path = None
        
        self._log_callback = None
    
    def _init_services(self):
        """初始化所有服务"""
        self.ffmpeg_service = FFmpegService()
        self.qwen_vl_service = QwenVLService()
        self.qwen_video_service = QwenVideoService()
        self.scene_segmenter = SceneSegmentationService()
        self.json_parser = JSONPromptParser()
        self.frame_continuity_service = FrameContinuityService()
        self.speaker_voice_service = SpeakerVoiceService()
        self.speaker_tts_integration = SpeakerTTSIntegration()
        self.video_quality_service = VideoQualityAssessmentService(
            self.config.get('quality_config', {
                'min_resolution': (1280, 720),
                'min_fps': 24,
                'min_bitrate': 1000000
            })
        )
        
        consistency_config_path = self.config.get(
            'consistency_config_path', 
            "video_consistency_agent/config/config.yaml"
        )
        try:
            from video_consistency_agent.agent.consistency_agent import ConsistencyAgent
            self.consistency_agent = ConsistencyAgent(consistency_config_path)
        except Exception as e:
            logger.warning(f"ConsistencyAgent初始化失败: {e}")
            self.consistency_agent = None
    
    def set_log_callback(self, callback: Callable[[str, str, str], None]):
        """设置日志回调函数"""
        self._log_callback = callback
    
    def log(self, step_name: str, status: str, debug_info: str = ""):
        """记录日志"""
        message = f"[{time.strftime('%H:%M:%S')}] {step_name}: {status}"
        if debug_info:
            message += f" | {debug_info}"
        
        logger.info(message)
        
        if self._log_callback:
            self._log_callback(step_name, status, debug_info)
        else:
            print(message)
    
    async def slice_video(self, video_path: str) -> Dict[str, Any]:
        """
        视频切片
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            切片结果
        """
        self.log("视频切片", "开始")
        self.video_path = video_path
        
        try:
            video_info = await self.ffmpeg_service.get_video_info(video_path)
            total_duration = video_info.get('duration', 20)
            
            self.log("视频切片", "获取视频信息", f"总时长: {total_duration:.1f}s, 切片时长: {self.slice_duration}s")
            
            slice_result = await self.ffmpeg_service.slice_video(
                video_path, 
                slice_duration=self.slice_duration,
                slice_limit=10
            )
            
            if slice_result and 'slices' in slice_result:
                self.video_slices = slice_result['slices'][:self.slice_count]
                
                for i, slice_info in enumerate(self.video_slices):
                    audio_result = await self.ffmpeg_service.extract_audio(slice_info['output_file'])
                    if audio_result and 'audio_path' in audio_result:
                        self.video_slices[i]['audio_file'] = audio_result['audio_path']
                        self.log("音频提取", f"切片{i+1}音频提取完成", f"音频路径: {audio_result['audio_path']}")
                    
                    if 'keyframes' in slice_info and slice_info['keyframes']:
                        self.log("关键帧提取", f"切片{i+1}已提取关键帧", f"关键帧数量: {len(slice_info['keyframes'])}")
                
                self.log("视频切片", f"完成，生成{len(self.video_slices)}个切片")
                return {'success': True, 'slices': self.video_slices}
            else:
                self.log("视频切片", "失败，切片结果格式错误")
                return {'success': False, 'error': '切片结果格式错误'}
        except Exception as e:
            self.log("视频切片", f"失败: {str(e)}")
            logger.error(f"视频切片失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def analyze_video_slices(self) -> Dict[str, Any]:
        """
        分析视频切片
        
        Returns:
            分析结果
        """
        self.log("视频切片分析", "开始")
        
        try:
            from app.services.speech_recognition_service import SimpleSpeechRecognizer
            speech_recognizer = SimpleSpeechRecognizer()
            
            self.log("视频切片分析", "初始化服务", "语音识别器初始化完成")
            
            slice_audio_contents = []
            for i, slice_info in enumerate(self.video_slices):
                if 'audio_file' in slice_info and slice_info['audio_file']:
                    self.log("音频转录", f"开始转录切片{i+1}的音频")
                    transcribe_result = speech_recognizer.transcribe(slice_info['audio_file'])
                    if transcribe_result.get('success'):
                        slice_audio_content = transcribe_result.get('text', '')
                        slice_audio_contents.append(slice_audio_content)
                        self.video_slices[i]['audio_content'] = slice_audio_content
                        self.log("音频转录", f"切片{i+1}音频转录完成", f"音频内容长度: {len(slice_audio_content)} 字符")
                    else:
                        slice_audio_contents.append('')
                        self.log("音频转录", f"切片{i+1}音频转录失败")
                else:
                    slice_audio_contents.append('')
            
            self.log("qwen-omni-turbo分析", "开始", f"分析{len(self.video_slices)}个切片")
            try:
                analysis_results = await self.qwen_vl_service.analyze_video_content(
                    self.video_slices,
                    audio_contents=slice_audio_contents
                )
                
                if analysis_results:
                    for i, result in enumerate(analysis_results):
                        if i < len(self.video_slices):
                            self.video_slices[i]['analysis'] = result
                            self.log("qwen-omni-turbo分析", f"切片{i+1}分析完成")
                    self.log("qwen-omni-turbo分析", "完成")
            except Exception as e:
                self.log("qwen-omni-turbo分析", f"失败: {str(e)}")
                logger.error(f"qwen-omni-turbo分析失败: {str(e)}", exc_info=True)
            
            self.log("关键帧提取", "开始")
            for i, slice_info in enumerate(self.video_slices):
                if 'keyframes' not in slice_info or not slice_info['keyframes']:
                    if 'preview_file' in slice_info and slice_info['preview_file']:
                        self.video_slices[i]['keyframes'] = [slice_info['preview_file']]
                        self.log("关键帧提取", f"切片{i+1}完成", "关键帧数量: 1")
                else:
                    self.log("关键帧提取", f"切片{i+1}已有{len(slice_info['keyframes'])}个关键帧")
            self.log("关键帧提取", "完成")
            
            self.log("qwen3-vl-plus关键帧分析", "开始")
            try:
                for i, slice_info in enumerate(self.video_slices):
                    if 'keyframes' in slice_info and slice_info['keyframes']:
                        keyframes = slice_info['keyframes']
                        try:
                            vl_result = self.qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                                keyframes, 
                                {"video_prompt": f"分析第{i+1}个场景的关键帧，生成详细的视频描述",
                                 "audio_content": slice_info.get('audio_content', '')}
                            )
                            if vl_result.get('success'):
                                self.video_slices[i]['vl_analysis'] = vl_result
                                self.log("qwen3-vl-plus关键帧分析", f"场景{i+1}成功")
                            else:
                                self.log("qwen3-vl-plus关键帧分析", f"场景{i+1}失败")
                        except Exception as e:
                            self.log("qwen3-vl-plus关键帧分析", f"场景{i+1}失败: {str(e)}")
                self.log("qwen3-vl-plus关键帧分析", "完成")
            except Exception as e:
                self.log("qwen3-vl-plus关键帧分析", f"失败: {str(e)}")
                logger.error(f"qwen3-vl-plus关键帧分析失败: {str(e)}", exc_info=True)
            
            return {'success': True, 'slices': self.video_slices}
        except Exception as e:
            self.log("视频切片分析", f"失败: {str(e)}")
            logger.error(f"视频切片分析失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def combine_and_optimize_prompts(self) -> Dict[str, Any]:
        """
        结合和优化提示词
        
        Returns:
            优化结果
        """
        self.log("提示词优化", "开始")
        
        try:
            for i, slice_info in enumerate(self.video_slices):
                previous_scene_info = None
                if i > 0 and self.scene_prompts:
                    previous_scene_info = {
                        'shot_breakdown': self.scene_prompts[i-1].get('shot_breakdown', {}),
                        'visual_content': self.scene_prompts[i-1].get('visual_content', {}),
                        'audio_info': self.scene_prompts[i-1].get('audio_info', {})
                    }
                
                result = self.qwen_video_service.generate_structured_prompt(
                    slice_info=slice_info,
                    scene_index=i,
                    previous_scene_info=previous_scene_info
                )
                
                if result.get('success'):
                    combined_prompt = {
                        "scene_id": result['scene_id'],
                        "start_time": result['start_time'],
                        "end_time": result['end_time'],
                        "duration": result['duration'],
                        "shot_breakdown": result['shot_breakdown'],
                        "shot_info": result['shot_info'],
                        "visual_content": result['visual_content'],
                        "audio_info": result['audio_info'],
                        "video_prompt": result['video_prompt'],
                        "optimized_prompt": result['optimized_prompt'],
                        "style_elements": result['style_elements'],
                        "original_video_info": {
                            "slice_path": slice_info['output_file'],
                            "audio_path": slice_info.get('audio_file', ''),
                            "keyframes": slice_info.get('keyframes', [])
                        }
                    }
                    self.scene_prompts.append(combined_prompt)
                else:
                    self.log("提示词优化", f"场景{i+1}生成失败: {result.get('error')}")
            
            if self.scene_prompts:
                summary_result = self.qwen_video_service.generate_overall_summary(self.scene_prompts)
                if summary_result.get('success'):
                    self.scene_prompts[0]["overall_summary"] = summary_result
            
            self.log("提示词优化", f"完成，生成{len(self.scene_prompts)}个场景提示词")
            return {'success': True, 'prompts': self.scene_prompts}
        except Exception as e:
            self.log("提示词优化", f"失败: {str(e)}")
            logger.error(f"提示词优化失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def parse_json_prompts(self) -> Dict[str, Any]:
        """
        解析JSON提示词
        
        Returns:
            解析结果
        """
        self.log("JSON提示词解析", "开始")
        
        try:
            for i, prompt in enumerate(self.scene_prompts):
                prompt_json = json.dumps(prompt, ensure_ascii=False)
                parsed_result = self.json_parser.parse_prompt(prompt_json, prompt_type="txt2img")
                
                if parsed_result.get('success'):
                    self.scene_prompts[i]['parsed_prompt'] = parsed_result.get('prompt', '')
                else:
                    self.scene_prompts[i]['parsed_prompt'] = prompt.get('optimized_prompt', '')
            
            self.log("JSON提示词解析", "完成")
            return {'success': True, 'prompts': self.scene_prompts}
        except Exception as e:
            self.log("JSON提示词解析", f"失败: {str(e)}")
            logger.error(f"JSON提示词解析失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def generate_scene_videos(self) -> Dict[str, Any]:
        """
        生成场景视频
        
        Returns:
            生成结果
        """
        self.log("场景视频生成", "开始")
        
        try:
            previous_keyframes = []
            previous_scene_last_frame = None
            
            for i, scene_prompt in enumerate(self.scene_prompts):
                self.log(f"场景{i+1}视频生成", "开始")
                
                slice_info = self.video_slices[i]
                reference_keyframes = slice_info.get('keyframes', [])
                
                enhanced_prompt = scene_prompt.get('parsed_prompt', '')
                if i > 0 and previous_scene_last_frame:
                    self.log(f"场景{i+1}视频生成", "使用上一场景的最后一帧作为首帧")
                    enhanced_prompt = self.frame_continuity_service.build_contextual_prompt(
                        current_prompt=scene_prompt.get('parsed_prompt', ''),
                        previous_scene_info={
                            'prompt_data': {
                                'original_prompt': self.scene_prompts[i-1].get('parsed_prompt', '') if i > 0 else '',
                                'generation_params': {
                                    'frame_rate': 24,
                                    'resolution': '1920x1080',
                                    'duration': self.scene_prompts[i-1].get('duration', 4) if i > 0 else 4
                                }
                            },
                            'last_frame': previous_scene_last_frame
                        },
                        use_first_frame_constraint=True
                    )
                    enhanced_prompt += ", 保持与上一场景的连续性，确保当前场景的第一帧与上一场景的最后一帧自然过渡"
                    scene_prompt['parsed_prompt'] = enhanced_prompt
                    self.log(f"场景{i+1}视频生成", "成功构建包含上下文的提示词")
                
                if self.use_original_keyframes:
                    self.log(f"场景{i+1}视频生成", "使用原视频的关键帧")
                    
                    if i > 0 and previous_scene_last_frame:
                        generated_keyframes = [previous_scene_last_frame] + reference_keyframes
                        generated_keyframes = generated_keyframes[:3]
                    else:
                        generated_keyframes = reference_keyframes[:3]
                    
                    self.log(f"场景{i+1}视频生成", f"使用关键帧，数量: {len(generated_keyframes)}")
                    
                    formatted_keyframes = []
                    for keyframe in generated_keyframes:
                        if keyframe and os.path.exists(keyframe):
                            normalized_path = self.ffmpeg_service.normalize_frame_path(keyframe)
                            formatted_keyframes.append(normalized_path)
                    if formatted_keyframes:
                        generated_keyframes = formatted_keyframes
                        self.log(f"场景{i+1}视频生成", f"格式化关键帧路径完成")
                    else:
                        self.log(f"场景{i+1}视频生成", "警告: 没有有效的关键帧")
                        generated_keyframes = [f"https://example.com/simulated_keyframe_{i+1}.jpg"]
                else:
                    self.log(f"场景{i+1}视频生成", "使用AI生成关键帧")
                    keyframe_prompt = {
                        "video_prompt": scene_prompt.get('parsed_prompt', ''),
                        "technical_params": {"frame_rate": 24, "resolution": "1920x1080"}
                    }
                    
                    reference_imgs = reference_keyframes
                    if i > 0 and previous_scene_last_frame:
                        reference_imgs = [previous_scene_last_frame] + reference_imgs
                    
                    if previous_keyframes:
                        keyframe_prompt['previous_keyframes'] = previous_keyframes
                    
                    keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
                        keyframe_prompt,
                        reference_images=reference_imgs,
                        num_keyframes=3,
                        previous_last_frame=previous_scene_last_frame
                    )
                    
                    if not keyframe_result.get('success'):
                        self.log(f"场景{i+1}视频生成", "失败，关键帧生成失败")
                        continue
                    
                    generated_keyframes = keyframe_result.get('keyframes', [])
                    self.log(f"场景{i+1}视频生成", f"关键帧生成完成，数量: {len(generated_keyframes)}")
                
                if i > 0 and previous_scene_last_frame and os.path.exists(previous_scene_last_frame):
                    scene_prompt['parsed_prompt'] += f", 严格将上一场景的最后一帧作为当前场景的第一帧"
                    generated_keyframes = [previous_scene_last_frame] + generated_keyframes[:2]
                
                video_result = self.qwen_video_service.generate_video_from_keyframes(
                    generated_keyframes,
                    {
                        "video_prompt": scene_prompt.get('parsed_prompt', ''),
                        "technical_params": {
                            "frame_rate": 24,
                            "resolution": "1920x1080",
                            "duration": scene_prompt.get('duration', 4)
                        }
                    }
                )
                
                if video_result.get('success'):
                    video_path = await self.ffmpeg_service.download_video(
                        video_result.get('video_url', ''),
                        os.path.join(self.output_dir, f"scene_{i+1}.mp4")
                    )
                    
                    quality_result = self.video_quality_service.assess_video_quality(video_path)
                    if quality_result.get('success'):
                        self.log(f"场景{i+1}视频质量评估", 
                                f"得分: {quality_result.get('overall_score', 0):.2f}, "
                                f"等级: {quality_result.get('grade', '未知')}, "
                                f"通过: {'是' if quality_result.get('passed') else '否'}")
                    
                    last_frame_path = os.path.join(self.output_dir, f"scene_{i+1}_last_frame.jpg")
                    last_frame_result = await self.ffmpeg_service.extract_last_frame(
                        video_path,
                        last_frame_path
                    )
                    
                    if last_frame_result.get('success'):
                        extracted_frame_path = last_frame_result.get('frame_path', last_frame_path)
                        previous_scene_last_frame = extracted_frame_path
                        self.frame_continuity_service.set_previous_scene_frame(previous_scene_last_frame)
                        self.log(f"场景{i+1}视频生成", f"成功提取最后一帧")
                    
                    consistency_result = None
                    if self.consistency_agent:
                        consistency_data = {
                            "current_scene": {
                                "keyframes": generated_keyframes,
                                "prompt_data": {
                                    "original_prompt": scene_prompt.get('parsed_prompt', ''),
                                    "generation_params": {
                                        "frame_rate": 24,
                                        "resolution": "1920x1080",
                                        "duration": scene_prompt.get('duration', 4)
                                    }
                                },
                                "order": i
                            },
                            "previous_scene": {
                                "keyframes": previous_keyframes,
                                "prompt_data": {
                                    "original_prompt": self.scene_prompts[i-1].get('parsed_prompt', '') if i > 0 else '',
                                    "generation_params": {
                                        "frame_rate": 24,
                                        "resolution": "1920x1080",
                                        "duration": self.scene_prompts[i-1].get('duration', 4) if i > 0 else 4
                                    }
                                },
                                "order": i-1
                            },
                            "prompt_data": {
                                "original_prompt": scene_prompt.get('parsed_prompt', ''),
                                "generation_params": {
                                    "frame_rate": 24,
                                    "resolution": "1920x1080",
                                    "duration": scene_prompt.get('duration', 4)
                                }
                            }
                        }
                        
                        consistency_result = await self.consistency_agent.check_consistency(
                            consistency_data["current_scene"],
                            consistency_data["previous_scene"],
                            consistency_data["prompt_data"]
                        )
                        self.consistency_results.append(consistency_result)
                    
                    self.generated_videos.append({
                        'scene_id': i + 1,
                        'video_path': video_path,
                        'keyframes': generated_keyframes,
                        'consistency_score': consistency_result.get('consistency_results', {}).get('score', 0.0) if consistency_result else 0,
                        'quality_score': quality_result.get('overall_score', 0) if quality_result.get('success') else 0,
                        'quality_grade': quality_result.get('grade', '未知') if quality_result.get('success') else '未知',
                        'quality_passed': quality_result.get('passed', False) if quality_result.get('success') else False,
                        'success': True
                    })
                    
                    previous_keyframes = generated_keyframes
                    
                    if consistency_result and consistency_result.get('passed'):
                        self.log(f"场景{i+1}视频生成", "完成")
                    else:
                        self.log(f"场景{i+1}视频生成", "一致性检查未通过，但继续执行")
                else:
                    self.log(f"场景{i+1}视频生成", f"失败: {video_result.get('error')}")
            
            success_count = len([v for v in self.generated_videos if v['success']])
            total_count = len(self.generated_videos)
            self.log("场景视频生成", f"完成，生成{total_count}个场景视频，其中{success_count}个成功")
            return {'success': True, 'videos': self.generated_videos}
        except Exception as e:
            self.log("场景视频生成", f"失败: {str(e)}")
            logger.error(f"场景视频生成失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def synthesize_audio(self) -> Dict[str, Any]:
        """
        合成音频
        
        Returns:
            合成结果
        """
        self.log("音频合成", "开始")
        
        try:
            from app.services.text_to_speech_service import TextToSpeechService
            content_generator = TextToSpeechService()
            
            speaker_id = None
            voice_seed = None
            
            if self.video_slices and 'audio_file' in self.video_slices[0]:
                audio_path = self.video_slices[0]['audio_file']
                if os.path.exists(audio_path):
                    self.log("音频合成", "提取说话人信息")
                    speaker_result = self.speaker_voice_service.extract_speakers_from_audio(audio_path)
                    if speaker_result.get('success') and speaker_result.get('speakers'):
                        speaker = speaker_result['speakers'][0]
                        speaker_id = speaker.get('speaker_id')
                        voice_seed = speaker.get('voice_seed')
                        self.log("音频合成", f"成功提取说话人: {speaker_id}")
                        
                        save_result = self.speaker_voice_service.save_speaker_voice_seed(
                            speaker_id=speaker_id,
                            voice_seed=voice_seed,
                            audio_sample_path=audio_path
                        )
                        if save_result.get('success'):
                            self.log("音频合成", "成功保存说话人voice seed")
                    
                    self.speaker_info = {
                        'speaker_id': speaker_id,
                        'voice_seed': voice_seed,
                        'total_speakers': speaker_result.get('total_speakers', 1)
                    }
            
            for i, video in enumerate(self.generated_videos):
                if video['success']:
                    scene_prompt = self.scene_prompts[i]
                    slice_info = self.video_slices[i] if i < len(self.video_slices) else {}
                    audio_content = slice_info.get('audio_content', '')
                    if audio_content:
                        text = audio_content
                    else:
                        text = scene_prompt.get('parsed_prompt', '')
                    
                    audio_output_path = os.path.join(self.output_dir, f"scene_{i+1}_audio.mp3")
                    
                    if speaker_id:
                        self.log(f"场景{i+1}音频合成", "使用说话人识别确保语音一致性")
                        audio_result = self.speaker_tts_integration.generate_audio_with_speaker(
                            text=text,
                            speaker_id=speaker_id,
                            output_path=audio_output_path
                        )
                    else:
                        self.log(f"场景{i+1}音频合成", "使用默认TTS")
                        audio_result = content_generator.text_to_speech(
                            text=text,
                            output_path=audio_output_path
                        )
                    
                    if audio_result.get('success'):
                        video['audio_path'] = audio_result.get('audio_path', '')
                        if 'voice_seed' in audio_result:
                            video['voice_seed'] = audio_result['voice_seed']
            
            self.log("音频合成", "完成")
            return {'success': True, 'speaker_info': self.speaker_info}
        except Exception as e:
            self.log("音频合成", f"失败: {str(e)}")
            logger.error(f"音频合成失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def compose_final_video(self) -> Dict[str, Any]:
        """
        合成最终视频
        
        Returns:
            合成结果
        """
        self.log("最终视频合成", "开始")
        
        try:
            scene_videos_with_audio = []
            for video in self.generated_videos:
                if 'video_path' in video and video['video_path']:
                    if 'audio_path' in video and video['audio_path']:
                        synced_video = await self.ffmpeg_service.sync_audio_video(
                            video['video_path'],
                            video['audio_path'],
                            os.path.join(self.output_dir, f"scene_{video['scene_id']}_with_audio.mp4")
                        )
                        scene_videos_with_audio.append(synced_video)
                    else:
                        scene_videos_with_audio.append({
                            'output_path': video['video_path'],
                            'success': True
                        })
            
            if scene_videos_with_audio:
                final_video_path = os.path.join(self.output_dir, "final_composed_video.mp4")
                video_paths = [v['output_path'] for v in scene_videos_with_audio if v['success'] and 'output_path' in v]
                
                if video_paths:
                    compose_result = await self.ffmpeg_service.compose_videos(
                        video_paths,
                        final_video_path
                    )
                    
                    if compose_result.get('success'):
                        self.log("最终视频合成", f"完成，最终视频路径: {final_video_path}")
                        
                        final_quality = self.video_quality_service.assess_video_quality(final_video_path)
                        if final_quality.get('success'):
                            self.log("最终视频质量评估", 
                                    f"得分: {final_quality.get('overall_score', 0):.2f}, "
                                    f"等级: {final_quality.get('grade', '未知')}")
                        
                        if self.video_path:
                            comparison = self.video_quality_service.compare_with_original(
                                self.video_path, 
                                final_video_path
                            )
                            if comparison.get('success'):
                                similarity = comparison.get('comparison', {}).get('similarity_score', 0)
                                self.log("视频对比分析", f"与原视频相似度: {similarity:.2f}")
                        
                        report_path = os.path.join(self.output_dir, "quality_report.md")
                        report_result = self.video_quality_service.generate_quality_report(
                            final_video_path,
                            report_path
                        )
                        if report_result.get('success'):
                            self.log("质量报告生成", f"报告已保存: {report_path}")
                        
                        return {'success': True, 'video_path': final_video_path}
                    else:
                        self.log("最终视频合成", f"失败: {compose_result.get('error', '未知错误')}")
                        return {'success': False, 'error': compose_result.get('error', '未知错误')}
            
            self.log("最终视频合成", "失败，没有可合成的场景视频")
            return {'success': False, 'error': '没有可合成的场景视频'}
        except Exception as e:
            self.log("最终视频合成", f"失败: {str(e)}")
            logger.error(f"最终视频合成失败: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def run_full_pipeline(self, video_path: str) -> Dict[str, Any]:
        """
        运行完整流程
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            完整流程结果
        """
        self.log("完整流程", "开始")
        
        results = {}
        
        steps = [
            ("切片视频", lambda: self.slice_video(video_path)),
            ("分析视频切片", self.analyze_video_slices),
            ("结合和优化提示词", lambda: asyncio.to_thread(self.combine_and_optimize_prompts)),
            ("解析JSON提示词", lambda: asyncio.to_thread(self.parse_json_prompts)),
            ("生成场景视频", self.generate_scene_videos),
            ("合成音频", self.synthesize_audio),
            ("合成最终视频", self.compose_final_video)
        ]
        
        for step_name, step_func in steps:
            try:
                result = await step_func()
                results[step_name] = result
                if not result.get('success'):
                    self.log("完整流程", f"警告：步骤 '{step_name}' 执行失败，但继续执行后续步骤")
            except Exception as e:
                self.log("完整流程", f"错误：步骤 '{step_name}' 执行异常: {str(e)}")
                logger.error(f"步骤 '{step_name}' 执行异常: {str(e)}", exc_info=True)
                results[step_name] = {'success': False, 'error': str(e)}
        
        self.log("完整流程", "完成")
        return {
            'success': True,
            'results': results,
            'output_dir': self.output_dir,
            'video_slices': self.video_slices,
            'scene_prompts': self.scene_prompts,
            'generated_videos': self.generated_videos,
            'speaker_info': self.speaker_info
        }
