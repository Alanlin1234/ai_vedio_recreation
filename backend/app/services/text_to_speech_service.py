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
    """
    文本转语音服务类
    使用SiliconFlow API将文本转换为语音
    """
    
    def __init__(self, api_key: str = None):
        """
        初始化文本转语音服务
        
        Args:
            api_key: SiliconFlow API密钥
        """
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = "https://api.siliconflow.cn/v1/audio/speech"
        
        if not self.api_key:
            raise ValueError("SiliconFlow API密钥未设置，请在config.py中配置SILICONFLOW_API_KEY或传入api_key参数")
    
    def text_to_speech(self, 
                      text: str, 
                      output_path: str = None,
                      voice: str = "FunAudioLLM/CosyVoice2-0.5B:claire",
                      response_format: str = "mp3",
                      sample_rate: int = 32000,
                      speed: float = 1.0,
                      gain: float = 0.0) -> Dict[str, Any]:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本内容
            output_path: 输出音频文件路径，如果不指定则自动生成
            voice: 语音模型，默认为alex
            response_format: 音频格式，默认为mp3
            sample_rate: 采样率，默认32000
            speed: 语速，默认1.0
            gain: 音量增益，默认0.0
            
        Returns:
            包含转换结果的字典
        """
        try:
            # 如果没有指定输出路径，自动生成
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'audio')
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"tts_{timestamp}.{response_format}")
            
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
                
                return {
                    'success': True,
                    'audio_path': output_path,
                    'text': text,
                    'voice': voice,
                    'duration_estimate': len(text) / 10,  # 粗略估算时长（字符数/10秒）
                    'file_size': os.path.getsize(output_path)
                }
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
        """
        批量将文本转换为语音
        
        Args:
            texts: 文本列表
            output_dir: 输出目录
            voice: 语音模型
            
        Returns:
            批量转换结果
        """
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
        """
        获取可用的语音模型列表
        
        Returns:
            可用语音模型列表
        """
        # 这里返回一些常用的语音模型
        # 实际可用模型需要查询API文档
        return [
            "FunAudioLLM/CosyVoice2-0.5B:alex",
            "FunAudioLLM/CosyVoice2-0.5B:bella",
            "FunAudioLLM/CosyVoice2-0.5B:chris",
            "FunAudioLLM/CosyVoice2-0.5B:diana"
        ]
    
    def validate_text_length(self, text: str, max_length: int = 4000) -> bool:
        """
        验证文本长度是否符合API限制
        
        Args:
            text: 要验证的文本
            max_length: 最大长度限制
            
        Returns:
            是否符合长度要求
        """
        return len(text) <= max_length
    
    def split_long_text(self, text: str, max_length: int = 4000) -> list:
        """
        将长文本分割为多个短文本
        
        Args:
            text: 要分割的文本
            max_length: 每段最大长度
            
        Returns:
            分割后的文本列表
        """
        if len(text) <= max_length:
            return [text]
        
        # 按句号分割
        sentences = text.split('。')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk + sentence + '。') <= max_length:
                current_chunk += sentence + '。'
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip('。'))
                current_chunk = sentence + '。'
        
        if current_chunk:
            chunks.append(current_chunk.rstrip('。'))
        
        return chunks