import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import Field
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.outputs import ChatResult, ChatGeneration
from dashscope import MultiModalConversation

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import config

class DashScopeChatModel(BaseChatModel):
    """基于DashScope的LangChain聊天模型包装器"""
    
    api_key: str = Field(default="")
    model_name: str = Field(default="qwen-vl-max-latest")
    
    def __init__(self, api_key: str = None, model_name: str = "qwen-vl-max-latest", **kwargs):
        # 设置默认值
        if api_key is None:
            api_key = config.DASHSCOPE_API_KEY
        
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)
        
        if not self.api_key:
            raise ValueError("API密钥未提供且在配置中未找到DASHSCOPE_API_KEY")
    
    @property
    def _llm_type(self) -> str:
        return "dashscope"
    
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """调用DashScope API生成响应"""
        try:
            print(f"[DashScope] 开始API调用，模型: {self.model_name}")
            
            # 转换LangChain消息格式为DashScope格式
            dashscope_messages = self._convert_messages(messages)
            print(f"[DashScope] 消息转换完成，消息数量: {len(dashscope_messages)}")
            
            # 打印第一个消息的内容类型（用于调试）
            if dashscope_messages:
                first_msg = dashscope_messages[0]
                print(f"[DashScope] 第一个消息角色: {first_msg.get('role')}")
                if 'content' in first_msg and isinstance(first_msg['content'], list):
                    content_types = [list(item.keys())[0] if item else 'empty' for item in first_msg['content']]
                    print(f"[DashScope] 内容类型: {content_types}")
            
            print(f"[DashScope] 开始调用MultiModalConversation.call")
            response = MultiModalConversation.call(
                api_key=self.api_key,
                model=self.model_name,
                messages=dashscope_messages
            )
            
            print(f"[DashScope] API调用完成")
            
            if response is None:
                raise Exception("API响应为空")
            
            print(f"[DashScope] 响应对象类型: {type(response)}")
            
            # 检查响应状态
            if hasattr(response, 'status_code'):
                print(f"[DashScope] 响应状态码: {response.status_code}")
                if response.status_code != 200:
                    error_msg = f"API调用失败，状态码: {response.status_code}"
                    if hasattr(response, 'message'):
                        error_msg += f", 错误信息: {response.message}"
                    raise Exception(error_msg)
            
            if not hasattr(response, 'output') or response.output is None:
                print(f"[DashScope] 响应对象属性: {dir(response)}")
                raise Exception("API响应格式错误：缺少output字段")
            
            print(f"[DashScope] output对象类型: {type(response.output)}")
            
            if not hasattr(response.output, 'choices') or not response.output.choices:
                print(f"[DashScope] output对象属性: {dir(response.output)}")
                raise Exception("API响应格式错误：缺少choices字段")
            
            print(f"[DashScope] choices数量: {len(response.output.choices)}")
            
            choice = response.output.choices[0]
            print(f"[DashScope] 第一个choice类型: {type(choice)}")
            
            if not hasattr(choice, 'message'):
                print(f"[DashScope] choice对象属性: {dir(choice)}")
                raise Exception("API响应格式错误：choice缺少message字段")
            
            message = choice.message
            print(f"[DashScope] message类型: {type(message)}")
            
            if not hasattr(message, 'content'):
                print(f"[DashScope] message对象属性: {dir(message)}")
                raise Exception("API响应格式错误：message缺少content字段")
            
            content_data = message.content
            print(f"[DashScope] content类型: {type(content_data)}")
            
            if isinstance(content_data, list) and len(content_data) > 0:
                if isinstance(content_data[0], dict) and "text" in content_data[0]:
                    content = content_data[0]["text"]
                else:
                    content = str(content_data[0])
            else:
                content = str(content_data)
            
            print(f"[DashScope] 提取的内容长度: {len(content)}")
            
            generation = ChatGeneration(message=HumanMessage(content=content))
            return ChatResult(generations=[generation])
            
        except Exception as e:
            print(f"[DashScope] API调用异常: {str(e)}")
            print(f"[DashScope] 异常类型: {type(e).__name__}")
            import traceback
            print(f"[DashScope] 异常堆栈: {traceback.format_exc()}")
            raise Exception(f"DashScope API调用失败: {str(e)}")
    
    def _convert_messages(self, messages: list[BaseMessage]) -> list[Dict[str, Any]]:
        """将LangChain消息格式转换为DashScope格式"""
        dashscope_messages = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                dashscope_messages.append({
                    'role': 'system',
                    'content': [{'text': message.content}]
                })
            elif isinstance(message, HumanMessage):
                # 检查是否包含视频内容
                if hasattr(message, 'additional_kwargs') and 'video_path' in message.additional_kwargs:
                    video_path = message.additional_kwargs['video_path']
                    fps = message.additional_kwargs.get('fps', 10)
                    dashscope_messages.append({
                        'role': 'user',
                        'content': [
                            {'video': f"file://{os.path.abspath(video_path)}", "fps": fps},
                            {'text': message.content}
                        ]
                    })
                else:
                    dashscope_messages.append({
                        'role': 'user',
                        'content': [{'text': message.content}]
                    })
        
        return dashscope_messages

