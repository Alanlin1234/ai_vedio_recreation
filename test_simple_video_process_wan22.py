#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import asyncio
import json
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# 导入logging模块并创建logger
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 添加控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 导入必要的服务类
from app.services.ffmpeg_service import FFmpegService
from app.services.qwen_vl_service import QwenVLService
from app.services.qwen_video_service import QwenVideoService
from app.services.scene_segmentation_service import SceneSegmentationService
from app.services.json_prompt_parser import JSONPromptParser
from app.services.frame_continuity_service import FrameContinuityService
from app.services.speaker_voice_service import SpeakerVoiceService
from app.services.speaker_tts_integration import SpeakerTTSIntegration
from video_consistency_agent.agent.consistency_agent import ConsistencyAgent

# 不需要Flask应用实例，直接进行测试

class QwenVideoServiceWan26(QwenVideoService):
    """
    使用wan2.6模型的QwenVideoService子类
    """
    
    def generate_video_from_keyframes(self, keyframes: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 使用父类的logger
            logger.info(f"开始使用wan2.6生成视频")
            
            # 获取核心提示词并进行编码检查
            video_prompt = prompt.get('video_prompt', '')
            
            # 编码检查和处理
            if isinstance(video_prompt, str):
                try:
                    # 确保字符串是UTF-8编码
                    video_prompt = video_prompt.encode('utf-8').decode('utf-8')
                    logger.info(f"提示词编码检查通过，长度: {len(video_prompt)}")
                except UnicodeError as e:
                    logger.error(f"提示词编码错误: {str(e)}")
                    # 尝试使用错误处理模式
                    video_prompt = video_prompt.encode('utf-8', errors='replace').decode('utf-8')
                    logger.info(f"使用错误处理模式修复编码")
            
            logger.info(f"提示词: {video_prompt[:150]}...")
            logger.info(f"关键帧数量: {len(keyframes)}")
            logger.info(f"关键帧列表: {keyframes}")
            
            # 导入VideoSynthesis类和HTTPStatus
            from dashscope import VideoSynthesis
            from http import HTTPStatus
            
            # 检查关键帧数量，确保至少有一个关键帧
            if not keyframes:
                error_msg = "wan2.2视频生成失败: 没有可用的关键帧"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # 使用第一个关键帧作为参考图像（这是上一场景的最后一帧）
            img_url = keyframes[0]
            
            logger.info(f"使用参考图像: {img_url}")
            logger.info(f"该参考图像是{'上一场景的最后一帧' if len(keyframes) > 1 else '当前场景的关键帧'}")
            
            # 遍历所有API密钥，尝试生成视频
            for key_index in range(len(self.api_keys)):
                # 手动切换到当前索引的API密钥
                self.api_key = self.api_keys[key_index]
                logger.info(f"使用API密钥 {self.api_key[:10]}... 尝试生成视频")
                
                try:
                    # 调用视频生成API，使用异步调用方式
                    # 添加free_tier_only=False参数来禁用免费模式，使用付费模式
                    # 使用wan2.2模型
                    rsp = VideoSynthesis.async_call(
                        model='wan2.6-i2v-flash',
                        prompt=video_prompt,
                        img_url=img_url,
                        api_key=self.api_key,
                        free_tier_only=False,
                        video_params={
                            "resolution": "720p",
                            "audio": False
                        }
                    )
                    
                    logger.debug(f"异步调用响应: {rsp}")
                    
                    if rsp.status_code != HTTPStatus.OK:
                        error_msg = f"wan2.6视频生成失败: HTTP {rsp.status_code}, code: {rsp.code}, message: {rsp.message}"
                        logger.error(error_msg)
                        
                        # 检查是否是API密钥错误
                        if hasattr(rsp, 'code') and 'InvalidApiKey' in str(rsp.code):
                            logger.error(f"API密钥无效，切换到下一个密钥")
                            self.rotate_api_key()
                            continue
                        else:
                            # 其他错误，直接返回失败
                            return {
                                "success": False,
                                "error": error_msg
                            }
                    
                    task_id = rsp.output.task_id
                    logger.info(f"wan2.6视频生成任务创建成功，task_id: {task_id}")
                    
                    # 等待任务完成 - 使用自定义等待逻辑，增加等待时间和轮询次数
                    logger.info(f"开始等待视频生成任务完成...")
                    
                    # 自定义等待逻辑，确保有足够的时间让任务完成
                    max_wait_time = 600  # 最大等待时间（秒）
                    poll_interval = 10  # 轮询间隔（秒）
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait_time:
                        # 显式传递API密钥给fetch方法
                        wait_rsp = VideoSynthesis.fetch(rsp, api_key=self.api_key)
                        logger.debug(f"轮询任务状态: {wait_rsp.output.task_status}, 已等待: {time.time() - start_time:.1f}秒")
                        
                        if wait_rsp.status_code != HTTPStatus.OK:
                            error_msg = f"wan2.6视频生成失败: HTTP {wait_rsp.status_code}, code: {wait_rsp.code}, message: {wait_rsp.message}"
                            logger.error(error_msg)
                            return {
                                "success": False,
                                "error": error_msg
                            }
                        
                        # 检查任务状态
                        task_status = wait_rsp.output.task_status
                        if task_status == "SUCCEEDED":
                            # 任务成功完成，获取视频URL
                            video_url = wait_rsp.output.video_url
                            if video_url:
                                logger.info(f"视频生成成功，视频URL: {video_url}")
                                return {
                                    "success": True,
                                    "video_url": video_url,
                                    "task_id": task_id
                                }
                            else:
                                logger.warning("任务状态为SUCCEEDED，但未返回视频URL，继续等待...")
                        elif task_status in ["FAILED", "CANCELED"]:
                            # 任务失败或被取消
                            error_msg = f"wan2.2视频生成失败: 任务状态为 {task_status}"
                            logger.error(error_msg)
                            return {
                                "success": False,
                                "error": error_msg
                            }
                        
                        # 任务还在处理中，继续等待
                        logger.info(f"任务状态: {task_status}，继续等待...")
                        time.sleep(poll_interval)
                    
                    # 等待超时
                    error_msg = f"wan2.2视频生成超时: 超过 {max_wait_time} 秒仍未完成"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                
                except Exception as e:
                    error_msg = f"wan2.2视频生成异常: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    import traceback
                    traceback.print_exc()
                    print(f"[ERROR] 视频生成异常: {str(e)}")
                    print(f"[ERROR] 异常类型: {type(e).__name__}")
                    
                    # 检查是否是API密钥错误
                    if "InvalidApiKey" in str(e) or "api_key" in str(e).lower():
                        logger.error(f"API密钥无效，切换到下一个密钥")
                        self.rotate_api_key()
                        continue
                    else:
                        # 其他异常，直接返回失败
                        break
            
            # 如果所有API密钥都尝试过仍失败，返回最终失败结果
            logger.error("所有API密钥都尝试过，视频生成失败")
            return {
                "success": False,
                "error": "所有API密钥都尝试过，视频生成失败"
            }
            
        except Exception as e:
            error_msg = f"wan2.2视频生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg
            }

class VideoProcessingTest:
    def __init__(self, video_path: str, slice_count: int = 5):
        self.video_path = video_path
        self.slice_count = slice_count
        self.output_dir = f"downloads/test_wan22_{int(time.time())}"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 配置选项
        self.use_original_keyframes = True  # 直接使用原视频关键帧，不使用AI生成
        
        # 初始化服务
        self.ffmpeg_service = FFmpegService()
        self.qwen_vl_service = QwenVLService()
        self.qwen_video_service = QwenVideoServiceWan26()  # 使用wan2.6模型
        self.scene_segmenter = SceneSegmentationService()
        self.json_parser = JSONPromptParser()
        self.frame_continuity_service = FrameContinuityService()
        self.speaker_voice_service = SpeakerVoiceService()
        self.speaker_tts_integration = SpeakerTTSIntegration()
        # 初始化ConsistencyAgent
        config_path = "video_consistency_agent/config/config.yaml"
        self.consistency_agent = ConsistencyAgent(config_path)
        
        # 流程状态
        self.video_slices = []
        self.scene_prompts = []
        self.generated_videos = []
        self.consistency_results = []
        
    def log_step(self, step_name: str, status: str, debug_info: str = ""):
        if debug_info:
            print(f"[{time.strftime('%H:%M:%S')}] {step_name}: {status} | {debug_info}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] {step_name}: {status}")
    
    async def slice_video(self):
        self.log_step("视频切片", "开始")
        
        try:
            # 获取视频总时长，使用固定的5秒切片时长
            video_info = await self.ffmpeg_service.get_video_info(self.video_path)
            total_duration = video_info.get('duration', 20)
            slice_duration = 5  # 固定为5秒/个
            
            self.log_step("视频切片", "获取视频信息", f"总时长: {total_duration:.1f}s, 切片时长: {slice_duration}s")
            
            # 切片视频，限制最多生成10个切片
            slice_result = await self.ffmpeg_service.slice_video(
                self.video_path, 
                slice_duration=slice_duration,
                slice_limit=10  # 添加切片数量限制
            )
            
            if slice_result and 'slices' in slice_result:
                self.video_slices = slice_result['slices'][:self.slice_count]
                
                # 为每个切片提取音频文件
                for i, slice_info in enumerate(self.video_slices):
                    audio_result = await self.ffmpeg_service.extract_audio(slice_info['output_file'])
                    if audio_result and 'audio_path' in audio_result:
                        self.video_slices[i]['audio_file'] = audio_result['audio_path']
                        self.log_step("音频提取", f"切片{i+1}音频提取完成", f"音频路径: {audio_result['audio_path']}")
                
                self.log_step("视频切片", f"完成，生成{len(self.video_slices)}个切片", f"总时长: {total_duration:.1f}s, 每个切片时长: {slice_duration}s")
                return True
            else:
                self.log_step("视频切片", "失败，切片结果格式错误")
                return False
        except Exception as e:
            self.log_step("视频切片", f"失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def analyze_video_slices(self):
        self.log_step("视频切片分析", "开始")
        
        try:
            # 导入语音识别服务
            from app.services.speech_recognition_service import SimpleSpeechRecognizer
            
            # 初始化语音识别器
            speech_recognizer = SimpleSpeechRecognizer()
            
            self.log_step("视频切片分析", "初始化服务", "语音识别器初始化完成")
            
            # 为每个切片转录音频内容
            slice_audio_contents = []
            for i, slice_info in enumerate(self.video_slices):
                if 'audio_file' in slice_info and slice_info['audio_file']:
                    self.log_step("音频转录", f"开始转录切片{i+1}的音频", f"音频路径: {slice_info['audio_file']}")
                    transcribe_result = speech_recognizer.transcribe(slice_info['audio_file'])
                    if transcribe_result.get('success'):
                        slice_audio_content = transcribe_result.get('text', '')
                        slice_audio_contents.append(slice_audio_content)
                        self.video_slices[i]['audio_content'] = slice_audio_content
                        self.log_step("音频转录", f"切片{i+1}音频转录完成", f"音频内容长度: {len(slice_audio_content)} 字符")
                    else:
                        slice_audio_contents.append('')
                        self.log_step("音频转录", f"切片{i+1}音频转录失败", f"错误: {transcribe_result.get('error', '未知错误')}")
                else:
                    slice_audio_contents.append('')
            
            # 使用qwen-omni-turbo分析视频内容
            self.log_step("qwen-omni-turbo分析", "开始", f"分析{len(self.video_slices)}个切片")
            try:
                # 传递音频内容作为辅助信息
                await self.qwen_vl_service.analyze_video_content(
                    self.video_slices,
                    audio_contents=slice_audio_contents  # 添加音频内容作为辅助信息
                )
                self.log_step("qwen-omni-turbo分析", "完成")
            except Exception as e:
                self.log_step("qwen-omni-turbo分析", f"失败: {str(e)}")
                import traceback
                traceback.print_exc()
                # 继续执行后续步骤，不中断流程
            
            # 从每个切片提取关键帧
            self.log_step("关键帧提取", "开始", f"为{len(self.video_slices)}个切片提取关键帧")
            # 模拟关键帧提取，使用切片的预览图作为关键帧
            for i, slice_info in enumerate(self.video_slices):
                if 'preview_file' in slice_info and slice_info['preview_file']:
                    self.video_slices[i]['keyframes'] = [slice_info['preview_file']]
                    self.log_step("关键帧提取", f"切片{i+1}完成", f"关键帧数量: 1")
            self.log_step("关键帧提取", "完成")
            
            # 尝试使用qwen3-vl-plus分析关键帧
            self.log_step("qwen3-vl-plus关键帧分析", "开始", f"分析{len(self.video_slices)}个切片的关键帧")
            try:
                for i, slice_info in enumerate(self.video_slices):
                    if 'keyframes' in slice_info and slice_info['keyframes']:
                        keyframes = slice_info['keyframes']
                        try:
                            # 调用analyze_keyframes_with_qwen3vl_plus方法（同步方法，不需要await）
                            vl_result = self.qwen_video_service.analyze_keyframes_with_qwen3vl_plus(
                                keyframes, 
                                {"video_prompt": f"分析第{i+1}个场景的关键帧，生成详细的视频描述",
                                 "audio_content": slice_info.get('audio_content', '')}
                            )
                            if vl_result.get('success'):
                                self.video_slices[i]['vl_analysis'] = vl_result
                                self.log_step(f"qwen3-vl-plus关键帧分析", f"场景{i+1}成功")
                            else:
                                self.log_step(f"qwen3-vl-plus关键帧分析", f"场景{i+1}失败", f"错误: {vl_result.get('error', '未知错误')}")
                        except Exception as e:
                            self.log_step(f"qwen3-vl-plus关键帧分析", f"场景{i+1}失败: {str(e)}")
                            # 继续处理下一个场景
                self.log_step("qwen3-vl-plus关键帧分析", "完成")
            except Exception as e:
                self.log_step("qwen3-vl-plus关键帧分析", f"失败: {str(e)}")
                import traceback
                traceback.print_exc()
                # 跳过关键帧分析，继续执行后续步骤
            
            return True
        except Exception as e:
            self.log_step("视频切片分析", f"失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def combine_and_optimize_prompts(self):
        self.log_step("提示词优化", "开始")
        
        try:
            for i, slice_info in enumerate(self.video_slices):
                # 结合分析结果生成基础prompt
                combined_prompt = {
                    "scene_id": i + 1,
                    "start_time": slice_info.get('start_time', 0),
                    "end_time": slice_info.get('end_time', 0),
                    "duration": slice_info.get('duration', 4),
                    "original_video_info": {
                        "slice_path": slice_info['output_file'],
                        "audio_path": slice_info.get('audio_file', ''),
                        "keyframes": slice_info.get('keyframes', [])
                    }
                }
                
                # 构建基础提示词，根据改进建议优化
                base_prompt = f"场景{i+1}: 使用中文，基于原视频关键帧，重点描述以下内容： "
                
                # 添加qwen-omni-turbo分析结果，提取关键信息
                if 'analysis' in slice_info:
                    video_content = slice_info['analysis'].get('video_content', '')
                    # 提取动作和表情信息
                    if '动作' in video_content or '表情' in video_content:
                        base_prompt += f"{video_content} "
                
                # 添加关键帧分析结果，重点关注风格、动作、表情
                if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
                    vl_result = slice_info['vl_analysis'].get('analysis_result', {})
                    
                    # 1. 风格信息
                    if 'style' in vl_result:
                        base_prompt += f"风格: {vl_result['style']} "
                    
                    # 2. 动作和表情信息
                    if 'action' in vl_result:
                        base_prompt += f"动作: {vl_result['action']} "
                    if 'emotion' in vl_result:
                        base_prompt += f"表情: {vl_result['emotion']} "
                    
                    # 3. 镜头类型和角度
                    if 'camera' in vl_result:
                        base_prompt += f"镜头: {vl_result['camera']} "
                    
                    # 4. 氛围和情绪
                    if 'atmosphere' in vl_result:
                        base_prompt += f"氛围: {vl_result['atmosphere']} "
                    if 'mood' in vl_result:
                        base_prompt += f"情绪: {vl_result['mood']} "
                    
                    # 5. 时间和地点
                    if 'time' in vl_result:
                        base_prompt += f"时间: {vl_result['time']} "
                    if 'location' in vl_result:
                        base_prompt += f"地点: {vl_result['location']} "
                
                # 添加音频内容作为辅助信息
                if 'audio_content' in slice_info and slice_info['audio_content']:
                    base_prompt += f"音频内容: {slice_info['audio_content'][:100]}... "
                
                # 添加改进建议的内容
                base_prompt += "，添加以下详细信息： "
                base_prompt += "1. 具体动作和表情描述； "
                base_prompt += "2. 明确的镜头类型和角度； "
                base_prompt += "3. 丰富的氛围和情绪； "
                base_prompt += "4. 明确的时间和地点； "
                base_prompt += "5. 合适的节奏和速度； "
                base_prompt += "6. 相关的音效和背景音乐； "
                base_prompt += "，减少对画面和人物的详细描述，依赖原视频关键帧，保持所有场景风格一致，统一使用中文，保持与原视频的镜头语言一致"
                
                # 使用qwen-plus-latest优化提示词，重点优化指定内容
                optimize_context = {
                    'audio_content': slice_info.get('audio_content', ''),
                    'keyframes': slice_info.get('keyframes', []),
                    'scene_order': i + 1,
                    'optimization_focus': '动作,表情,镜头类型,镜头角度,氛围,情绪,时间,地点,节奏,速度,音效,背景音乐,减少画面描述,保持连续性'  # 添加优化重点
                }
                
                optimize_result = self.qwen_video_service.optimize_prompt_with_qwen_plus_latest(
                    base_prompt,
                    optimize_context
                )
                
                if optimize_result.get('success'):
                    optimized_prompt = optimize_result.get('optimized_prompt', base_prompt)
                    # 进一步优化，确保满足改进建议
                    optimized_prompt = optimized_prompt.replace("详细描述", "简要描述").replace("详细", "")
                    # 添加更多关于动作、表情、镜头等的关键词
                    if "动作" not in optimized_prompt:
                        optimized_prompt += "，添加具体动作描述"
                    if "表情" not in optimized_prompt:
                        optimized_prompt += "，添加具体表情描述"
                    if "镜头" not in optimized_prompt:
                        optimized_prompt += "，添加明确的镜头类型和角度"
                    if "氛围" not in optimized_prompt and "情绪" not in optimized_prompt:
                        optimized_prompt += "，添加丰富的氛围和情绪描述"
                    if "时间" not in optimized_prompt and "地点" not in optimized_prompt:
                        optimized_prompt += "，添加明确的时间和地点"
                    if "节奏" not in optimized_prompt and "速度" not in optimized_prompt:
                        optimized_prompt += "，添加合适的节奏和速度描述"
                    if "音效" not in optimized_prompt and "背景音乐" not in optimized_prompt:
                        optimized_prompt += "，添加相关的音效和背景音乐描述"
                    
                    combined_prompt["optimized_prompt"] = optimized_prompt
                else:
                    combined_prompt["optimized_prompt"] = base_prompt
                
                self.scene_prompts.append(combined_prompt)
            
            self.log_step("提示词优化", f"完成，生成{len(self.scene_prompts)}个场景提示词")
            return True
        except Exception as e:
            self.log_step("提示词优化", f"失败: {str(e)}")
            return False
    
    def parse_json_prompts(self):
        self.log_step("JSON提示词解析", "开始")
        
        try:
            # 测试JSON解析器的各种场景（增强版）
            test_cases = [
                # 正常JSON格式
                '{"video_prompt": "A beautiful scene", "style_elements": {"characters": "person"}}',
                # 包含额外字段的JSON
                '{"video_prompt": "A scene", "custom_field": "value", "another_field": 123}',
                # 可能有格式问题的JSON
                '{"video_prompt": "A scene", "style_elements": {"characters": "person"}',
                # 空JSON
                '{}',
                # 纯文本
                'This is just plain text, not JSON',
                # 包含复杂嵌套结构的JSON
                '{"video_prompt": "A complex scene", "style_elements": {"characters": "person", "environment": "forest", "visual_style": "cinematic"}, "technical_params": {"aspect_ratio": "16:9", "fps": 24}}'
            ]
            
            for i, test_json in enumerate(test_cases):
                parsed_result = self.json_parser.parse_prompt(test_json, prompt_type="txt2img")
                self.log_step("JSON提示词解析测试", f"测试用例{i+1}: {'成功' if parsed_result.get('success') else '失败'}")
                if parsed_result.get('success'):
                    self.log_step("JSON提示词解析测试", f"测试用例{i+1}解析结果: {parsed_result.get('prompt', '')[:50]}...")
            
            for i, prompt in enumerate(self.scene_prompts):
                # 将prompt转换为JSON字符串，使用JSON解析器解析
                prompt_json = json.dumps(prompt, ensure_ascii=False)
                parsed_result = self.json_parser.parse_prompt(prompt_json, prompt_type="txt2img")
                
                if parsed_result.get('success'):
                    self.scene_prompts[i]['parsed_prompt'] = parsed_result.get('prompt', '')
                else:
                    self.scene_prompts[i]['parsed_prompt'] = prompt.get('optimized_prompt', '')
            
            self.log_step("JSON提示词解析", "完成")
            return True
        except Exception as e:
            self.log_step("JSON提示词解析", f"失败: {str(e)}")
            return False
    
    async def generate_scene_videos(self):
        self.log_step("场景视频生成", "开始")
        
        try:
            previous_keyframes = []
            previous_scene_last_frame = None
            
            for i, scene_prompt in enumerate(self.scene_prompts):
                self.log_step(f"场景{i+1}视频生成", "开始")
                
                slice_info = self.video_slices[i]
                reference_keyframes = slice_info.get('keyframes', [])
                
                # 使用首尾帧功能，添加上一个场景的最后一帧作为当前场景的首帧
                enhanced_prompt = scene_prompt.get('parsed_prompt', '')
                if i > 0 and previous_scene_last_frame:
                    self.log_step(f"场景{i+1}视频生成", "使用上一场景的最后一帧作为首帧")
                    # 构建包含上下文的提示词，明确要求保持与上一场景的连贯性
                    enhanced_prompt = self.frame_continuity_service.build_contextual_prompt(
                        current_prompt=scene_prompt.get('parsed_prompt', ''),
                        previous_scene_info={
                            'prompt_data': {
                                'original_prompt': self.scene_prompts[i-1].get('parsed_prompt', '') if i > 0 else '',
                                'generation_params': {
                                    'frame_rate': 24,
                                    'resolution': '1280x720',
                                    'duration': self.scene_prompts[i-1].get('duration', 4) if i > 0 else 4
                                }
                            },
                            'last_frame': previous_scene_last_frame  # 添加上一场景的最后一帧信息
                        },
                        use_first_frame_constraint=True
                    )
                    # 在prompt中明确要求保持与上一场景的连贯性
                    enhanced_prompt += ", 保持与上一场景的连续性，确保当前场景的第一帧与上一场景的最后一帧自然过渡，保持相同的角色、风格和语言"
                    scene_prompt['parsed_prompt'] = enhanced_prompt
                    self.log_step(f"场景{i+1}视频生成", "成功构建包含上下文的提示词")
                
                # 处理关键帧，实现首尾帧连接
                if self.use_original_keyframes:
                    self.log_step(f"场景{i+1}视频生成", "使用原视频的关键帧，跳过AI生成步骤")
                    
                    # 实现真正的首尾帧连接：将上一场景的最后一帧作为当前场景的第一帧
                    if i > 0 and previous_scene_last_frame:
                        self.log_step(f"场景{i+1}视频生成", f"使用上一场景的最后一帧作为当前场景的第一帧: {previous_scene_last_frame}")
                        # 创建新的关键帧列表，以上一场景的最后一帧为第一帧
                        generated_keyframes = [previous_scene_last_frame] + reference_keyframes
                        # 确保关键帧数量不超过3个
                        generated_keyframes = generated_keyframes[:3]
                    else:
                        # 第一个场景或没有上一场景的最后一帧，使用原关键帧
                        generated_keyframes = reference_keyframes[:3]  # 限制关键帧数量为3个
                    
                    self.log_step(f"场景{i+1}视频生成", f"使用关键帧，数量: {len(generated_keyframes)}")
                    
                    # 确保关键帧路径是file://格式，以便直接访问本地文件
                    formatted_keyframes = []
                    for keyframe in generated_keyframes:
                        if keyframe and os.path.exists(keyframe):
                            # 将本地路径转换为file://格式
                            file_url = f"file://{os.path.abspath(keyframe)}"
                            formatted_keyframes.append(file_url)
                        elif keyframe.startswith('file://') or keyframe.startswith('http://') or keyframe.startswith('https://'):
                            # 已经是URL格式，直接使用
                            formatted_keyframes.append(keyframe)
                    if formatted_keyframes:
                        generated_keyframes = formatted_keyframes
                        self.log_step(f"场景{i+1}视频生成", f"格式化关键帧路径完成，数量: {len(generated_keyframes)}")
                        for j, url in enumerate(generated_keyframes):
                            self.log_step(f"场景{i+1}视频生成", f"关键帧 URL {j+1}: {url}")
                    else:
                        self.log_step(f"场景{i+1}视频生成", "警告: 没有有效的关键帧")
                        # 使用模拟关键帧
                        generated_keyframes = [f"https://example.com/simulated_keyframe_{i+1}_{j}.jpg" for j in range(3)]
                else:
                    # 使用qwen-image-edit生成关键帧
                    self.log_step(f"场景{i+1}视频生成", "使用AI生成关键帧")
                    keyframe_prompt = {
                        "video_prompt": scene_prompt.get('parsed_prompt', ''),
                        "technical_params": {"frame_rate": 24, "resolution": "1280x720"}
                    }
                    
                    # 实现真正的首尾帧连接：将上一场景的最后一帧作为参考图像
                    reference_imgs = reference_keyframes
                    if i > 0 and previous_scene_last_frame:
                        # 将上一场景的最后一帧添加到参考图像列表的开头
                        reference_imgs = [previous_scene_last_frame] + reference_imgs
                        self.log_step(f"场景{i+1}视频生成", f"使用上一场景的最后一帧作为参考图像: {previous_scene_last_frame}")
                    
                    # 加入上一个场景的关键帧作为参考
                    if previous_keyframes:
                        keyframe_prompt['previous_keyframes'] = previous_keyframes
                    
                    # 调用generate_keyframes_with_qwen_image_edit方法（同步方法，不需要await）
                    keyframe_result = self.qwen_video_service.generate_keyframes_with_qwen_image_edit(
                        keyframe_prompt,
                        reference_images=reference_imgs,
                        num_keyframes=3,
                        previous_last_frame=previous_scene_last_frame
                    )
                    
                    if not keyframe_result.get('success'):
                        self.log_step(f"场景{i+1}视频生成", "失败，关键帧生成失败")
                        continue
                    
                    generated_keyframes = keyframe_result.get('keyframes', [])
                    self.log_step(f"场景{i+1}视频生成", f"关键帧生成完成，数量: {len(generated_keyframes)}")
                
                # 确保上一场景的最后一帧严格作为当前场景的第一帧
                # 1. 如果是后续场景，确保生成的视频从previous_scene_last_frame开始
                if i > 0 and previous_scene_last_frame:
                    # 将上一场景的最后一帧作为当前场景的首帧，确保视觉上完全一致
                    scene_prompt['parsed_prompt'] += f", 严格将上一场景的最后一帧作为当前场景的第一帧，确保视觉上完全一致"
                    # 确保上一场景的最后一帧是file://格式
                    if os.path.exists(previous_scene_last_frame):
                        # 将本地路径转换为file://格式
                        previous_scene_last_frame_url = f"file://{os.path.abspath(previous_scene_last_frame)}"
                    else:
                        # 已经是file://或HTTP URL格式
                        previous_scene_last_frame_url = previous_scene_last_frame
                    # 确保首帧是上一场景的最后一帧，但保留当前场景的其他关键帧
                    # 只在关键帧列表的开头添加上一场景的最后一帧
                    if generated_keyframes:
                        # 如果已经有其他关键帧，确保上一场景的最后一帧在开头
                        if generated_keyframes[0] != previous_scene_last_frame_url:
                            generated_keyframes = [previous_scene_last_frame_url] + generated_keyframes[1:]
                    else:
                        # 如果没有其他关键帧，只使用上一场景的最后一帧
                        generated_keyframes = [previous_scene_last_frame_url]
                
                # 使用wan2.2生成视频，将处理后的关键帧传给API
                # 调用generate_video_from_keyframes方法（同步方法，不需要await）
                video_result = self.qwen_video_service.generate_video_from_keyframes(
                    generated_keyframes,
                    {
                        "video_prompt": scene_prompt.get('parsed_prompt', ''),
                        "technical_params": {
                            "frame_rate": 24,
                            "resolution": "1280x720",
                            "duration": scene_prompt.get('duration', 4)
                        }
                    }
                )
                
                if video_result.get('success'):
                    # 下载视频到本地
                    video_path = await self.ffmpeg_service.download_video(
                        video_result.get('video_url', ''),
                        os.path.join(self.output_dir, f"scene_{i+1}.mp4")
                    )
                    
                    # 移除视频中的音频
                    video_path = await self.ffmpeg_service.remove_audio(video_path)
                    
                    # 2. 从生成的视频中提取最后一帧，用于下一场景
                    last_frame_path = os.path.join(self.output_dir, f"scene_{i+1}_last_frame.jpg")
                    last_frame_result = await self.ffmpeg_service.extract_last_frame(
                        video_path,
                        last_frame_path
                    )
                    
                    # 3. 更新previous_scene_last_frame为当前视频的最后一帧
                    if last_frame_result.get('success'):
                        extracted_frame_path = last_frame_result.get('frame_path', last_frame_path)
                        previous_scene_last_frame = extracted_frame_path
                        self.frame_continuity_service.set_previous_scene_frame(previous_scene_last_frame)
                        self.log_step(f"场景{i+1}视频生成", f"成功提取最后一帧: {extracted_frame_path}")
                    
                    # 一致性检查
                    consistency_data = {
                        "current_scene": {
                            "keyframes": generated_keyframes,
                            "prompt_data": {
                                "original_prompt": scene_prompt.get('parsed_prompt', ''),
                                "generation_params": {
                                    "frame_rate": 24,
                                    "resolution": "1280x720",
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
                                    "resolution": "1280x720",
                                    "duration": self.scene_prompts[i-1].get('duration', 4) if i > 0 else 4
                                }
                            },
                            "order": i-1
                        },
                        "prompt_data": {
                            "original_prompt": scene_prompt.get('parsed_prompt', ''),
                            "generation_params": {
                                "frame_rate": 24,
                                "resolution": "1280x720",
                                "duration": scene_prompt.get('duration', 4)
                            }
                        }
                    }
                    
                    # 使用check_consistency方法
                    current_scene = consistency_data["current_scene"]
                    previous_scene = consistency_data["previous_scene"]
                    prompt_data = consistency_data["prompt_data"]
                    
                    consistency_result = await self.consistency_agent.check_consistency(
                        current_scene,
                        previous_scene,
                        prompt_data
                    )
                    self.consistency_results.append(consistency_result)
                    
                    # 无论一致性检查结果如何，都保存生成的视频
                    self.generated_videos.append({
                        'scene_id': i + 1,
                        'video_path': video_path,
                        'keyframes': generated_keyframes,
                        'consistency_score': consistency_result.get('consistency_results', {}).get('score', 0.0),
                        'success': True  # 总是标记为成功，以便后续合成
                    })
                    
                    # 保存当前关键帧供下一个场景使用
                    previous_keyframes = generated_keyframes
                    # 保持使用从视频中提取的最后一帧，不覆盖
                    
                    # 一致性检查结果处理
                    if consistency_result.get('passed'):
                        self.log_step(f"场景{i+1}视频生成", "完成")
                    else:
                        # 一致性不满足，记录警告但继续执行
                        self.log_step(f"场景{i+1}视频生成", "一致性检查失败，但继续执行")
                        # 优化提示词，供下一次生成使用
                        optimized_prompt = consistency_result.get('optimization_feedback', {}).get('optimized_prompt', f"{scene_prompt.get('parsed_prompt', '')}\n\n优化建议：请确保生成的内容与原视频高度一致，保持风格连贯性")
                        scene_prompt['parsed_prompt'] = optimized_prompt
                else:
                    self.log_step(f"场景{i+1}视频生成", f"失败: {video_result.get('error')}")
            
            # 计算成功生成的视频数量
            success_count = len([v for v in self.generated_videos if v['success']])
            total_count = len(self.generated_videos)
            self.log_step("场景视频生成", f"完成，生成{total_count}个场景视频，其中{success_count}个成功")
            return True
        except Exception as e:
            self.log_step("场景视频生成", f"失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def synthesize_audio(self):
        self.log_step("音频合成", "开始")
        
        try:
            # 初始化文本到语音服务
            from app.services.text_to_speech_service import TextToSpeechService
            self.content_generator = TextToSpeechService()
            
            # 测试语音一致性seed机制
            speaker_id = None
            voice_seed = None
            
            # 从第一个切片提取说话人信息
            if self.video_slices and 'audio_file' in self.video_slices[0]:
                audio_path = self.video_slices[0]['audio_file']
                if os.path.exists(audio_path):
                    self.log_step("音频合成", "提取说话人信息")
                    speaker_result = self.speaker_voice_service.extract_speakers_from_audio(audio_path)
                    if speaker_result.get('success') and speaker_result.get('speakers'):
                        speaker = speaker_result['speakers'][0]
                        speaker_id = speaker.get('speaker_id')
                        voice_seed = speaker.get('voice_seed')
                        self.log_step("音频合成", f"成功提取说话人: {speaker_id}, voice seed: {voice_seed}")
                        
                        # 保存说话人voice seed
                        save_result = self.speaker_voice_service.save_speaker_voice_seed(
                            speaker_id=speaker_id,
                            voice_seed=voice_seed,
                            audio_sample_path=audio_path
                        )
                        if save_result.get('success'):
                            self.log_step("音频合成", f"成功保存说话人voice seed")
            
            # 用于测试语音一致性的文本
            test_text = "这是一段测试文本，用于验证语音一致性"
            
            # 第一次生成音频
            first_audio_path = os.path.join(self.output_dir, "first_test_audio.mp3")
            if speaker_id:
                first_audio_result = self.speaker_tts_integration.generate_audio_with_speaker(
                    text=test_text,
                    speaker_id=speaker_id,
                    output_path=first_audio_path
                )
                if first_audio_result.get('success'):
                    self.log_step("音频合成", "成功生成第一次测试音频")
            
            # 第二次生成音频（使用相同的speaker_id）
            second_audio_path = os.path.join(self.output_dir, "second_test_audio.mp3")
            if speaker_id:
                second_audio_result = self.speaker_tts_integration.generate_audio_with_speaker(
                    text=test_text,
                    speaker_id=speaker_id,
                    output_path=second_audio_path
                )
                if second_audio_result.get('success'):
                    self.log_step("音频合成", "成功生成第二次测试音频")
                    self.log_step("音频合成", "语音一致性测试完成：使用相同的speaker_id生成了两次音频")
            
            for i, video in enumerate(self.generated_videos):
                if video['success']:
                    scene_prompt = self.scene_prompts[i]
                    text = scene_prompt.get('optimized_prompt', '')[:100]  # 限制文本长度，使用优化后的prompt
                    
                    # 使用speaker_tts_integration生成音频，确保语音一致性
                    audio_output_path = os.path.join(self.output_dir, f"scene_{i+1}_audio.mp3")
                    
                    if speaker_id:
                        self.log_step(f"场景{i+1}音频合成", "使用说话人识别和voice seed确保语音一致性")
                        audio_result = self.speaker_tts_integration.generate_audio_with_speaker(
                            text=text,
                            speaker_id=speaker_id,
                            output_path=audio_output_path
                        )
                    else:
                        self.log_step(f"场景{i+1}音频合成", "使用默认TTS")
                        audio_result = self.content_generator.text_to_speech(
                            text=text,
                            output_path=audio_output_path
                        )
                    
                    if audio_result.get('success'):
                        video['audio_path'] = audio_result.get('audio_path', '')
                        # 保存voice seed信息
                        if 'voice_seed' in audio_result:
                            video['voice_seed'] = audio_result['voice_seed']
                            self.log_step(f"场景{i+1}音频合成", f"保存voice seed: {audio_result['voice_seed']}")
            
            self.log_step("音频合成", "完成")
            return True
        except Exception as e:
            self.log_step("音频合成", f"失败: {str(e)}")
            return False
    
    async def compose_final_video(self):
        self.log_step("最终视频合成", "开始")
        
        try:
            # 为每个场景同步音频和视频
            scene_videos_with_audio = []
            # 使用所有生成的视频，无论其success状态如何
            for video in self.generated_videos:
                # 如果有音频路径，同步音频和视频
                if 'video_path' in video and video['video_path']:
                    if 'audio_path' in video and video['audio_path']:
                        synced_video = await self.ffmpeg_service.sync_audio_video(
                            video['video_path'],
                            video['audio_path'],
                            os.path.join(self.output_dir, f"scene_{video['scene_id']}_with_audio.mp4")
                        )
                        scene_videos_with_audio.append(synced_video)
                    else:
                        # 没有音频，直接使用视频
                        scene_videos_with_audio.append({
                            'output_path': video['video_path'],
                            'success': True
                        })
            
            # 合成所有场景视频
            if scene_videos_with_audio:
                final_video_path = os.path.join(self.output_dir, "final_composed_video.mp4")
                # 收集所有可用的视频路径
                video_paths = [v['output_path'] for v in scene_videos_with_audio if v['success'] and 'output_path' in v]
                
                if video_paths:
                    compose_result = await self.ffmpeg_service.compose_videos(
                        video_paths,
                        final_video_path
                    )
                    
                    if compose_result.get('success'):
                        self.log_step("最终视频合成", f"完成，最终视频路径: {final_video_path}")
                        return final_video_path
                    else:
                        self.log_step("最终视频合成", f"失败: {compose_result.get('error', '未知错误')}")
                        return None
            
            self.log_step("最终视频合成", "失败，没有可合成的场景视频")
            return None
        except Exception as e:
            self.log_step("最终视频合成", f"失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run_workflow(self):
        self.log_step("完整流程", "开始")
        
        # 执行流程步骤
        steps = [
            ("切片视频", self.slice_video),
            ("分析视频切片", self.analyze_video_slices),
            ("结合和优化提示词", lambda: asyncio.to_thread(self.combine_and_optimize_prompts)),
            ("解析JSON提示词", lambda: asyncio.to_thread(self.parse_json_prompts)),
            ("生成场景视频", self.generate_scene_videos),
            ("合成音频", self.synthesize_audio),
            ("合成最终视频", self.compose_final_video)
        ]
        
        for step_name, step_func in steps:
            try:
                if not await step_func():
                    self.log_step("完整流程", f"警告：步骤 '{step_name}' 执行失败，但继续执行后续步骤")
            except Exception as e:
                self.log_step("完整流程", f"错误：步骤 '{step_name}' 执行异常: {str(e)}")
                import traceback
                traceback.print_exc()
                # 继续执行后续步骤，不中断流程
        
        self.log_step("完整流程", "完成")
        return True

async def main():
    if len(sys.argv) != 2:
        print(f"用法: python {sys.argv[0]} <视频文件路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在 - {video_path}")
        sys.exit(1)
    
    # 创建测试实例并运行
    test = VideoProcessingTest(video_path, slice_count=5)
    await test.run_workflow()

if __name__ == "__main__":
    asyncio.run(main())
