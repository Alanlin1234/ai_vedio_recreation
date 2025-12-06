import os
import sys
import json
import requests
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config
from .video_analysis_agent import VideoAnalysisAgent
from .speech_recognition_service import SimpleSpeechRecognizer
from .scene_segmentation_service import SceneSegmentationService
from .content_generation_service import ContentGenerationService
from app.models import db, VideoRecreation, RecreationScene, RecreationLog

class VideoRecreationService:
    """
    视频二创服务类
    整合视频理解、语音转文本、文案生成、场景分割等功能
    """
    
    def __init__(self):
        self.video_analyzer = VideoAnalysisAgent()
        self.speech_recognizer = SimpleSpeechRecognizer()
        self.scene_segmenter = SceneSegmentationService()
        self.content_generator = ContentGenerationService()
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.video_generation_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
        self.task_query_url = "https://dashscope.aliyuncs.com/api/v1/tasks"
    
    def create_task_directory(self, recreation_id: int, base_video_path: str) -> str:
        """
        为任务创建独立的目录结构
        
        Args:
            recreation_id: 任务ID
            base_video_path: 原视频路径
            
        Returns:
            任务目录路径
        """
        try:
            # 获取原视频所在目录
            video_dir = os.path.dirname(base_video_path)
            
            # 创建任务目录
            task_dir = os.path.join(video_dir, f"recreation_{recreation_id}")
            os.makedirs(task_dir, exist_ok=True)
            
            # 创建子目录
            subdirs = ['audio', 'scripts', 'tts', 'videos', 'final']
            for subdir in subdirs:
                os.makedirs(os.path.join(task_dir, subdir), exist_ok=True)
            
            print(f"[目录管理] 任务目录创建完成: {task_dir}")
            return task_dir
            
        except Exception as e:
            print(f"[目录管理] 创建任务目录失败: {e}")
            raise e
    
    def update_recreation_step(self, recreation_id: int, step_data: Dict[str, Any]):
        """
        更新数据库中的二创步骤数据
        
        Args:
            recreation_id: 任务ID
            step_data: 步骤数据
        """
        try:
            recreation = VideoRecreation.query.get(recreation_id)
            if not recreation:
                raise Exception(f"任务 {recreation_id} 不存在")
            
            # 更新字段
            for key, value in step_data.items():
                if hasattr(recreation, key):
                    if isinstance(value, (dict, list)):
                        setattr(recreation, key, json.dumps(value, ensure_ascii=False))
                    else:
                        setattr(recreation, key, value)
            
            recreation.updated_at = datetime.now()
            db.session.commit()
            print(f"[数据库] 任务 {recreation_id} 数据更新完成")
            
        except Exception as e:
            db.session.rollback()
            print(f"[数据库] 更新任务 {recreation_id} 数据失败: {e}")
            raise e
    
    def log_step(self, recreation_id: int, step_name: str, status: str, message: str):
        """
        记录步骤日志
        
        Args:
            recreation_id: 任务ID
            step_name: 步骤名称
            status: 状态
            message: 消息
        """
        try:
            log = RecreationLog(
                recreation_id=recreation_id,
                step_name=step_name,
                log_level=status,
                message=message,
                created_at=datetime.now()
            )
            db.session.add(log)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"[日志] 记录步骤日志失败: {e}")
    
    def extract_and_transcribe_audio(self, video_path: str, recreation_id: int = None, task_dir: str = None) -> Dict[str, Any]:
        """
        提取视频音频并转录为文本
        
        Args:
            video_path: 视频文件路径
            recreation_id: 任务ID
            task_dir: 任务目录
            
        Returns:
            包含转录结果和音频路径的字典
        """
        try:
            print(f"[语音转录] 开始处理视频: {video_path}")
            
            # 确定音频文件路径
            if task_dir:
                audio_filename = os.path.splitext(os.path.basename(video_path))[0] + '.mp3'
                audio_path = os.path.join(task_dir, 'audio', audio_filename)
            else:
                audio_path = video_path.replace('.mp4', '.mp3')
            
            print(f"[语音转录] 音频文件路径: {audio_path}")
            
            # 如果音频文件不存在，从视频中提取
            if not os.path.exists(audio_path):
                print(f"[语音转录] 音频文件不存在，开始从视频中提取音频")
                from moviepy.editor import VideoFileClip
                video = VideoFileClip(video_path)
                video.audio.write_audiofile(audio_path)
                video.close()
                print(f"[语音转录] 音频提取完成")
            else:
                print(f"[语音转录] 音频文件已存在，跳过提取步骤")
            
            # 使用语音识别服务转录音频
            print(f"[语音转录] 开始语音识别")
            result = self.speech_recognizer.transcribe(audio_path)
            
            if result.get('success', False):
                transcription_text = result.get('text', '')
                text_length = len(transcription_text)
                print(f"[语音转录] 语音识别成功，文本长度: {text_length}")
                
                # 保存到数据库
                if recreation_id:
                    self.update_recreation_step(recreation_id, {
                        'audio_file_path': audio_path,
                        'transcription_text': transcription_text,
                        'transcription_service': 'SimpleSpeechRecognizer'
                    })
                    self.log_step(recreation_id, 'audio_transcription', 'success', f'语音转录完成，文本长度: {text_length}')
                
                return {
                    'success': True,
                    'text': transcription_text,
                    'audio_path': audio_path
                }
            else:
                error_msg = result.get('error', '未知错误')
                print(f"[语音转录] 语音转录失败: {error_msg}")
                
                if recreation_id:
                    self.log_step(recreation_id, 'audio_transcription', 'failed', f'语音转录失败: {error_msg}')
                
                return {
                    'success': False,
                    'error': error_msg,
                    'text': '',
                    'audio_path': audio_path
                }
                
        except Exception as e:
            error_msg = str(e)
            print(f"[语音转录] 提取和转录音频时发生错误: {error_msg}")
            
            if recreation_id:
                self.log_step(recreation_id, 'audio_transcription', 'failed', f'语音转录异常: {error_msg}')
            
            return {
                'success': False,
                'error': error_msg,
                'text': '',
                'audio_path': audio_path if 'audio_path' in locals() else ''
            }
    
    def generate_scene_prompts(self, video_path: str, video_understanding: Dict[str, Any], audio_transcription: str, recreation_id: int = None, task_dir: str = None) -> Dict[str, Any]:
        """
        生成场景提示词
        
        Args:
            video_path: 视频文件路径
            video_understanding: 视频理解结果
            audio_transcription: 音频转录结果（字符串）
            recreation_id: 任务ID
            task_dir: 任务目录
            
        Returns:
            场景分析和提示词生成结果
        """
        try:
            print(f"[场景分割] 开始生成场景提示词: {video_path}")
            
            # 提取视频理解内容和音频文本
            video_content = video_understanding.get('content', '') if video_understanding.get('success') else ''
            audio_text = audio_transcription  # 直接使用字符串，不需要.get()方法
            print(f"[场景分割] 视频理解内容长度: {len(video_content)}")
            print(f"[场景分割] 音频文本长度: {len(audio_text)}")
            
            # 使用场景分割服务进行智能场景分割
            print(f"[场景分割] 开始智能场景分割")
            scene_result = self.scene_segmenter.intelligent_scene_segmentation(
                video_path=video_path,
                video_understanding=video_content,
                audio_text=audio_text
            )
            
            if not scene_result.get('success'):
                print(f"[场景分割] 场景分割失败: {scene_result.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': scene_result.get('error', '场景分割失败'),
                    'scenes': []
                }
            
            scenes = scene_result.get('scenes', [])
            print(f"[场景分割] 场景分割成功，共获得{len(scenes)}个场景")
            print(f"场景分割成功，共 {len(scenes)} 个场景")
            
            # 为每个场景生成视频提示词
            enhanced_scenes = []
            for i, scene in enumerate(scenes):
                try:
                    print(f"为场景 {i+1} 生成视频提示词...")
                    
                    # 生成视频提示词 - 修正参数调用
                    prompt_result = self.scene_segmenter.generate_video_prompt_for_scene(
                        scene=scene,
                        video_understanding=video_content,
                        audio_text=audio_text,
                        scene_index=i
                    )
                    
                    # 将提示词结果添加到场景中
                    enhanced_scene = scene.copy()
                    enhanced_scene['video_prompt'] = prompt_result
                    enhanced_scenes.append(enhanced_scene)
                    
                    if prompt_result.get('success'):
                        print(f"场景 {i+1} 提示词生成成功")
                    else:
                        print(f"场景 {i+1} 提示词生成失败: {prompt_result.get('error', '未知错误')}")
                        
                except Exception as e:
                    print(f"场景 {i+1} 提示词生成时发生错误: {e}")
                    enhanced_scene = scene.copy()
                    enhanced_scene['video_prompt'] = {
                        'success': False,
                        'error': str(e),
                        'video_prompt': ''
                    }
                    enhanced_scenes.append(enhanced_scene)
            
            return {
                'success': True,
                'scenes': enhanced_scenes,
                'total_scenes': len(enhanced_scenes),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"生成场景提示词时发生错误: {e}")
            return {
                'success': False,
                'error': str(e),
                'scenes': [],
                'timestamp': datetime.now().isoformat()
            }
    
    def process_video_for_recreation(self, video_path: str, recreation_id: int) -> Dict[str, Any]:
        """
        完整的视频二创处理流程
        
        Args:
            video_path: 视频文件路径
            recreation_id: 任务ID
            
        Returns:
            包含所有处理结果的字典
        """
        try:
            print(f"开始处理视频: {video_path}，任务ID: {recreation_id}")
            
            # 创建任务目录
            task_dir = self.create_task_directory(recreation_id, video_path)
            
            # 步骤1: 视频内容理解
            print("步骤1: 视频内容理解...")
            self.log_step(recreation_id, 'video_understanding', 'processing', '开始视频内容理解')
            
            start_time = time.time()
            video_understanding = self.video_analyzer.understand_video_content_and_scenes(
                video_path=video_path,
                fps=10
            )
            understanding_time = time.time() - start_time
            
            if video_understanding.get('success'):
                # 保存视频理解结果到数据库
                self.update_recreation_step(recreation_id, {
                    'video_understanding': video_understanding.get('content', ''),
                    'understanding_model': 'VideoAnalysisAgent',
                    'understanding_time_cost': understanding_time
                })
                self.log_step(recreation_id, 'video_understanding', 'success', f'视频理解完成，耗时: {understanding_time:.2f}秒')
            else:
                error_msg = video_understanding.get('error', '视频理解失败')
                self.log_step(recreation_id, 'video_understanding', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤2: 语音转文本
            print("步骤2: 语音转文本...")
            self.log_step(recreation_id, 'audio_transcription', 'processing', '开始语音转文本')
            
            audio_result = self.extract_and_transcribe_audio(video_path, recreation_id, task_dir)
            if not audio_result.get('success'):
                raise Exception(f"语音转录失败: {audio_result.get('error')}")
            
            audio_transcription = audio_result.get('text', '')
            
            # 步骤3: 新文案创作
            print("步骤3: 新文案创作...")
            self.log_step(recreation_id, 'new_script_creation', 'processing', '开始新文案创作')
            
            new_script = self.content_generator.generate_new_script(
                video_understanding=video_understanding.get('content', ''),
                original_script=audio_transcription
            )
            
            if new_script.get('success'):
                self.update_recreation_step(recreation_id, {
                    'new_script_content': new_script.get('new_script', ''),
                    'script_generation_model': 'qwen-max'
                })
                self.log_step(recreation_id, 'new_script_creation', 'success', '新文案创作完成')
            else:
                error_msg = new_script.get('error', '新文案创作失败')
                self.log_step(recreation_id, 'new_script_creation', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤4: 智能场景分割和提示词生成
            print("步骤4: 智能场景分割和提示词生成...")
            self.log_step(recreation_id, 'scene_analysis', 'processing', '开始场景分析')
            
            scene_analysis = self.generate_scene_prompts(
                video_path=video_path,
                video_understanding=video_understanding,
                audio_transcription=audio_transcription,
                recreation_id=recreation_id,
                task_dir=task_dir
            )
            
            if scene_analysis.get('success'):
                self.log_step(recreation_id, 'scene_analysis', 'success', f'场景分析完成，共{len(scene_analysis.get("scenes", []))}个场景')
            else:
                error_msg = scene_analysis.get('error', '场景分析失败')
                self.log_step(recreation_id, 'scene_analysis', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤5: 文生视频
            print("步骤5: 文生视频...")
            self.log_step(recreation_id, 'video_generation', 'processing', '开始视频生成')
            
            video_generation_result = self.generate_videos_from_scenes(
                scene_analysis=scene_analysis,
                video_path=video_path,
                recreation_id=recreation_id,
                task_dir=task_dir
            )
            
            if video_generation_result.get('success'):
                self.log_step(recreation_id, 'video_generation', 'success', f'视频生成完成，成功: {video_generation_result.get("successful_count", 0)}')
            else:
                self.log_step(recreation_id, 'video_generation', 'failed', video_generation_result.get('error', '视频生成失败'))
            
            # 步骤6: 文本转语音
            print("步骤6: 文本转语音...")
            self.log_step(recreation_id, 'text_to_speech', 'processing', '开始文本转语音')
            
            tts_audio_path = os.path.join(task_dir, 'tts', 'tts_audio.mp3')
            os.makedirs(os.path.dirname(tts_audio_path), exist_ok=True)
            
            tts_result = self.content_generator.text_to_speech(
                text=new_script.get('new_script', ''),
                output_path=tts_audio_path
            )
            
            if tts_result.get('success'):
                self.update_recreation_step(recreation_id, {
                    'tts_audio_path': tts_result.get('audio_path'),
                    'tts_service': 'edge-tts',
                    'tts_voice_model': 'zh-CN-XiaoxiaoNeural',
                    'tts_audio_duration': tts_result.get('duration', 0)
                })
                self.log_step(recreation_id, 'text_to_speech', 'success', '文本转语音完成')
            else:
                error_msg = tts_result.get('error', '文本转语音失败')
                self.log_step(recreation_id, 'text_to_speech', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤7: 视频拼接
            print("步骤7: 视频拼接...")
            self.log_step(recreation_id, 'video_composition', 'processing', '开始视频拼接')
            
            # 获取所有成功生成的视频路径
            successful_videos = [v for v in video_generation_result.get('generated_videos', []) if v.get('success')]
            video_paths = [v.get('local_path') for v in successful_videos if v.get('local_path')]
            
            if video_paths:
                final_video_path = os.path.join(task_dir, 'final', 'final_video.mp4')
                os.makedirs(os.path.dirname(final_video_path), exist_ok=True)
                
                composition_result = self.content_generator.compose_videos(
                    video_paths=video_paths,
                    output_path=final_video_path
                )
                
                if composition_result.get('success'):
                    self.update_recreation_step(recreation_id, {
                        'final_video_path': composition_result.get('output_path'),
                        'composition_status': 'completed',
                        'total_duration': composition_result.get('duration', 0),
                        'final_file_size': composition_result.get('file_size', 0),
                        'video_resolution': composition_result.get('resolution', ''),
                        'video_fps': composition_result.get('fps', 0)
                    })
                    self.log_step(recreation_id, 'video_composition', 'success', '视频拼接完成')
                else:
                    error_msg = composition_result.get('error', '视频拼接失败')
                    self.log_step(recreation_id, 'video_composition', 'failed', error_msg)
                    raise Exception(error_msg)
            else:
                error_msg = '没有可用的视频进行拼接'
                self.log_step(recreation_id, 'video_composition', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤8: 音画同步
            print("步骤8: 音画同步...")
            self.log_step(recreation_id, 'audio_video_sync', 'processing', '开始音画同步')
            
            final_video_with_audio_path = os.path.join(task_dir, 'final', 'final_video_with_audio.mp4')
            sync_result = self.content_generator.sync_audio_video(
                video_path=composition_result.get('output_path'),
                audio_path=tts_result.get('audio_path'),
                output_path=final_video_with_audio_path
            )
            
            if sync_result.get('success'):
                self.update_recreation_step(recreation_id, {
                    'final_video_with_audio_path': sync_result.get('output_path')
                })
                self.log_step(recreation_id, 'audio_video_sync', 'success', '音画同步完成')
            else:
                error_msg = sync_result.get('error', '音画同步失败')
                self.log_step(recreation_id, 'audio_video_sync', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 更新任务状态为完成
            self.update_recreation_step(recreation_id, {
                'status': 'completed',
                'completed_at': datetime.now()
            })
            
            # 整合结果
            result = {
                'recreation_id': recreation_id,
                'task_dir': task_dir,
                'video_path': video_path,
                'video_understanding': video_understanding,
                'audio_transcription': audio_transcription,
                'new_script': new_script.get('new_script', ''),
                'scene_analysis': scene_analysis,
                'video_generation': video_generation_result,
                'tts_result': tts_result,
                'composition_result': composition_result,
                'sync_result': sync_result,
                'final_video_path': composition_result.get('output_path'),
                'final_video_with_audio_path': sync_result.get('output_path'),
                'processing_status': 'success'
            }
            
            # 保存结果到文件
            self.save_recreation_result(result, task_dir)
            
            print(f"视频二创处理完成! 任务ID: {recreation_id}")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"视频二创处理失败: {error_msg}")
            
            # 更新任务状态为失败
            try:
                self.update_recreation_step(recreation_id, {
                    'status': 'failed'
                })
                self.log_step(recreation_id, 'process_error', 'failed', error_msg)
            except:
                pass
            
            error_result = {
                'recreation_id': recreation_id,
                'video_path': video_path,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'processing_status': 'failed'
            }
            return error_result
    
    def generate_videos_from_scenes(self, scene_analysis: Dict[str, Any], video_path: str, recreation_id: int = None, task_dir: str = None) -> Dict[str, Any]:
        """
        根据场景分析结果生成视频
        
        Args:
            scene_analysis: 场景分析结果
            video_path: 原视频路径
            recreation_id: 任务ID
            task_dir: 任务目录
            
        Returns:
            视频生成结果
        """
        try:
            if not scene_analysis.get('success') or not scene_analysis.get('scenes'):
                return {
                    'success': False,
                    'error': '场景分析失败或无场景数据',
                    'generated_videos': []
                }
            
            # 确定视频输出目录
            if task_dir:
                produce_video_dir = os.path.join(task_dir, 'videos')
            else:
                video_dir = os.path.dirname(video_path)
                produce_video_dir = os.path.join(video_dir, 'produce_video')
            
            os.makedirs(produce_video_dir, exist_ok=True)
            print(f"[文生视频] 创建视频输出目录: {produce_video_dir}")
            
            generated_videos = []
            scenes = scene_analysis['scenes']
            
            print(f"[文生视频] 开始生成视频，共 {len(scenes)} 个场景")
            
            for i, scene in enumerate(scenes):
                try:
                    print(f"\n[文生视频] 开始生成场景 {i+1}/{len(scenes)} 的视频...")
                    
                    # 获取视频提示词
                    video_prompt_data = scene.get('video_prompt', {})
                    if not video_prompt_data.get('success'):
                        print(f"[文生视频] 场景 {i+1} 提示词生成失败，跳过")
                        continue
                    
                    prompt = video_prompt_data.get('video_prompt', '')
                    if not prompt:
                        print(f"[文生视频] 场景 {i+1} 提示词为空，跳过")
                        continue
                    
                    print(f"[文生视频] 场景 {i+1} 提示词: {prompt[:100]}...")
                    
                    # 创建视频生成任务
                    print(f"[文生视频] 调用视频生成服务")
                    task_result = self.create_video_generation_task(prompt)
                    if not task_result['success']:
                        print(f"[文生视频] 场景 {i+1} 任务创建失败: {task_result['error']}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': task_result['error'],
                            'prompt': prompt
                        })
                        continue
                    
                    task_id = task_result['task_id']
                    print(f"[文生视频] 场景 {i+1} 任务创建成功，任务ID: {task_id}")
                    
                    # 等待五分钟
                    # time.sleep(300)
                    # 等待任务完成并获取结果
                    video_result = self.wait_for_video_generation(task_id, max_wait_time=600)  # 最多等待10分钟
                    
                    if video_result['success']:
                        # 下载视频
                        video_url = video_result['video_url']
                        local_video_path = os.path.join(produce_video_dir, f"scene_{i+1:02d}_{scene.get('scene_id', i+1)}.mp4")
                        
                        download_result = self.download_video(video_url, local_video_path)
                        
                        if download_result['success']:
                            print(f"[文生视频] 场景 {i+1} 视频生成并下载成功: {local_video_path}")
                            generated_videos.append({
                                'scene_index': i,
                                'scene_id': scene.get('scene_id', i+1),
                                'success': True,
                                'task_id': task_id,
                                'video_url': video_url,
                                'local_path': local_video_path,
                                'prompt': prompt,
                                'duration': scene.get('duration', 0),
                                'start_time': scene.get('start_time', 0),
                                'end_time': scene.get('end_time', 0)
                            })
                        else:
                            print(f"[文生视频] 场景 {i+1} 视频下载失败: {download_result['error']}")
                            generated_videos.append({
                                'scene_index': i,
                                'scene_id': scene.get('scene_id', i+1),
                                'success': False,
                                'error': f"下载失败: {download_result['error']}",
                                'task_id': task_id,
                                'video_url': video_url,
                                'prompt': prompt
                            })
                    else:
                        print(f"[文生视频] 场景 {i+1} 视频生成失败: {video_result['error']}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': video_result['error'],
                            'task_id': task_id,
                            'prompt': prompt
                        })
                    
                    # 添加延迟避免请求过于频繁
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"[文生视频] 场景 {i+1} 处理异常: {e}")
                    generated_videos.append({
                        'scene_index': i,
                        'scene_id': scene.get('scene_id', i+1),
                        'success': False,
                        'error': str(e),
                        'prompt': scene.get('video_prompt', {}).get('video_prompt', '')
                    })
            
            # 统计结果
            successful_videos = [v for v in generated_videos if v['success']]
            failed_videos = [v for v in generated_videos if not v['success']]
            
            result = {
                'success': len(successful_videos) > 0,
                'total_scenes': len(scenes),
                'successful_count': len(successful_videos),
                'failed_count': len(failed_videos),
                'output_directory': produce_video_dir,
                'generated_videos': generated_videos
            }
            
            print(f"\n[文生视频] 视频生成完成! 成功: {len(successful_videos)}, 失败: {len(failed_videos)}")
            return result
            
        except Exception as e:
            print(f"[文生视频] 视频生成过程异常: {e}")
            return {
                'success': False,
                'error': str(e),
                'generated_videos': []
            }
    
    def create_video_generation_task(self, prompt: str) -> Dict[str, Any]:
        """
        创建视频生成任务
        
        Args:
            prompt: 视频生成提示词
            
        Returns:
            任务创建结果
        """
        try:
            headers = {
                'X-DashScope-Async': 'enable',
                'Authorization': f'Bearer sk-039090af18474073b5f6ec283e544685',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'wanx2.1-t2v-turbo',
                'input': {
                    'prompt': prompt
                },
                'parameters': {
                    'size': '1280*720'
                }
            }
            
            response = requests.post(
                self.video_generation_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'output' in result and 'task_id' in result['output']:
                    return {
                        'success': True,
                        'task_id': result['output']['task_id'],
                        'response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': f"响应格式错误: {result}"
                    }
            else:
                return {
                    'success': False,
                    'error': f"API调用失败: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def wait_for_video_generation(self, task_id: str, max_wait_time: int = 600) -> Dict[str, Any]:
        """
        等待视频生成完成
        
        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒）
            
        Returns:
            视频生成结果
        """
        try:
            headers = {
                'Authorization': f'Bearer sk-039090af18474073b5f6ec283e544685'
            }
            
            start_time = time.time()
            check_interval = 30  # 每30秒检查一次
            
            print(f"[视频等待] 开始等待任务 {task_id} 完成，最大等待时间: {max_wait_time} 秒")
            
            while time.time() - start_time < max_wait_time:
                print(f"[视频等待] 检查任务 {task_id} 状态")
                response = requests.get(
                    f"{self.task_query_url}/{task_id}",
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if 'output' in result:
                        task_status = result['output'].get('task_status')
                        print(f"[视频等待] 任务 {task_id} 状态: {task_status}")
                        
                        if task_status == 'SUCCEEDED':
                            video_url = result['output'].get('video_url')
                            if video_url:
                                print(f"[视频等待] 任务 {task_id} 完成，获取到视频URL")
                                return {
                                    'success': True,
                                    'task_status': task_status,
                                    'video_url': video_url,
                                    'response': result
                                }
                            else:
                                return {
                                    'success': False,
                                    'error': '任务成功但未获取到视频URL'
                                }
                        
                        elif task_status == 'FAILED':
                            print(f"[视频等待] 任务 {task_id} 失败")
                            return {
                                'success': False,
                                'error': f"任务失败: {result.get('message', '未知错误')}"
                            }
                        
                        elif task_status in ['PENDING', 'RUNNING']:
                            elapsed_time = int(time.time() - start_time)
                            print(f"[视频等待] 任务 {task_id} 状态: {task_status}, 已等待: {elapsed_time}秒")
                            time.sleep(check_interval)
                            continue
                        
                        else:
                            return {
                                'success': False,
                                'error': f"未知任务状态: {task_status}"
                            }
                    else:
                        return {
                            'success': False,
                            'error': f"响应格式错误: {result}"
                        }
                else:
                    print(f"[视频等待] 查询任务状态失败: {response.status_code} - {response.text}")
                    time.sleep(check_interval)
            
            print(f"[视频等待] 任务 {task_id} 超时")
            return {
                'success': False,
                'error': f"任务超时，等待时间超过 {max_wait_time} 秒"
            }
            
        except Exception as e:
            print(f"[视频等待] 等待视频生成时发生错误: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_video(self, video_url: str, local_path: str) -> Dict[str, Any]:
        """
        下载视频到本地
        
        Args:
            video_url: 视频URL
            local_path: 本地保存路径
            
        Returns:
            下载结果
        """
        try:
            print(f"[视频下载] 开始下载视频: {video_url}")
            print(f"[视频下载] 保存路径: {local_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            print(f"[视频下载] 目录创建完成")
            
            # 下载视频
            print(f"[视频下载] 开始HTTP请求")
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            print(f"[视频下载] HTTP请求成功，开始写入文件")
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"[视频下载] 文件写入完成")
            
            # 验证文件是否下载成功
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                file_size = os.path.getsize(local_path)
                print(f"[视频下载] 视频下载成功: {local_path}，文件大小: {file_size} 字节")
                return {
                    'success': True,
                    'local_path': local_path
                }
            else:
                print(f"[视频下载] 下载的文件为空或不存在")
                return {
                    'success': False,
                    'error': '下载的文件为空或不存在'
                }
                
        except Exception as e:
            print(f"[视频下载] 下载视频失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_recreation_result(self, result: Dict[str, Any], task_dir: str = None):
        """
        保存二创结果到文件
        
        Args:
            result: 处理结果
            task_dir: 任务目录
        """
        try:
            # 确定结果保存目录
            if task_dir:
                results_dir = task_dir
                result_file = os.path.join(results_dir, 'recreation_result.json')
            else:
                results_dir = os.path.join(os.path.dirname(result['video_path']), 'recreation_results')
                os.makedirs(results_dir, exist_ok=True)
                video_name = os.path.splitext(os.path.basename(result['video_path']))[0]
                result_file = os.path.join(results_dir, f"{video_name}_recreation.json")
            
            # 保存结果
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"结果已保存到: {result_file}")
            
        except Exception as e:
            print(f"保存结果失败: {e}")
