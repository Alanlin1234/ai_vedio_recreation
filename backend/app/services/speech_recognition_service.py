import os
import sys
import requests
from typing import Optional, Dict, Any

from pydantic import Field

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

class SiliconFlowSpeechRecognizer:
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        self.transcription_url = f"{self.base_url}/audio/transcriptions"
        
        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError("请在config.py中设置有效的SILICONFLOW_API_KEY")
    
    def transcribe_audio(self, audio_file_path: str, model: str = "FunAudioLLM/SenseVoiceSmall") -> Dict[str, Any]:
        try:
            # 检查文件是否存在
            if not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"音频文件不存在: {audio_file_path}")
            
            # 准备请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 准备文件和数据
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg'),
                    'model': (None, model)
                }
                
                # 发送请求，增加超时时间并添加重试机制
                import time
                max_retries = 3
                timeout = 120
                
                for retry in range(max_retries):
                    try:
                        response = requests.post(
                            self.transcription_url,
                            headers=headers,
                            files=files,
                            timeout=timeout
                        )
                        # 如果请求成功，跳出循环
                        if response.status_code == 200:
                            break
                        # 如果是网络错误，继续重试
                    except requests.exceptions.RequestException as e:
                        if retry < max_retries - 1:
                            print(f"重试第 {retry + 1} 次...")
                            time.sleep(5)
                        else:
                            raise e
            
            # 处理响应
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'text': result.get('text', ''),
                    'status_code': response.status_code
                }
            else:
                error_msg = f"API调用失败，状态码: {response.status_code}"
                if response.text:
                    error_msg += f"，错误信息: {response.text}"
                
                return {
                    'success': False,
                    'error': error_msg,
                    'status_code': response.status_code,
                    'text': ''
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"网络请求错误: {str(e)}",
                'text': ''
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"转录过程中发生错误: {str(e)}",
                'text': ''
            }
    

# 简化版本（推荐使用）
class SimpleSpeechRecognizer:
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            self.recognizer = SiliconFlowSpeechRecognizer(api_key)
        except ValueError:
            # 如果SiliconFlow API密钥无效，跳过初始化，在transcribe方法中返回模拟结果
            self.recognizer = None
            print("[语音识别] SiliconFlow API密钥无效，将使用模拟结果")
    
    def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """转录音频文件，返回详细结果"""
        if self.recognizer:
            return self.recognizer.transcribe_audio(audio_file_path)
        else:
            # 模拟语音识别结果
            return {
                'success': True,
                'text': '这是一段模拟的语音识别结果，实际应用中请配置有效的SILICONFLOW_API_KEY',
                'status_code': 200
            }
    

# 测试代码
if __name__ == "__main__":
    # 示例音频文件路径
    audio_file = "e:/视频生成Agent/backend/video/20250604/7511717082225921334.mp3"
    
    
    print("\n=== 方式2：使用SimpleSpeechRecognizer（推荐） ===")
    try:
        simple_recognizer = SimpleSpeechRecognizer()
        
        # 详细结果
        result = simple_recognizer.transcribe(audio_file)
        print(f"详细结果: {result}")
        
        
    except Exception as e:
        print(f"方式2出错: {e}")
    
