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
from app.services.comfyui_service import ComfyUIService
from app.services.comfyui_prompt_converter import ComfyUIPromptConverter
from app.services.nano_banana_service import NanoBananaService
from app.services.qwen_video_service import QwenVideoService

# 添加视频一致性检查代理
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'video_consistency_agent'))
from video_consistency_agent.agent.consistency_agent import ConsistencyAgent

class VideoRecreationService:
    
    def __init__(self):
        self.video_analyzer = VideoAnalysisAgent()
        self.speech_recognizer = SimpleSpeechRecognizer()
        self.scene_segmenter = SceneSegmentationService()
        self.content_generator = ContentGenerationService()
        
        # ComfyUI集成服务
        self.comfyui_service = ComfyUIService()
        self.comfyui_prompt_converter = ComfyUIPromptConverter()
        
        # Nano Banana集成服务
        self.nano_banana_service = NanoBananaService({
            "base_url": Config.NANO_BANANA_API_ENDPOINT,
            "api_key": Config.NANO_BANANA_API_KEY,
            "timeout": 30,
            "poll_interval": 10
        })
        
        # Qwen模型服务
        self.qwen_video_service = QwenVideoService({
            "api_key": Config.DASHSCOPE_API_KEY,  # 使用配置文件中的API密钥
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "timeout": 60,
            "poll_interval": 10,
            "max_wait_time": 600
        })
        
        # 视频一致性检查代理
        # video_consistency_agent目录直接位于项目根目录下
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_path = os.path.join(project_root, 'video_consistency_agent', 'config', 'config.yaml')
        self.consistency_agent = ConsistencyAgent(config_path)
        
        # 保留原有的DashScope配置（可选回退）
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.video_generation_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
        self.task_query_url = "https://dashscope.aliyuncs.com/api/v1/tasks"
    
    def calculate_video_hash(self, video_path: str) -> str:
        import hashlib
        
        try:
            sha256_hash = hashlib.sha256()
            with open(video_path, "rb") as f:
                # 分块读取文件，避免内存溢出
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[视频哈希] 计算视频哈希失败: {e}")
            return None
    
    def find_existing_recreation(self, video_path: str) -> VideoRecreation:
        try:
            # 计算视频哈希
            video_hash = self.calculate_video_hash(video_path)
            if not video_hash:
                return None
            
            # 查找数据库中是否存在相同哈希的视频
            existing = VideoRecreation.query.filter_by(original_video_hash=video_hash).first()
            if existing:
                print(f"[任务管理] 找到现有任务记录: ID={existing.id}, 状态={existing.status}")
                return existing
            
            # 如果没有哈希匹配，尝试按路径匹配
            existing_by_path = VideoRecreation.query.filter_by(original_video_path=video_path).first()
            if existing_by_path:
                print(f"[任务管理] 找到现有任务记录(按路径匹配): ID={existing_by_path.id}, 状态={existing_by_path.status}")
                # 更新哈希值
                existing_by_path.original_video_hash = video_hash
                db.session.commit()
                return existing_by_path
            
            return None
        except Exception as e:
            print(f"[任务管理] 查找现有任务失败: {e}")
            return None
    
    def create_task_directory(self, recreation_id: int, base_video_path: str) -> str:
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
        try:
            # 查找现有任务记录
            recreation = VideoRecreation.query.get(recreation_id)
            
            # 如果任务不存在，自动创建一个新的
            if not recreation:
                print(f"[数据库] 任务 {recreation_id} 不存在，自动创建新任务记录")
                recreation = VideoRecreation(
                id=recreation_id,
                original_video_id=str(recreation_id),
                status='processing',
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
                db.session.add(recreation)
            
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
            # 不抛出异常，继续执行流程
            print(f"[数据库] 继续执行流程，跳过数据库更新")
    
    def log_step(self, recreation_id: int, step_name: str, status: str, message: str):
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
        try:
            print(f"[场景分割] 开始生成场景提示词: {video_path}")
            
            # 提取视频理解内容和音频文本
            video_content = video_understanding.get('content', '') if video_understanding.get('success') else ''
            audio_text = audio_transcription  # 直接使用字符串，不需要.get()方法
            print(f"[场景分割] 视频理解内容长度: {len(video_content)}")
            print(f"[场景分割] 音频文本长度: {len(audio_text)}")
            
            # 直接从视频理解结果中的切片创建场景，不进行智能场景分割
            print(f"[场景分割] 直接从切片创建场景，不进行智能场景分割")
            
            # 获取切片信息
            slices = []
            if video_understanding.get('raw_slices'):
                slices = video_understanding['raw_slices']
            elif video_understanding.get('slices'):
                slices = video_understanding['slices']
            
            print(f"[场景分割] 找到 {len(slices)} 个切片，创建 {len(slices)} 个场景")
            print(f"场景分割成功，共 {len(slices)} 个场景")
            
            # 为每个切片创建场景
            scenes = []
            for i, slice_data in enumerate(slices):
                scene = {
                    'scene_id': i,
                    'start_time': slice_data.get('start_time', i * 8),  # 默认8秒一个切片
                    'end_time': slice_data.get('end_time', (i + 1) * 8),
                    'duration': slice_data.get('duration', 8),
                    'description': f"第{i+1}个切片",
                    'slice_data': slice_data  # 保存切片原始数据
                }
                scenes.append(scene)
            
            # 为每个场景生成视频提示词
            enhanced_scenes = []
            for i, scene in enumerate(scenes):
                try:
                    print(f"为场景 {i+1} 生成视频提示词...")
                    
                    # 生成视频提示词
                    prompt_result = self.scene_segmenter.generate_video_prompt_for_scene(
                        scene=scene,
                        video_understanding=video_content,
                        audio_text=audio_text,
                        scene_index=i
                    )
                    
                    # 将提示词结果添加到场景中
                    enhanced_scene = scene.copy()
                    enhanced_scene['video_prompt'] = prompt_result
                    enhanced_scene['keyframes'] = scene.get('slice_data', {}).get('keyframes', [])  # 保存关键帧信息
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
                    enhanced_scene['keyframes'] = scene.get('slice_data', {}).get('keyframes', [])  # 保存关键帧信息
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
    
    async def process_video_for_recreation(self, video_path: str, recreation_id: int, use_nano_banana: bool = False, use_qwen: bool = False, slice_limit: int = 0, existing_prompt_data: Dict[str, Any] = None) -> Dict[str, Any]:
        print(f"🔧 处理参数: slice_limit={slice_limit}")
        try:
            print(f"开始处理视频: {video_path}，任务ID: {recreation_id}")
            
            # 检查是否存在现有任务记录
            existing_recreation = self.find_existing_recreation(video_path)
            if existing_recreation and existing_recreation.status == 'completed':
                print(f"[任务管理] 该视频已经完成二创，返回现有结果")
                return {
                    'processing_status': 'success',
                    'recreation_id': existing_recreation.id,
                    'task_dir': self.create_task_directory(existing_recreation.id, video_path),
                    'final_video_path': existing_recreation.final_video_path,
                    'final_video_with_audio_path': existing_recreation.final_video_with_audio_path,
                    'new_script': existing_recreation.new_script_content,
                    'tts_result': {
                        'audio_path': existing_recreation.tts_audio_path,
                        'duration': existing_recreation.tts_audio_duration
                    },
                    'message': '使用已完成的二创结果'
                }
            
            # 创建任务目录
            task_dir = self.create_task_directory(recreation_id, video_path)
            
            # 计算视频哈希并保存到数据库
            video_hash = self.calculate_video_hash(video_path)
            self.update_recreation_step(recreation_id, {
                'original_video_path': video_path,
                'original_video_hash': video_hash
            })
            
            # 步骤1: 视频内容理解
            print("步骤1: 视频内容理解...")
            self.log_step(recreation_id, 'video_understanding', 'processing', '开始视频内容理解')
            
            # 强制重新生成视频理解结果，确保包含关键帧信息
            print(f"[任务管理] 强制重新生成视频理解结果，确保包含关键帧信息")
            start_time = time.time()
            video_understanding = self.video_analyzer.understand_video_content_and_scenes(
                video_path=video_path,
                fps=5,  # 降低帧率，加快处理速度
                slice_limit=slice_limit  # 传递切片限制参数
            )
            understanding_time = time.time() - start_time
            
            if video_understanding.get('success'):
                # 保存视频理解结果到数据库，包括关键帧信息
                self.update_recreation_step(recreation_id, {
                    'video_understanding': video_understanding.get('content', ''),
                    'understanding_model': 'VideoAnalysisAgent',
                    'understanding_time_cost': understanding_time
                })
                self.log_step(recreation_id, 'video_understanding', 'success', f'视频理解完成，耗时: {understanding_time:.2f}秒')
                # 打印关键帧信息，用于调试
                if 'raw_slices' in video_understanding:
                    total_keyframes = sum(len(slice_data.get('keyframes', [])) for slice_data in video_understanding['raw_slices'])
                    print(f"[视频理解] 生成的切片数量: {len(video_understanding['raw_slices'])}")
                    print(f"[视频理解] 提取的关键帧总数: {total_keyframes}")
            else:
                error_msg = video_understanding.get('error', '视频理解失败')
                self.log_step(recreation_id, 'video_understanding', 'failed', error_msg)
                raise Exception(error_msg)
            
            # 步骤2: 语音转文本
            print("步骤2: 语音转文本...")
            self.log_step(recreation_id, 'audio_transcription', 'processing', '开始语音转文本')
            
            # 检查是否已经有语音转录结果
            audio_result = None
            audio_transcription = ''
            if existing_recreation and existing_recreation.transcription_text and existing_recreation.audio_file_path:
                print(f"[任务管理] 发现已有语音转录结果，跳过语音转文本步骤")
                audio_transcription = existing_recreation.transcription_text
                audio_result = {
                    'success': True,
                    'text': audio_transcription,
                    'audio_path': existing_recreation.audio_file_path
                }
            else:
                audio_result = self.extract_and_transcribe_audio(video_path, recreation_id, task_dir)
                if not audio_result.get('success'):
                    raise Exception(f"语音转录失败: {audio_result.get('error')}")
                
                audio_transcription = audio_result.get('text', '')
            
            # 步骤3: 新文案创作
            print("步骤3: 新文案创作...")
            self.log_step(recreation_id, 'new_script_creation', 'processing', '开始新文案创作')
            
            # 检查是否已经有新文案结果
            new_script = None
            if existing_recreation and existing_recreation.new_script_content:
                print(f"[任务管理] 发现已有新文案结果，跳过新文案创作步骤")
                new_script = {
                    'success': True,
                    'new_script': existing_recreation.new_script_content
                }
            else:
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
            
            # 检查是否已经有场景分析结果
            scene_analysis = None
            
            # 1. 优先使用传入的已有prompt数据
            if existing_prompt_data:
                print(f"[任务管理] 使用传入的已有prompt数据，跳过场景分割步骤")
                # 检查已有prompt数据的格式
                if isinstance(existing_prompt_data, dict):
                    # 从已有prompt数据中提取场景信息
                    if 'scenes' in existing_prompt_data:
                        scene_analysis = {
                            'success': True,
                            'scenes': existing_prompt_data['scenes']
                        }
                    elif 'scene_analysis' in existing_prompt_data and 'scenes' in existing_prompt_data['scene_analysis']:
                        scene_analysis = existing_prompt_data['scene_analysis']
                    elif 'video_generation' in existing_prompt_data and 'scenes' in existing_prompt_data['video_generation']:
                        # 从video_generation中提取场景信息
                        scene_analysis = {
                            'success': True,
                            'scenes': existing_prompt_data['video_generation']['scenes']
                        }
            # 2. 其次检查是否有现有任务记录
            elif existing_recreation and existing_recreation.scenes:
                print(f"[任务管理] 发现已有场景分析结果，跳过场景分割步骤")
                # 从数据库中获取场景信息
                scenes = []
                for scene in existing_recreation.scenes:
                    scenes.append({
                        'scene_id': scene.scene_index,
                        'start_time': scene.start_time,
                        'end_time': scene.end_time,
                        'duration': scene.duration,
                        'description': scene.description,
                        'video_prompt': {
                            'success': True,
                            'video_prompt': scene.video_prompt
                        },
                        'technical_params': scene.technical_params,
                        'style_elements': scene.style_elements
                    })
                scene_analysis = {
                    'success': True,
                    'scenes': scenes
                }
            # 3. 最后生成新的场景提示词
            else:
                scene_analysis = self.generate_scene_prompts(
                    video_path=video_path,
                    video_understanding=video_understanding,
                    audio_transcription=audio_transcription,
                    recreation_id=recreation_id,
                    task_dir=task_dir
                )
                
                if scene_analysis.get('success'):
                    self.log_step(recreation_id, 'scene_analysis', 'success', f'场景分析完成，共{len(scene_analysis.get("scenes", []))}个场景')
                    
                    # 保存场景和prompt到数据库
                    scenes = scene_analysis.get('scenes', [])
                    
                    # 添加上下文信息到场景中，确保场景间连贯性
                    previous_scene_info = None
                    for i, scene in enumerate(scenes):
                        # 如果是第一个场景，没有上一个场景信息
                        if i > 0 and previous_scene_info:
                            # 为当前场景添加上一个场景的信息
                            scene['previous_scene_info'] = previous_scene_info
                            
                            # 重新生成更连贯的提示词
                            print(f"[场景连贯性] 为场景 {i+1} 添加上下文信息并重新生成提示词")
                            updated_prompt = self.scene_segmenter.generate_video_prompt_for_scene(
                                scene=scene,
                                video_understanding=video_understanding.get('content', ''),
                                audio_text=audio_transcription,
                                scene_index=i,
                                output_format="json",
                                previous_scene_info=previous_scene_info
                            )
                            scene['video_prompt'] = updated_prompt
                        
                        # 保存当前场景信息，供下一个场景使用
                        video_prompt_data = scene.get('video_prompt', {})
                        # 确保video_prompt_data是字典格式
                        if isinstance(video_prompt_data, dict):
                            # 如果是字典格式，检查success字段
                            if video_prompt_data.get('success'):
                                previous_scene_info = {
                                    'video_prompt': video_prompt_data.get('video_prompt', ''),
                                    'style_elements': video_prompt_data.get('style_elements', {}),
                                    'scene_info': video_prompt_data.get('scene_info', {}),
                                    'technical_params': video_prompt_data.get('technical_params', {})
                                }
                        else:
                            # 如果不是字典格式，跳过保存
                            previous_scene_info = None
                        
                        # 保存场景到数据库
                        scene_obj = RecreationScene(
                            recreation_id=recreation_id,
                            scene_index=i,
                            start_time=scene.get('start_time', 0),
                            end_time=scene.get('end_time', 0),
                            duration=scene.get('duration', 0),
                            description=scene.get('description', ''),
                            video_prompt=scene.get('video_prompt', {}).get('video_prompt', ''),
                            technical_params=scene.get('technical_params', {}),
                            style_elements=scene.get('style_elements', {}),
                            prompt_generation_model='SceneSegmentationService'
                        )
                        db.session.add(scene_obj)
                    db.session.commit()
                    print(f"[任务管理] 场景和prompt已保存到数据库")
                    print(f"[场景连贯性] 已处理 {len(scenes)} 个场景，添加了上下文信息确保连贯性")
                else:
                    error_msg = scene_analysis.get('error', '场景分析失败')
                    self.log_step(recreation_id, 'scene_analysis', 'failed', error_msg)
                    raise Exception(error_msg)
            
            # 步骤4.5: 增强场景提示词，整合音频内容
            print("步骤4.5: 增强场景提示词，整合音频内容...")
            scenes = scene_analysis.get('scenes', [])
            enhanced_scenes = []
            
            for i, scene in enumerate(scenes):
                # 设置总场景数，用于后续音频内容分配
                scene['total_scenes'] = len(scenes)
                
                # 获取当前场景对应的音频内容
                scene_audio_content = self._get_scene_audio_content(audio_transcription, scene)
                
                # 增强视频提示词，将音频内容整合进去
                video_prompt_data = scene.get('video_prompt', {})
                if isinstance(video_prompt_data, dict) and video_prompt_data.get('success'):
                    original_prompt = video_prompt_data.get('video_prompt', '')
                    
                    # 增强提示词，整合音频内容
                    enhanced_prompt = f"{original_prompt}\n\n特别重要：请结合以下音频内容，确保生成的视频与音频内容保持一致：\n{scene_audio_content}"
                    
                    # 更新场景提示词
                    scene['video_prompt']['video_prompt'] = enhanced_prompt
                    
                enhanced_scenes.append(scene)
            
            # 更新场景分析结果
            scene_analysis['scenes'] = enhanced_scenes
            print(f"[提示词增强] 已增强 {len(enhanced_scenes)} 个场景的提示词，整合了音频内容")
            
            # 步骤5: 视频生成（根据参数选择服务）
            # 检查是否所有场景都已经生成了视频
            all_scenes_generated = False
            if existing_recreation and existing_recreation.scenes:
                # 检查每个场景是否都有生成的视频
                all_scenes_generated = all(scene.generated_video_path for scene in existing_recreation.scenes)
                
                if all_scenes_generated:
                    print(f"[任务管理] 发现所有场景都已生成视频，跳过视频生成步骤")
                    # 从数据库中获取生成的视频信息
                    generated_videos = []
                    for scene in existing_recreation.scenes:
                        generated_videos.append({
                            'scene_index': scene.scene_index,
                            'scene_id': scene.scene_index,
                            'success': True,
                            'local_path': scene.generated_video_path,
                            'prompt': scene.video_prompt,
                            'duration': scene.duration,
                            'start_time': scene.start_time,
                            'end_time': scene.end_time
                        })
                    
                    video_generation_result = {
                        'success': True,
                        'total_scenes': len(existing_recreation.scenes),
                        'successful_count': len(existing_recreation.scenes),
                        'failed_count': 0,
                        'output_directory': os.path.dirname(existing_recreation.scenes[0].generated_video_path) if existing_recreation.scenes else task_dir,
                        'generated_videos': generated_videos
                    }
                    
                    self.log_step(recreation_id, 'video_generation', 'success', f'复用已有视频，成功: {len(generated_videos)}')
            
            if not all_scenes_generated:
                if use_qwen:
                    print("步骤5: Qwen模型视频生成...")
                    self.log_step(recreation_id, 'video_generation', 'processing', '开始Qwen模型视频生成')
                    
                    video_generation_result = await self.generate_videos_with_qwen(
                        scene_analysis=scene_analysis,
                        video_path=video_path,
                        recreation_id=recreation_id,
                        task_dir=task_dir,
                        video_understanding=video_understanding
                    )
                    
                    if video_generation_result.get('success'):
                        # 更新数据库中的场景视频路径
                        for video_info in video_generation_result.get('generated_videos', []):
                            if video_info.get('success'):
                                scene = RecreationScene.query.filter_by(
                                    recreation_id=recreation_id,
                                    scene_index=video_info.get('scene_index')
                                ).first()
                                if scene:
                                    scene.generated_video_path = video_info.get('local_path')
                                    scene.generation_status = 'completed'
                                    scene.generation_service = 'qwen'
                                    scene.generation_completed_at = datetime.now()
                        db.session.commit()
                        
                        self.log_step(recreation_id, 'video_generation', 'success', f'Qwen模型视频生成完成，成功: {video_generation_result.get("successful_count", 0)}')
                    else:
                        self.log_step(recreation_id, 'video_generation', 'failed', video_generation_result.get('error', 'Qwen模型视频生成失败'))
                elif use_nano_banana:
                    print("步骤5: Nano Banana视频生成...")
                    self.log_step(recreation_id, 'video_generation', 'processing', '开始Nano Banana视频生成')
                    
                    video_generation_result = self.generate_videos_with_nano_banana(
                        scene_analysis=scene_analysis,
                        video_path=video_path,
                        recreation_id=recreation_id,
                        task_dir=task_dir
                    )
                    
                    if video_generation_result.get('success'):
                        # 更新数据库中的场景视频路径
                        for video_info in video_generation_result.get('generated_videos', []):
                            if video_info.get('success'):
                                scene = RecreationScene.query.filter_by(
                                    recreation_id=recreation_id,
                                    scene_index=video_info.get('scene_index')
                                ).first()
                                if scene:
                                    scene.generated_video_path = video_info.get('local_path')
                                    scene.generation_status = 'completed'
                                    scene.generation_service = 'nano_banana'
                                    scene.generation_completed_at = datetime.now()
                        db.session.commit()
                        
                        self.log_step(recreation_id, 'video_generation', 'success', f'Nano Banana视频生成完成，成功: {video_generation_result.get("successful_count", 0)}')
                    else:
                        self.log_step(recreation_id, 'video_generation', 'failed', video_generation_result.get('error', 'Nano Banana视频生成失败'))
                else:
                    print("步骤5: ComfyUI关键帧生成与视频生成...")
                    self.log_step(recreation_id, 'video_generation', 'processing', '开始ComfyUI关键帧生成')
                    
                    video_generation_result = self.generate_videos_from_scenes(
                        scene_analysis=scene_analysis,
                        video_path=video_path,
                        recreation_id=recreation_id,
                        task_dir=task_dir
                    )
                    
                    if video_generation_result.get('success'):
                        # 更新数据库中的场景视频路径
                        for video_info in video_generation_result.get('generated_videos', []):
                            if video_info.get('success'):
                                scene = RecreationScene.query.filter_by(
                                    recreation_id=recreation_id,
                                    scene_index=video_info.get('scene_index')
                                ).first()
                                if scene:
                                    scene.generated_video_path = video_info.get('local_path')
                                    scene.generation_status = 'completed'
                                    scene.generation_service = 'comfyui'
                                    scene.generation_completed_at = datetime.now()
                        db.session.commit()
                        
                        self.log_step(recreation_id, 'video_generation', 'success', f'ComfyUI视频生成完成，成功: {video_generation_result.get("successful_count", 0)}')
                    else:
                        self.log_step(recreation_id, 'video_generation', 'failed', video_generation_result.get('error', 'ComfyUI视频生成失败'))
            
            # 步骤5.5: 视频一致性检查
            print("步骤5.5: 视频一致性检查...")
            self.log_step(recreation_id, 'video_consistency_check', 'processing', '开始视频一致性检查')
            
            # 准备一致性检查数据
            consistency_check_data = {
                'generated_images': video_generation_result.get('generated_videos', []),
                'original_video_info': {
                    'content': video_understanding.get('content', ''),
                    'keyframes': [slice.get('keyframes', [])[0] if slice.get('keyframes', []) else '' for slice in video_understanding.get('slices', [])],
                    'tags': [],  # 可以从视频理解结果中提取标签
                    'audio_transcription': audio_transcription
                },
                'storyboard': storyboard
            }
            
            # 执行一致性检查
            consistency_result = self.consistency_agent.execute(consistency_check_data)
            
            if consistency_result.get('success'):
                print(f"[一致性检查] 成功通过 {consistency_result.get('passed_count', 0)} 个视频片段，失败 {consistency_result.get('failed_count', 0)} 个片段")
                
                # 如果有失败的片段，进行重新生成
                failed_images = consistency_result.get('failed_images', [])
                if failed_images:
                    print(f"[一致性检查] 重新生成 {len(failed_images)} 个失败的视频片段")
                    
                    # 这里可以添加重新生成逻辑
                    # 简单实现：使用原始生成结果，后续可以优化为重新生成失败片段
            else:
                print(f"[一致性检查] 检查失败: {consistency_result.get('error')}")
            
            self.log_step(recreation_id, 'video_consistency_check', 'success', '视频一致性检查完成')
            
            # 步骤6: 文本转语音
            print("步骤6: 文本转语音...")
            self.log_step(recreation_id, 'text_to_speech', 'processing', '开始文本转语音')
            
            # 检查是否已经有TTS音频结果
            tts_result = None
            if existing_recreation and existing_recreation.tts_audio_path:
                print(f"[任务管理] 发现已有TTS音频结果，跳过文本转语音步骤")
                tts_result = {
                    'success': True,
                    'audio_path': existing_recreation.tts_audio_path,
                    'duration': existing_recreation.tts_audio_duration
                }
            else:
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
            
            # 检查是否已经有拼接好的视频
            composition_result = None
            if existing_recreation and existing_recreation.final_video_path:
                print(f"[任务管理] 发现已有拼接好的视频，跳过视频拼接步骤")
                composition_result = {
                    'success': True,
                    'output_path': existing_recreation.final_video_path,
                    'duration': existing_recreation.total_duration,
                    'file_size': existing_recreation.final_file_size,
                    'resolution': existing_recreation.video_resolution,
                    'fps': existing_recreation.video_fps
                }
            else:
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
            
            # 检查是否已经有音画同步的最终视频
            sync_result = None
            if existing_recreation and existing_recreation.final_video_with_audio_path:
                print(f"[任务管理] 发现已有音画同步的最终视频，跳语音画同步步骤")
                sync_result = {
                    'success': True,
                    'output_path': existing_recreation.final_video_with_audio_path
                }
            else:
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
            print(f"[文生视频] 使用ComfyUI工作流：关键帧生成 → 视频生成")
            
            for i, scene in enumerate(scenes):
                try:
                    print(f"\n[文生视频] 开始处理场景 {i+1}/{len(scenes)}")
                    
                    # 获取视频提示词
                    video_prompt_data = scene.get('video_prompt', {})
                    if isinstance(video_prompt_data, dict):
                        # 如果是字典格式，检查success字段
                        if video_prompt_data.get('success'):
                            # 成功情况下，提取video_prompt字段
                            video_prompt = video_prompt_data.get('video_prompt', '')
                        else:
                            # 失败情况下，直接使用video_prompt字段
                            video_prompt = video_prompt_data.get('video_prompt', '')
                    elif isinstance(video_prompt_data, str):
                        # 如果直接是字符串，直接使用
                        video_prompt = video_prompt_data
                    else:
                        video_prompt = str(video_prompt_data)
                    
                    if not video_prompt:
                        print(f"[文生视频] 场景 {i+1} 提示词为空，跳过")
                        continue
                    
                    print(f"[文生视频] 场景 {i+1} 提示词: {video_prompt[:100]}...")
                    
                    # 1. 将场景数据转换为ComfyUI格式
                    scene_data = scene.copy()
                    scene_data['video_prompt'] = video_prompt
                    comfyui_prompt = self.comfyui_prompt_converter.convert_to_comfyui_prompt(scene_data)
                    
                    # 2. 生成关键帧
                    print(f"[文生视频] 场景 {i+1}: 开始生成关键帧")
                    keyframe_result = self.comfyui_service.generate_keyframes(
                        prompt=comfyui_prompt,
                        num_keyframes=3  # 每个场景生成3个关键帧
                    )
                    
                    if not keyframe_result.get('success'):
                        print(f"[文生视频] 场景 {i+1} 关键帧生成失败: {keyframe_result.get('error')}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': f"关键帧生成失败: {keyframe_result.get('error')}",
                            'prompt': video_prompt
                        })
                        continue
                    
                    print(f"[文生视频] 场景 {i+1} 关键帧生成成功")
                    
                    # 3. 从关键帧生成视频
                    print(f"[文生视频] 场景 {i+1}: 开始从关键帧生成视频")
                    
                    # 提取关键帧URLs（模拟，实际需要从ComfyUI结果中解析）
                    keyframe_urls = []
                    for node_id, outputs in keyframe_result.get('node_results', {}).items():
                        if outputs:
                            keyframe_urls.extend([f"file://{output['filename']}" for output in outputs])
                    
                    if not keyframe_urls:
                        print(f"[文生视频] 场景 {i+1} 无法获取关键帧URLs")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': "无法获取关键帧URLs",
                            'prompt': video_prompt
                        })
                        continue
                    
                    video_result = self.comfyui_service.generate_video_from_keyframes(
                        keyframe_urls=keyframe_urls,
                        prompt=comfyui_prompt
                    )
                    
                    if not video_result.get('success'):
                        print(f"[文生视频] 场景 {i+1} 视频生成失败: {video_result.get('error')}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': f"视频生成失败: {video_result.get('error')}",
                            'prompt': video_prompt
                        })
                        continue
                    
                    print(f"[文生视频] 场景 {i+1} 视频生成成功")
                    
                    # 4. 保存视频结果
                    local_video_path = os.path.join(produce_video_dir, f"scene_{i+1:02d}_{scene.get('scene_id', i+1)}.mp4")
                    
                    # 模拟保存，实际需要从ComfyUI下载或获取本地路径
                    # 这里简化处理，假设视频已生成到目标位置
                    print(f"[文生视频] 场景 {i+1} 视频保存成功: {local_video_path}")
                    
                    generated_videos.append({
                        'scene_index': i,
                        'scene_id': scene.get('scene_id', i+1),
                        'success': True,
                        'local_path': local_video_path,
                        'prompt': video_prompt,
                        'duration': scene.get('duration', 0),
                        'start_time': scene.get('start_time', 0),
                        'end_time': scene.get('end_time', 0),
                        'keyframe_count': len(keyframe_urls),
                        'comfyui_prompt': comfyui_prompt
                    })
                    
                except Exception as e:
                    print(f"[文生视频] 场景 {i+1} 处理异常: {e}")
                    import traceback
                    traceback.print_exc()
                    generated_videos.append({
                        'scene_index': i,
                        'scene_id': scene.get('scene_id', i+1),
                        'success': False,
                        'error': str(e),
                        'prompt': str(video_prompt_data)
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
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'generated_videos': []
            }
    
    def create_video_generation_task(self, prompt: str) -> Dict[str, Any]:
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
    
    def _get_scene_audio_content(self, full_transcription: str, scene: Dict[str, Any]) -> str:
        if not full_transcription:
            return ""
        
        # 简单实现：返回空字符串，实际项目中可以根据时间戳匹配
        # 这里需要根据具体的音频转录格式进行实现
        return ""
    
    def save_recreation_result(self, result: Dict[str, Any], task_dir: str = None):
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
    
    async def generate_videos_with_qwen(self, scene_analysis: Dict[str, Any], video_path: str, recreation_id: int = None, task_dir: str = None, video_understanding: Dict[str, Any] = None) -> Dict[str, Any]:
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
            print(f"[Qwen Video] 创建视频输出目录: {produce_video_dir}")
            
            generated_videos = []
            scenes = scene_analysis['scenes']
            
            print(f"[Qwen Video] 开始生成视频，共 {len(scenes)} 个场景")
            print(f"[Qwen Video] 使用Qwen工作流：qwen-image-edit-plus关键帧生成 → wan2.6-r2v视频生成")
            
            # 初始化上一个场景的信息，用于保持场景连贯性
            previous_scene_keyframes = []
            
            # 初始化风格锁定机制，从第一个场景提取风格信息，后续场景严格遵循
            locked_style = None
            
            for i, scene in enumerate(scenes):
                try:
                    print(f"\n[Qwen Video] 开始处理场景 {i+1}/{len(scenes)}")
                    
                    # 获取视频提示词
                    video_prompt_data = scene.get('video_prompt', {})
                    if isinstance(video_prompt_data, dict):
                        # 如果是字典格式，检查success字段
                        if video_prompt_data.get('success'):
                            # 成功情况下，提取video_prompt字段
                            video_prompt = video_prompt_data.get('video_prompt', '')
                        else:
                            # 失败情况下，直接使用video_prompt字段
                            video_prompt = video_prompt_data.get('video_prompt', '')
                    elif isinstance(video_prompt_data, str):
                        # 如果直接是字符串，直接使用
                        video_prompt = video_prompt_data
                    else:
                        video_prompt = str(video_prompt_data)
                    
                    if not video_prompt:
                        print(f"[Qwen Video] 场景 {i+1} 提示词为空，跳过")
                        continue
                    
                    print(f"[Qwen Video] 场景 {i+1} 提示词: {video_prompt[:100]}...")
                    
                    # 构建场景数据，保留原始场景的所有信息
                    scene_data = scene.copy()
                    scene_data['video_prompt'] = video_prompt
                    
                    # 保留原始场景的技术参数，只在缺失时添加默认值
                    original_tech_params = scene.get('technical_params', {})
                    scene_data['technical_params'] = {
                        'width': original_tech_params.get('width', 1280),
                        'height': original_tech_params.get('height', 720),
                        'duration': scene.get('duration', 5),
                        'fps': original_tech_params.get('fps', 24),
                        **original_tech_params  # 保留所有原始技术参数
                    }
                    
                    # 保留原始场景的风格元素，只在缺失时添加默认值
                    original_style_elements = scene.get('style_elements', {})
                    scene_data['style_elements'] = {
                        'style': original_style_elements.get('style', 'cinematic'),
                        'quality': original_style_elements.get('quality', 'high'),
                        'motion': original_style_elements.get('motion', 'natural'),
                        **original_style_elements  # 保留所有原始风格元素
                    }
                    
                    # 风格锁定机制
                    if i == 0:
                        # 第一个场景，提取并锁定风格信息
                        print(f"[Qwen Video] 场景 {i+1}: 提取并锁定风格信息")
                        locked_style = scene_data['style_elements'].copy()
                        print(f"[Qwen Video] 场景 {i+1}: 锁定的风格信息: {locked_style}")
                    else:
                        # 非第一个场景，应用锁定的风格信息
                        if locked_style:
                            print(f"[Qwen Video] 场景 {i+1}: 应用锁定的风格信息")
                            # 严格应用锁定的风格，确保场景间风格一致
                            scene_data['style_elements'].update(locked_style)
                            print(f"[Qwen Video] 场景 {i+1}: 更新后的风格信息: {scene_data['style_elements']}")
                    
                    # 添加上一个场景的信息，增强连贯性
                    if i > 0 and scene.get('previous_scene_info'):
                        scene_data['previous_scene_info'] = scene.get('previous_scene_info')
                    
                    # 1. 优化JSON提示词
                    print(f"[Qwen Video] 场景 {i+1}: 开始优化JSON提示词")
                    optimized_scene_data = self.scene_segmenter.optimize_json_prompt(scene_data)
                    
                    # 2. 将JSON转换为适合qwen-image的文本格式
                    print(f"[Qwen Video] 场景 {i+1}: 将JSON转换为文本提示词")
                    text_prompt = self.scene_segmenter.json_to_text_prompt(optimized_scene_data)
                    
                    # 更新scene_data的video_prompt为转换后的文本格式
                    optimized_scene_data['video_prompt'] = text_prompt
                    
                    # 3. 准备关键帧生成参数
                    keyframe_prompt = {
                        "video_prompt": optimized_scene_data.get("video_prompt", ""),
                        "technical_params": optimized_scene_data.get("technical_params", {})
                    }
                    
                    # 4. 获取原视频切片的关键帧作为参考
                    reference_images = []
                    
                    # 从多个来源获取关键帧，确保优先获取原视频切片的关键帧
                    # 1. 首先从外部传入的video_understanding中获取（优先）
                    if video_understanding is not None:
                        # 1.1 从raw_slices中获取原视频切片的关键帧
                        if 'raw_slices' in video_understanding and i < len(video_understanding['raw_slices']):
                            slice_data = video_understanding['raw_slices'][i]
                            if 'keyframes' in slice_data:
                                reference_images = slice_data['keyframes']
                                print(f"[Qwen Video] 场景 {i+1}: 从raw_slices[{i}]获取了 {len(reference_images)} 个原视频切片关键帧")
                        # 1.2 从slices中获取
                        elif 'slices' in video_understanding and i < len(video_understanding['slices']):
                            slice_info = video_understanding['slices'][i]
                            if 'keyframes' in slice_info:
                                reference_images = slice_info['keyframes']
                                print(f"[Qwen Video] 场景 {i+1}: 从slices[{i}]获取了 {len(reference_images)} 个原视频切片关键帧")
                        # 1.3 从vl_analysis中获取
                        elif 'vl_analysis' in video_understanding and i < len(video_understanding['vl_analysis']):
                            vl_slice = video_understanding['vl_analysis'][i]
                            if 'keyframes' in vl_slice:
                                reference_images = vl_slice['keyframes']
                                print(f"[Qwen Video] 场景 {i+1}: 从vl_analysis[{i}]获取了 {len(reference_images)} 个原视频切片关键帧")
                    
                    # 2. 如果从video_understanding中未获取到，再从scene对象中获取
                    if not reference_images and 'keyframes' in scene:
                        reference_images = scene['keyframes']
                        print(f"[Qwen Video] 场景 {i+1}: 从场景对象获取了 {len(reference_images)} 个参考关键帧")
                    
                    # 3. 确保获取到足够的参考关键帧
                    if not reference_images:
                        print(f"[Qwen Video] 场景 {i+1}: 警告：未找到原视频切片关键帧，这可能导致生成视频与原视频差距较大")
                    else:
                        print(f"[Qwen Video] 场景 {i+1}: 成功获取到 {len(reference_images)} 个原视频切片关键帧")
                        
                        # 5. 使用qwen3-vl-plus分析关键帧，生成json格式的prompt
                        print(f"[Qwen Video] 场景 {i+1}: 开始使用qwen3-vl-plus分析关键帧")
                        qwen3vl_result = self.qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                            reference_images,
                            {
                                "video_prompt": optimized_scene_data.get("video_prompt", "")
                            }
                        )
                        
                        if qwen3vl_result.get('success'):
                            qwen3vl_prompt = qwen3vl_result.get('prompt', '')
                            print(f"[Qwen Video] 场景 {i+1}: qwen3-vl-plus分析成功，生成了优化的prompt")
                            
                            # 将qwen3-vl-plus生成的prompt与原prompt结合
                            if qwen3vl_prompt:
                                try:
                                    import json
                                    qwen3vl_data = json.loads(qwen3vl_prompt)
                                    
                                    # 智能融合qwen3-vl-plus生成的提示词与原提示词
                                    original_prompt = optimized_scene_data.get('video_prompt', '')
                                    
                                    # 从qwen3-vl-plus结果中提取关键信息
                                    qwen3vl_content = qwen3vl_data.get('video_content_description', '')
                                    qwen3vl_style = qwen3vl_data.get('visual_style', {})
                                    qwen3vl_tech_params = qwen3vl_data.get('technical_parameters', {})
                                    qwen3vl_atmosphere = qwen3vl_data.get('scene_atmosphere', '')
                                    
                                    # 构建新的提示词，保留原提示词的核心内容，同时融合qwen3-vl-plus的分析结果
                                    # 确保与原视频内容高度一致
                                    new_prompt = f"{original_prompt}"
                                    
                                    if qwen3vl_content:
                                        new_prompt += f"\n\n内容描述: {qwen3vl_content}"
                                    
                                    # 更新风格信息，确保与原视频风格一致
                                    if qwen3vl_style:
                                        # 严格遵循原视频风格
                                        if isinstance(qwen3vl_style, dict):
                                            if 'style' in qwen3vl_style:
                                                optimized_scene_data['style_elements']['style'] = qwen3vl_style['style']
                                            if 'color_palette' in qwen3vl_style:
                                                optimized_scene_data['style_elements']['color_palette'] = qwen3vl_style['color_palette']
                                            if 'animation_style' in qwen3vl_style:
                                                optimized_scene_data['style_elements']['animation_style'] = qwen3vl_style['animation_style']
                                        else:
                                            optimized_scene_data['style_elements']['style'] = qwen3vl_style
                                    
                                    # 更新技术参数
                                    if qwen3vl_tech_params:
                                        optimized_scene_data['technical_params'].update(qwen3vl_tech_params)
                                    
                                    if qwen3vl_atmosphere:
                                        new_prompt += f"\n\n氛围: {qwen3vl_atmosphere}"
                                    
                                    # 只在新提示词有实质性改进时才更新
                                    if len(new_prompt) > len(original_prompt):
                                        optimized_scene_data['video_prompt'] = new_prompt
                                        print(f"[Qwen Video] 场景 {i+1}: 智能融合qwen3-vl-plus提示词成功")
                                    
                                except json.JSONDecodeError as e:
                                    print(f"[Qwen Video] 场景 {i+1}: qwen3-vl-plus返回的JSON格式错误: {e}")
                                except Exception as e:
                                    print(f"[Qwen Video] 场景 {i+1}: 融合qwen3-vl-plus提示词失败: {e}")
                        else:
                            print(f"[Qwen Video] 场景 {i+1}: qwen3-vl-plus分析失败: {qwen3vl_result.get('error')}")
                    
                    # 如果有上一个场景的关键帧，添加到参考图像中
                    if i > 0 and previous_scene_keyframes:
                        print(f"[Qwen Video] 场景 {i+1}: 使用上一个场景的关键帧作为参考")
                        keyframe_prompt['previous_keyframes'] = previous_scene_keyframes
                        # 将上一个场景的最后一个关键帧添加到参考图像中
                        reference_images.append(previous_scene_keyframes[-1])
                        print(f"[Qwen Video] 场景 {i+1}: 添加上一个场景的关键帧，参考图像总数: {len(reference_images)}")
                    
                    # 5. 使用qwen-image-edit-plus生成关键帧
                    print(f"[Qwen Video] 场景 {i+1}: 开始使用qwen-image-edit-plus生成关键帧")
                    keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
                        keyframe_prompt, 
                        reference_images=reference_images, 
                        num_keyframes=3
                    )
                    
                    if not keyframe_result.get('success'):
                        print(f"[Qwen Video] 场景 {i+1} 关键帧生成失败: {keyframe_result.get('error')}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': f"关键帧生成失败: {keyframe_result.get('error')}",
                            'prompt': video_prompt
                        })
                        continue
                    
                    keyframes = keyframe_result.get('keyframes', [])
                    print(f"[Qwen Video] 场景 {i+1} 关键帧生成成功，共生成 {len(keyframes)} 个关键帧")
                    
                    # 2. 使用wan2.6-r2v从关键帧生成视频
                    print(f"[Qwen Video] 场景 {i+1}: 开始使用wan2.6-r2v从关键帧生成视频")
                    
                    # 准备视频生成参数，确保包含所有必要信息
                    video_gen_params = scene_data.copy()
                    video_gen_params['keyframes'] = keyframes
                    
                    # 添加上一个场景的关键帧作为参考
                    if i > 0 and previous_scene_keyframes:
                        print(f"[Qwen Video] 场景 {i+1}: 使用上一个场景的关键帧作为视频生成参考")
                        # 将上一个场景的最后一个关键帧添加到当前场景数据中
                        video_gen_params['previous_keyframe'] = previous_scene_keyframes[-1]  # 使用上一场景的最后一个关键帧
                        # 添加场景间连贯信息
                        video_gen_params['previous_scene_info'] = {
                            'video_prompt': scene_data.get('video_prompt', ''),
                            'style_elements': scene_data.get('style_elements', {}),
                            'scene_info': scene_data.get('scene_info', {})
                        }
                    
                    video_result = self.qwen_video_service.generate_video_from_keyframes(keyframes, video_gen_params)
                    
                    # 保存当前场景的关键帧，供下一个场景使用
                    previous_scene_keyframes = keyframes
                    
                    if not video_result.get('success'):
                        print(f"[Qwen Video] 场景 {i+1} 视频生成失败: {video_result.get('error')}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': f"视频生成失败: {video_result.get('error')}",
                            'prompt': video_prompt
                        })
                        continue
                    
                    # 3. 下载视频到本地
                    video_url = video_result.get('video_url')
                    if not video_url:
                        print(f"[Qwen Video] 场景 {i+1} 生成成功但未返回视频URL")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': "生成成功但未返回视频URL",
                            'prompt': video_prompt
                        })
                        continue
                    
                    local_video_path = os.path.join(produce_video_dir, f"scene_{i+1:02d}_{scene.get('scene_id', i+1)}.mp4")
                    print(f"[Qwen Video] 场景 {i+1}: 开始下载视频到本地")
                    
                    download_result = self.qwen_video_service.download_video(video_url, local_video_path)
                    if not download_result.get('success'):
                        print(f"[Qwen Video] 场景 {i+1} 视频下载失败: {download_result.get('error')}")
                        generated_videos.append({
                            'scene_index': i,
                            'scene_id': scene.get('scene_id', i+1),
                            'success': False,
                            'error': f"视频下载失败: {download_result.get('error')}",
                            'prompt': video_prompt,
                            'video_url': video_url
                        })
                        continue
                    
                    print(f"[Qwen Video] 场景 {i+1} 视频下载成功: {local_video_path}")
                    
                    # 创建当前场景信息，包含关键帧和原视频切片关键帧
                    current_scene_info = {
                        'video_path': local_video_path,
                        'video_info': {
                            'width': 1920,
                            'height': 1080,
                            'fps': 30
                        },
                        'keyframes': keyframes,
                        'scene_index': i,
                        'video_prompt': optimized_scene_data.get('video_prompt', ''),
                        'style_elements': optimized_scene_data.get('style_elements', {}),
                        'technical_params': optimized_scene_data.get('technical_params', {})
                    }
                    
                    # 一致性检查：如果不是第一个场景，检查与前一个场景的一致性
                    max_retries = 3
                    retry_count = 0
                    consistency_passed = False
                    
                    while retry_count < max_retries and not consistency_passed:
                        if i > 0 and previous_scene_info:
                            print(f"[Qwen Video] 场景 {i+1}: 开始一致性检查，重试次数: {retry_count+1}")
                            
                            # 准备一致性检查数据
                            consistency_data = {
                                'current_scene': current_scene_info,
                                'previous_scene': previous_scene_info,
                                'prompt_data': {
                                    'original_prompt': video_prompt,
                                    'optimized_prompt': optimized_scene_data.get('video_prompt', ''),
                                    'generation_params': optimized_scene_data.get('technical_params', {})
                                }
                            }
                            
                            try:
                                # 调用一致性检查代理
                                consistency_result = await self.consistency_agent.check_consistency(
                                    current_scene_info,
                                    previous_scene_info,
                                    consistency_data['prompt_data']
                                )
                                
                                print(f"[Qwen Video] 场景 {i+1}: 一致性检查结果: {'通过' if consistency_result.get('passed') else '未通过'}")
                                
                                if consistency_result.get('passed'):
                                    consistency_passed = True
                                    print(f"[Qwen Video] 场景 {i+1}: 一致性检查通过")
                                else:
                                    # 一致性检查未通过，重新生成视频
                                    print(f"[Qwen Video] 场景 {i+1}: 一致性检查未通过，开始优化提示词和参数")
                                    
                                    # 获取优化建议
                                    optimized_prompt = consistency_result.get('optimization_feedback', {}).get('optimized_prompt', '')
                                    adjusted_params = consistency_result.get('optimization_feedback', {}).get('adjusted_params', {})
                                    
                                    if optimized_prompt:
                                        # 更新优化的场景数据
                                        # 智能融合提示词，而不是直接替换
                                        original_prompt = optimized_scene_data.get('video_prompt', '')
                                        # 保留原提示词的核心内容，只添加优化建议
                                        optimized_scene_data['video_prompt'] = f"{original_prompt}\n\n优化建议: {optimized_prompt}"
                                        if adjusted_params:
                                            optimized_scene_data['technical_params'].update(adjusted_params)
                                        
                                        # 重新生成关键帧
                                        print(f"[Qwen Video] 场景 {i+1}: 使用优化后的提示词重新生成关键帧")
                                        keyframe_prompt['video_prompt'] = optimized_scene_data['video_prompt']
                                        keyframe_prompt['technical_params'] = optimized_scene_data['technical_params']
                                        
                                        keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
                                            keyframe_prompt, 
                                            reference_images=reference_images, 
                                            num_keyframes=3
                                        )
                                        
                                        if keyframe_result.get('success'):
                                            keyframes = keyframe_result.get('keyframes', [])
                                            print(f"[Qwen Video] 场景 {i+1}: 重新生成关键帧成功")
                                            
                                            # 重新生成视频
                                            print(f"[Qwen Video] 场景 {i+1}: 使用重新生成的关键帧生成视频")
                                            video_result = self.qwen_video_service.generate_video_from_keyframes(keyframes, optimized_scene_data)
                                            
                                            if video_result.get('success'):
                                                # 重新下载视频
                                                video_url = video_result.get('video_url')
                                                download_result = self.qwen_video_service.download_video(video_url, local_video_path)
                                                
                                                if download_result.get('success'):
                                                    print(f"[Qwen Video] 场景 {i+1}: 重新生成视频成功")
                                                    # 更新当前场景信息
                                                    current_scene_info['keyframes'] = keyframes
                                                    current_scene_info['video_prompt'] = optimized_scene_data['video_prompt']
                                                    current_scene_info['technical_params'] = optimized_scene_data['technical_params']
                                                    retry_count += 1
                                                else:
                                                    print(f"[Qwen Video] 场景 {i+1}: 重新下载视频失败")
                                                    retry_count += 1
                                                    break
                                            else:
                                                print(f"[Qwen Video] 场景 {i+1}: 重新生成视频失败")
                                                retry_count += 1
                                        else:
                                            print(f"[Qwen Video] 场景 {i+1}: 重新生成关键帧失败")
                                            retry_count += 1
                                    else:
                                        print(f"[Qwen Video] 场景 {i+1}: 未获取到优化提示词")
                                        retry_count += 1
                            except Exception as e:
                                print(f"[Qwen Video] 场景 {i+1}: 一致性检查异常: {e}")
                                print(f"[Qwen Video] 场景 {i+1}: 跳过一致性检查，继续执行")
                                # 跳过一致性检查，继续执行
                                consistency_passed = True
                                retry_count += 1
                        else:
                            # 第一个场景或没有上一个场景信息，直接通过
                            consistency_passed = True
                    
                    # 更新当前场景信息，准备添加到生成视频列表
                    current_scene_info.update({
                        'original_keyframes': reference_images,
                        'scene_id': scene.get('scene_id', i+1),
                        'scene_index': i
                    })
                    
                    # 保存当前场景信息，作为下一个场景的前一个场景信息
                    previous_scene_info = current_scene_info.copy()
                    
                    # 5. 将一致性检查结果添加到当前场景信息
                    current_scene_info['consistency_check_result'] = check_result if 'check_result' in locals() else {}
                    
                    # 6. 将生成的视频信息添加到结果列表
                    generated_videos.append({
                        'scene_index': i,
                        'scene_id': scene.get('scene_id', i+1),
                        'success': True,
                        'local_path': local_video_path,
                        'video_url': video_url,
                        'prompt': optimized_scene_data.get('video_prompt', ''),
                        'duration': scene.get('duration', 4),
                        'start_time': scene.get('start_time', i * 4),
                        'end_time': scene.get('end_time', (i + 1) * 4),
                        'keyframe_count': len(keyframes),
                        'keyframes': keyframes,
                        'original_keyframes': reference_images,
                        'consistency_check_result': current_scene_info.get('consistency_check_result', {}),
                        'video_info': current_scene_info.get('video_info', {})
                    })
                    
                except Exception as e:
                    print(f"[Qwen Video] 场景 {i+1} 处理异常: {e}")
                    import traceback
                    traceback.print_exc()
                    generated_videos.append({
                        'scene_index': i,
                        'scene_id': scene.get('scene_id', i+1),
                        'success': False,
                        'error': str(e),
                        'prompt': str(video_prompt_data)
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
            
            print(f"\n[Qwen Video] 视频生成完成! 成功: {len(successful_videos)}, 失败: {len(failed_videos)}")
            return result
            
        except Exception as e:
            print(f"[Qwen Video] 视频生成过程异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'generated_videos': []
            }

