import os
import sys
import requests
from typing import Optional, Dict, Any
# 注释掉LangChain相关导入，使用简化版本
# from langchain.schema import BaseRetriever
# from langchain.callbacks.manager import CallbackManagerForRetrieverRun
# from langchain.schema import Document
from pydantic import Field

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

class SiliconFlowSpeechRecognizer:
    """
    SiliconFlow语音识别服务封装类
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.SILICONFLOW_API_KEY
        self.base_url = Config.SILICONFLOW_BASE_URL
        self.transcription_url = f"{self.base_url}/audio/transcriptions"
        
        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError("请在config.py中设置有效的SILICONFLOW_API_KEY")
    
    def transcribe_audio(self, audio_file_path: str, model: str = "FunAudioLLM/SenseVoiceSmall") -> Dict[str, Any]:
        """
        转录音频文件为文本
        
        Args:
            audio_file_path: 音频文件路径
            model: 使用的模型名称
            
        Returns:
            包含转录结果的字典
        """
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
                
                # 发送请求
                response = requests.post(
                    self.transcription_url,
                    headers=headers,
                    files=files,
                    timeout=60
                )
            
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
    

# 简化的非LangChain版本（推荐使用）
class SimpleSpeechRecognizer:
    """
    简化的语音识别器，不依赖LangChain，推荐使用
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.recognizer = SiliconFlowSpeechRecognizer(api_key)
    
    def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """转录音频文件，返回详细结果"""
        return self.recognizer.transcribe_audio(audio_file_path)
    


# 使用示例
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
    