class VideoAnalysisAgent:
    """基于LangChain的视频分析智能体"""
    
    def __init__(self, api_key: str = None, model_name: str = "qwen-vl-max-latest"):
        """初始化视频分析智能体
        :param api_key: 可选，如果不传则从config中读取
        :param model_name: 使用的模型名称
        """
        self.llm = DashScopeChatModel(
            api_key=api_key,
            model_name=model_name
        )
        
        # 定义系统提示词
        self.system_prompt = (
            "你是一个专业的视频内容分析师，专门负责深度理解视频内容和画面细节。请按照以下要求进行分析：\n\n"
            "**核心任务：**\n"
            "1. 详细描述视频的整体内容和故事情节\n"
            "2. 逐个分析视频中的关键画面和场景\n"
            "3. 描述每个画面中的具体元素和细节\n\n"
            "**分析维度：**\n"
            "1. 视频内容理解：\n"
            "   - 主要内容和故事线\n"
            "   - 关键事件和转折点\n"
            "   - 整体叙事结构\n"
            "   - 传达的核心信息\n\n"
            "2. 画面场景分析：\n"
            "   - 按时间顺序描述关键画面\n"
            "   - 每个场景的具体内容（人物、物体、环境）\n"
            "   - 画面构图和视觉元素\n"
            "   - 色彩、光线、氛围\n"
            "   - 镜头运动和拍摄角度\n\n"
            "3. 细节描述：\n"
            "   - 人物表情、动作、服装\n"
            "   - 环境背景和道具\n"
            "   - 文字、标识、符号\n"
            "   - 特殊效果和视觉元素\n\n"
            "请用详细、具体、生动的语言描述，让读者能够通过你的描述完全理解视频内容和画面细节。"
        )
    
    def understand_video_content_and_scenes(
        self, 
        video_path: str, 
        fps: int = 10
    ) -> Dict[str, Any]:
        """深度理解视频内容和各个画面场景
        :param video_path: 视频本地绝对路径
        :param fps: 分析帧率
        :return: 视频理解结果字典
        """
        start_time = time.time()
        
        try:
            print(f"[视频理解] 开始分析视频: {video_path}")
            
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                error_msg = f"视频文件不存在: {video_path}"
                print(f"[视频理解] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "video_path": os.path.abspath(video_path),
                    "timestamp": datetime.now().isoformat(),
                    "content": None
                }
            
            print(f"[视频理解] 视频文件存在，开始构建消息")
            
            # 构建消息链
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(
                    content="请深度分析这个视频，重点关注：1）视频的整体内容和故事情节；2）逐个描述视频中的关键画面和场景；3）详细描述每个画面中的具体元素、人物、环境、色彩等细节。请用生动具体的语言，让我能够完全理解视频的内容和每个画面的细节。",
                    additional_kwargs={
                        'video_path': video_path,
                        'fps': fps
                    }
                )
            ]
            
            print(f"[视频理解] 消息构建完成，开始调用DashScope API")
            print(f"[视频理解] 使用模型: {self.llm.model_name}")
            print(f"[视频理解] API Key前缀: {self.llm.api_key[:10]}...")
            
            # 调用LangChain模型
            result = self.llm.generate([messages])
            analysis_result = result.generations[0][0].message.content
            
            time_cost = time.time() - start_time
            print(f"[视频理解] API调用成功，耗时: {time_cost:.2f}秒")
            print(f"[视频理解] 分析结果长度: {len(analysis_result)}")
            
            # 保存结果
            result_data = {
                "success": True,
                "video_path": os.path.abspath(video_path),
                "analysis_type": "video_content_and_scenes_understanding",
                "model_used": self.llm.model_name,
                "fps": fps,
                "time_cost": round(time_cost, 2),
                "content": analysis_result,
                "timestamp": datetime.now().isoformat()
            }
            return result_data
            
        except Exception as e:
            error_msg = f"视频内容理解失败：{str(e)}"
            print(f"[视频理解] {error_msg}")
            print(f"[视频理解] 错误类型: {type(e).__name__}")
            import traceback
            print(f"[视频理解] 错误堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg,
                "video_path": os.path.abspath(video_path),
                "timestamp": datetime.now().isoformat(),
                "content": None
            }

# 使用示例
if __name__ == "__main__":
    # 初始化Agent（API密钥从config中自动读取）
    agent = VideoAnalysisAgent()
    
    # 深度理解视频内容和画面场景
    result = agent.understand_video_content_and_scenes(
        video_path="e:/视频生成Agent/backend/video/20250604/7511717082225921334.mp4",
        fps=10
    )
    
    # 安全打印结果
    print("\n视频内容和画面理解结果：")
    if "error" in result:
        print(f"错误：{result['error']}")
    elif result.get("content_understanding"):
        print(result["content_understanding"])
    else:
        print("未获取到分析结果")



