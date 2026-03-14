import os
import sys
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

class TextToSpeechService:
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = "https://api.siliconflow.cn/v1/audio/speech"
        
        if not self.api_key:
            
            print(" SiliconFlow API密钥未设置")
            self.api_key = None
    
    def text_to_speech(self, 
                      text: str, 
                      output_path: str = None,
                      voice: str = "FunAudioLLM/CosyVoice2-0.5B:claire",
                      response_format: str = "mp3",
                      sample_rate: int = 32000,
                      speed: float = 1.0,
                      gain: float = 0.0,
                      voice_seed: Optional[str] = None,
                      speaker_id: Optional[str] = None) -> Dict[str, Any]:
        # 检查API密钥是否已设置
        if not self.api_key:
            # 模拟文本转语音结果
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'audio')
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"tts_{timestamp}.{response_format}")
            
            # 创建一个空的音频文件作为模拟结果
            open(output_path, 'a').close()
            
            print(f"[模拟] 语音合成成功，文件保存至: {output_path}")
            
            return {
                'success': True,
                'audio_path': output_path,
                'text': text,
                'voice': voice,
                'duration_estimate': len(text) / 10,  # 粗略估算时长（字符数/10秒）
                'file_size': 0  # 空文件大小为0
            }
        
        try:
            # 正常API调用逻辑
            
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'audio')
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"tts_{timestamp}.{response_format}")
            
            # 如果提供了speaker_id，尝试获取对应的voice_seed
            if speaker_id and not voice_seed:
                from app.services.speaker_voice_service import SpeakerVoiceService
                speaker_service = SpeakerVoiceService()
                voice_seed = speaker_service.get_speaker_voice_seed(speaker_id)
                if voice_seed:
                    print(f"[TTS] 使用说话人 {speaker_id} 的voice seed: {voice_seed}")
            
            # 构建请求参数
            payload = {
                "model": "FunAudioLLM/CosyVoice2-0.5B",
                "input": text,
                "voice": voice,
                "response_format": response_format,
                "sample_rate": sample_rate,
                "stream": False,  # 设置为False以获取完整音频
                "speed": speed,
                "gain": gain
            }
            
            # 如果提供了voice_seed，添加到请求参数中
            # 注意：不同TTS API的seed参数名称可能不同，需要根据实际情况调整
            if voice_seed:
                # 尝试作为seed参数（某些API支持）
                try:
                    seed_int = int(voice_seed)
                    payload["seed"] = seed_int
                    print(f"[TTS] 使用voice seed: {seed_int}")
                except ValueError:
                    print(f"[TTS] 警告: voice_seed不是有效整数，将忽略: {voice_seed}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            print(f"正在将文本转换为语音...")
            print(f"文本内容: {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # 发送请求
            response = requests.post(self.base_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                # 保存音频文件
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"语音合成成功，文件保存至: {output_path}")
                
                result = {
                    'success': True,
                    'audio_path': output_path,
                    'text': text,
                    'voice': voice,
                    'duration_estimate': len(text) / 10,  # 粗略估算时长（字符数/10秒）
                    'file_size': os.path.getsize(output_path)
                }
                
                # 添加voice_seed信息到结果中
                if voice_seed:
                    result['voice_seed'] = voice_seed
                if speaker_id:
                    result['speaker_id'] = speaker_id
                
                return result
            else:
                error_msg = f"API请求失败，状态码: {response.status_code}, 响应: {response.text}"
                print(f"语音合成失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            error_msg = f"语音合成过程中发生错误: {str(e)}"
            print(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def batch_text_to_speech(self, 
                           texts: list, 
                           output_dir: str = None,
                           voice: str = "FunAudioLLM/CosyVoice2-0.5B:alex") -> Dict[str, Any]:
        if not output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'audio', f'batch_{timestamp}')
        
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        for i, text in enumerate(texts):
            output_path = os.path.join(output_dir, f"audio_{i+1:03d}.mp3")
            result = self.text_to_speech(text, output_path, voice)
            result['index'] = i + 1
            results.append(result)
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            'success': success_count > 0,
            'total_count': len(texts),
            'success_count': success_count,
            'failed_count': len(texts) - success_count,
            'results': results,
            'output_dir': output_dir
        }
    
    def get_available_voices(self) -> list:
        # 这里返回一些常用的语音模型
        # 实际可用模型需要查询API文档
        return [
            "FunAudioLLM/CosyVoice2-0.5B:alex",
            "FunAudioLLM/CosyVoice2-0.5B:bella",
            "FunAudioLLM/CosyVoice2-0.5B:chris",
            "FunAudioLLM/CosyVoice2-0.5B:diana"
        ]
    
    def validate_text_length(self, text: str, max_length: int = 4000) -> bool:
        return len(text) <= max_length
    
    def sync_audio_video(self, video_path: str, audio_path: str, output_path: str) -> Dict[str, Any]:
        """
        音画同步，将音频合并到视频中
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            
        Returns:
            包含success和output_path的字典
        """
        try:
            import subprocess
            import os
            
            print(f"[音画同步] 开始合并音频 {audio_path} 到视频 {video_path}")
            print(f"[音画同步] 输出路径: {output_path}")
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # 构建FFmpeg命令
            # 使用-shortest参数确保输出视频时长与较短的媒体一致
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',  # 复制视频流，不重新编码
                '-c:a', 'aac',     # 重新编码音频为AAC
                '-shortest',       # 输出视频时长与较短的媒体一致
                '-strict', 'experimental',
                output_path
            ]
            
            # 执行FFmpeg命令
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"[音画同步] 音画同步成功: {output_path}")
                return {
                    'success': True,
                    'output_path': output_path,
                    'video_path': video_path,
                    'audio_path': audio_path
                }
            else:
                error_msg = f"[音画同步] FFmpeg执行失败: {result.stderr}"
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg,
                    'returncode': result.returncode
                }
                
        except Exception as e:
            error_msg = f"[音画同步] 音画同步失败: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
