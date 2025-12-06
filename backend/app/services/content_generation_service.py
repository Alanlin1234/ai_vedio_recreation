import os
import sys
from typing import Dict, List, Any
import dashscope
from dashscope import MultiModalConversation, Generation

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config
from .text_to_speech_service import TextToSpeechService

class ContentGenerationService:
    """
    内容生成服务类
    负责生成二创文案和文生视频提示词
    """
    
    def __init__(self):
        dashscope.api_key = Config.DASHSCOPE_API_KEY
        self.tts_service = TextToSpeechService()
    
    def generate_recreation_content(self, video_understanding: Dict, audio_text: str, scene_segments: List[Dict]) -> Dict[str, Any]:
        """
        生成二创文案内容
        
        Args:
            video_understanding: 视频理解结果
            audio_text: 音频转文本结果
            scene_segments: 场景分割结果
            
        Returns:
            二创文案内容
        """
        try:
            # 构建提示词
            prompt = self.build_recreation_prompt(video_understanding, audio_text, scene_segments)
            
            # 调用大模型生成内容
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的视频内容创作者，擅长根据原视频内容创作吸引人的二创文案。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                messages=messages
            )
            
            if response and response.output and response.output.choices:
                content = response.output.choices[0].message.content[0]["text"]
                
                return {
                    'success': True,
                    'content': content,
                    'prompt_used': prompt
                }
            else:
                return {
                    'success': False,
                    'content': '',
                    'error': '大模型响应为空'
                }
                
        except Exception as e:
            return {
                'success': False,
                'content': '',
                'error': str(e)
            }
    
    def generate_video_prompts(self, scene_segments: List[Dict], recreation_content: Dict, original_understanding: Dict) -> List[Dict[str, Any]]:
        """
        为每个场景生成文生视频提示词
        
        Args:
            scene_segments: 场景分割结果
            recreation_content: 二创文案内容
            original_understanding: 原视频理解结果
            
        Returns:
            每个场景的文生视频提示词
        """
        video_prompts = []
        
        # 提取人物和风格信息
        character_info = self.extract_character_info(original_understanding)
        style_info = self.extract_style_info(original_understanding)
        
        for scene in scene_segments:
            try:
                prompt = self.generate_scene_video_prompt(
                    scene=scene,
                    character_info=character_info,
                    style_info=style_info,
                    recreation_content=recreation_content
                )
                
                video_prompts.append({
                    'scene_id': scene['scene_id'],
                    'start_time': scene['start_time'],
                    'end_time': scene['end_time'],
                    'duration': scene['duration'],
                    'video_prompt': prompt,
                    'character_consistency': character_info,
                    'style_consistency': style_info
                })
                
            except Exception as e:
                print(f"生成场景{scene['scene_id']}提示词失败: {e}")
                video_prompts.append({
                    'scene_id': scene['scene_id'],
                    'start_time': scene['start_time'],
                    'end_time': scene['end_time'],
                    'duration': scene['duration'],
                    'video_prompt': f"场景{scene['scene_id']}提示词生成失败",
                    'error': str(e)
                })
        
        return video_prompts
    
    def build_recreation_prompt(self, video_understanding: Dict, audio_text: str, scene_segments: List[Dict]) -> str:
        """
        构建二创文案生成提示词
        """
        scene_info = "\n".join([f"场景{s['scene_id']}: {s['start_time_str']} - {s['end_time_str']} (时长: {s['duration']:.1f}秒)" for s in scene_segments])
        
        prompt = f"""
        请根据以下信息创作一个吸引人的视频二创文案：
        
        【原视频理解】：
        {video_understanding.get('content_understanding', '无视频理解内容')}
        
        【音频转录内容】：
        {audio_text if audio_text else '无音频内容'}
        
        【场景分割信息】：
        {scene_info}
        
        请创作要求：
        1. 保持原视频的核心信息和价值
        2. 语言要生动有趣，适合短视频传播
        3. 结构清晰，有开头、发展、高潮、结尾
        4. 字数控制在200-500字之间
        5. 要有吸引人的标题
        6. 适合配音和视觉呈现
        
        请按以下格式输出：
        【标题】：
        【文案内容】：
        【关键词】：
        【适合平台】：
        """
        
        return prompt
    
    def extract_character_info(self, understanding: Dict) -> Dict[str, str]:
        """
        提取人物信息以保持一致性
        """
        content = understanding.get('content_understanding', '')
        
        # 简单的人物信息提取（可以用更复杂的NLP方法）
        character_info = {
            'gender': '未知',
            'age_range': '未知',
            'appearance': '未知',
            'clothing': '未知',
            'expression': '未知'
        }
        
        # 这里可以添加更复杂的人物信息提取逻辑
        if '男' in content:
            character_info['gender'] = '男性'
        elif '女' in content:
            character_info['gender'] = '女性'
        
        return character_info
    
    def extract_style_info(self, understanding: Dict) -> Dict[str, str]:
        """
        提取风格信息以保持一致性
        """
        content = understanding.get('content_understanding', '')
        
        style_info = {
            'visual_style': '现实主义',
            'color_tone': '自然色调',
            'lighting': '自然光',
            'camera_style': '平稳拍摄',
            'mood': '中性'
        }
        
        # 这里可以添加更复杂的风格信息提取逻辑
        return style_info
    
    def generate_scene_video_prompt(self, scene: Dict, character_info: Dict, style_info: Dict, recreation_content: Dict) -> str:
        """
        为单个场景生成文生视频提示词
        """
        base_prompt = f"""
        场景{scene['scene_id']}视频生成提示词：
        
        【时长】：{scene['duration']:.1f}秒
        
        【人物一致性】：
        - 性别：{character_info['gender']}
        - 年龄：{character_info['age_range']}
        - 外观：{character_info['appearance']}
        - 服装：{character_info['clothing']}
        
        【风格一致性】：
        - 视觉风格：{style_info['visual_style']}
        - 色调：{style_info['color_tone']}
        - 光线：{style_info['lighting']}
        - 拍摄风格：{style_info['camera_style']}
        
        【场景描述】：
        根据二创文案第{scene['scene_id']}部分的内容，展现相应的视觉场景。
        保持人物和风格的一致性，确保视频流畅自然。
        
        【技术参数】：
        - 分辨率：1920x1080
        - 帧率：30fps
        - 时长：{scene['duration']:.1f}秒
        - 运动：平滑自然
        """
        
        return base_prompt.strip()
    
    def generate_new_script_with_qwen_plus(self, video_understanding: Dict, audio_text: str, original_script_length: int = None) -> Dict[str, Any]:
        """
        使用qwen-plus模型生成新的文案
        
        Args:
            video_understanding: 视频理解结果
            audio_text: 音频转文本结果
            original_script_length: 原文案长度（字符数），用于控制新文案长度
            
        Returns:
            生成的新文案结果
        """
        try:
            # 估算原文案长度
            if not original_script_length and audio_text:
                original_script_length = len(audio_text)
            elif not original_script_length:
                original_script_length = 300  # 默认长度
            
            # 构建提示词
            prompt = self.build_new_script_prompt(video_understanding, audio_text, original_script_length)
            
            # 调用qwen-plus模型生成文案
            messages = [
                {
                    'role': 'system',
                    'content': '你是一个专业的视频内容创作者，擅长根据视频内容和语音转录创作吸引人的新文案。你的文案要简洁有力，适合短视频传播。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
            
            response = Generation.call(
                model='qwen-plus',
                messages=messages,
                temperature=0.8,
                max_tokens=1000
            )
            
            if response and response.output and response.output.text:
                generated_script = response.output.text.strip()
                
                return {
                    'success': True,
                    'script': generated_script,
                    'script_length': len(generated_script),
                    'original_length': original_script_length,
                    'prompt_used': prompt
                }
            else:
                return {
                    'success': False,
                    'script': '',
                    'error': 'qwen-plus模型响应为空'
                }
                
        except Exception as e:
            return {
                'success': False,
                'script': '',
                'error': f'文案生成失败: {str(e)}'
            }
    
    def build_new_script_prompt(self, video_understanding: Dict, audio_text: str, target_length: int) -> str:
        """
        构建新文案生成的提示词
        
        Args:
            video_understanding: 视频理解结果
            audio_text: 音频转文本结果
            target_length: 目标文案长度
            
        Returns:
            构建的提示词
        """
        prompt = f"""
请根据以下信息创作一个全新的视频文案：

【视频理解内容】：
{video_understanding.get('content_understanding', '无视频理解内容')}

【原始语音转录】：
{audio_text if audio_text else '无音频内容'}

【文案创作要求】：
1. 文案长度控制在{target_length-50}到{target_length+50}个字符之间
2. 保持原视频的核心主题和价值观
3. 语言要生动有趣，适合现代短视频观众
4. 结构清晰，有吸引人的开头和有力的结尾
5. 避免直接复制原文，要有创新和改进
6. 适合配音朗读，语言流畅自然
7. 突出重点信息，删除冗余内容
8. 使用现代化的表达方式和网络流行语（适度）

【输出格式】：
请直接输出文案内容，不需要额外的说明或标题。
        """
        
        return prompt.strip()
    
    def generate_script_and_audio(self, video_understanding: Dict, audio_text: str, 
                                 output_audio_path: str = None, 
                                 voice: str = "FunAudioLLM/CosyVoice2-0.5B:alex") -> Dict[str, Any]:
        """
        生成新文案并转换为语音
        
        Args:
            video_understanding: 视频理解结果
            audio_text: 音频转文本结果
            output_audio_path: 输出音频文件路径
            voice: 语音模型
            
        Returns:
            包含文案和音频的完整结果
        """
        try:
            # 1. 生成新文案
            print("正在生成新文案...")
            script_result = self.generate_new_script_with_qwen_plus(video_understanding, audio_text)
            
            if not script_result['success']:
                return {
                    'success': False,
                    'error': f"文案生成失败: {script_result['error']}"
                }
            
            generated_script = script_result['script']
            print(f"文案生成成功，长度: {len(generated_script)}字符")
            print(f"生成的文案: {generated_script[:100]}{'...' if len(generated_script) > 100 else ''}")
            
            # 2. 将文案转换为语音
            print("正在将文案转换为语音...")
            
            # 检查文案长度，如果太长则分割
            if len(generated_script) > 4000:
                text_chunks = self.tts_service.split_long_text(generated_script)
                print(f"文案较长，分割为{len(text_chunks)}段")
                
                # 批量转换
                audio_result = self.tts_service.batch_text_to_speech(
                    texts=text_chunks,
                    output_dir=os.path.dirname(output_audio_path) if output_audio_path else None,
                    voice=voice
                )
            else:
                # 单次转换
                audio_result = self.tts_service.text_to_speech(
                    text=generated_script,
                    output_path=output_audio_path,
                    voice=voice
                )
            
            if not audio_result['success']:
                return {
                    'success': False,
                    'script': generated_script,
                    'script_result': script_result,
                    'error': f"语音合成失败: {audio_result['error']}"
                }
            
            print("语音合成成功！")
            
            return {
                'success': True,
                'script': generated_script,
                'script_result': script_result,
                'audio_result': audio_result,
                'audio_path': audio_result.get('audio_path') or audio_result.get('output_dir'),
                'script_length': len(generated_script),
                'voice_used': voice
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"文案生成和语音合成过程中发生错误: {str(e)}"
            }
    
    def generate_new_script(self, video_understanding: str, original_script: str) -> Dict[str, Any]:
        """
        生成新文案的简化接口
        
        Args:
            video_understanding: 视频理解内容（字符串）
            original_script: 原始文案
            
        Returns:
            生成的新文案结果
        """
        try:
            # 构建视频理解字典格式
            video_understanding_dict = {
                'content_understanding': video_understanding
            }
            
            # 调用完整的文案生成方法
            result = self.generate_new_script_with_qwen_plus(
                video_understanding=video_understanding_dict,
                audio_text=original_script
            )
            
            if result['success']:
                return {
                    'success': True,
                    'new_script': result['script']
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def text_to_speech(self, text: str, output_path: str) -> Dict[str, Any]:
        """
        文本转语音
        
        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            
        Returns:
            转换结果
        """
        try:
            result = self.tts_service.text_to_speech(
                text=text,
                output_path=output_path
            )
            
            if result['success']:
                return {
                    'success': True,
                    'audio_path': result.get('audio_path', output_path)
                }
            else:
                return {
                    'success': False,
                    'error': result['error']
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def compose_videos(self, video_paths: List[str], output_path: str) -> Dict[str, Any]:
        """
        拼接多个视频文件
        
        Args:
            video_paths: 视频文件路径列表
            output_path: 输出视频路径
            
        Returns:
            拼接结果
        """
        try:
            import moviepy.editor as mp
            
            if not video_paths:
                return {
                    'success': False,
                    'error': '没有提供视频文件'
                }
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 加载所有视频片段
            video_clips = []
            for video_path in video_paths:
                if os.path.exists(video_path):
                    clip = mp.VideoFileClip(video_path)
                    video_clips.append(clip)
                else:
                    print(f"警告：视频文件不存在: {video_path}")
            
            if not video_clips:
                return {
                    'success': False,
                    'error': '没有有效的视频文件'
                }
            
            # 拼接视频
            final_video = mp.concatenate_videoclips(video_clips)
            
            # 输出最终视频
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 清理资源
            for clip in video_clips:
                clip.close()
            final_video.close()
            
            return {
                'success': True,
                'output_path': output_path,
                'video_count': len(video_clips)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_audio_video(self, video_path: str, audio_path: str, output_path: str) -> Dict[str, Any]:
        """
        音画同步
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            
        Returns:
            同步结果
        """
        try:
            import moviepy.editor as mp
            
            if not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': f'视频文件不存在: {video_path}'
                }
            
            if not os.path.exists(audio_path):
                return {
                    'success': False,
                    'error': f'音频文件不存在: {audio_path}'
                }
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 加载视频和音频
            video_clip = mp.VideoFileClip(video_path)
            audio_clip = mp.AudioFileClip(audio_path)
            
            # 调整音频长度以匹配视频
            if audio_clip.duration > video_clip.duration:
                # 音频较长，截取
                audio_clip = audio_clip.subclip(0, video_clip.duration)
            elif audio_clip.duration < video_clip.duration:
                # 音频较短，循环播放或静音填充
                if audio_clip.duration > 0:
                    # 循环播放音频直到匹配视频长度
                    loops_needed = int(video_clip.duration / audio_clip.duration) + 1
                    audio_clips = [audio_clip] * loops_needed
                    extended_audio = mp.concatenate_audioclips(audio_clips)
                    audio_clip = extended_audio.subclip(0, video_clip.duration)
            
            # 将音频设置到视频
            final_video = video_clip.set_audio(audio_clip)
            
            # 输出最终视频
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # 清理资源
            video_clip.close()
            audio_clip.close()
            final_video.close()
            
            return {
                'success': True,
                'output_path': output_path,
                'video_duration': video_clip.duration,
                'audio_duration': audio_clip.duration
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }