import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
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
    """基于DashScope的LangChain聊天模型"""
    
    api_key: str = Field(default="")
    model_name: str = Field(default="qwen-omni-turbo-latest")
    
    def __init__(self, api_key: str = None, model_name: str = "qwen-omni-turbo-latest", **kwargs):
        # 设置默认值
        if api_key is None:
            api_key = config.DASHSCOPE_API_KEY
        
        super().__init__(api_key=api_key, model_name=model_name, **kwargs)
        
        if not self.api_key:
            raise ValueError("API密钥未提供")
    
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
                    # 检查是否已经提取了关键帧，如果有则使用关键帧，否则使用视频描述
                    if hasattr(message, 'additional_kwargs') and 'keyframes' in message.additional_kwargs:
                        keyframes = message.additional_kwargs['keyframes']
                        content_list = []
                        # 只使用前3个关键帧以加快处理速度
                        for frame_path in keyframes[:3]:
                            content_list.append({'image': f"file://{os.path.abspath(frame_path)}"})
                        content_list.append({'text': message.content})
                        dashscope_messages.append({
                            'role': 'user',
                            'content': content_list
                        })
                    else:
                        # 如果没有关键帧，只传递文本描述，避免URL错误
                        video_desc = f"视频文件路径: {video_path}, 大小约{os.path.getsize(video_path)/(1024*1024):.2f}MB"
                        dashscope_messages.append({
                            'role': 'user',
                            'content': [{'text': f"{message.content}\n{video_desc}"}]
                        })
                else:
                    dashscope_messages.append({
                        'role': 'user',
                        'content': [{'text': message.content}]
                    })
        
        return dashscope_messages

class VideoAnalysisAgent:
    """基于LangChain的视频分析智能体"""
    
    def __init__(self, api_key: str = None, model_name: str = "qwen-omni-turbo-latest"):
# 初始化视频分析智能体
        self.llm = DashScopeChatModel(
            api_key=api_key,
            model_name=model_name
        )
        
        # 定义系统提示词
        self.system_prompt = (
            "你是一个专业的视频内容分析师，专门负责深度理解视频的宏观结构和镜头语言。请按照以下要求进行分析：\n\n"
            "**核心任务：**\n"
            "1. 分析视频的整体场景结构和叙事流程\n"
            "2. 识别场景间的变化和过渡\n"
            "3. 分析镜头移动和拍摄手法\n\n"
            "**分析维度：**\n"
            "1. 宏观场景分析：\n"
            "   - 场景数量、顺序和转换逻辑\n"
            "   - 叙事流程和关键转折点\n"
            "   - 场景变化和节奏转换\n"
            "   - 整体氛围和情感走向\n\n"
            "2. 镜头语言分析：\n"
            "   - 镜头移动：推、拉、摇、移、跟等运动方式和效果\n"
            "   - 镜头角度：俯视、仰视、平视等角度选择及其叙事作用\n"
            "   - 景别变化：全景、中景、近景、特写等景别的使用和转换\n"
            "   - 镜头组合：蒙太奇手法、镜头剪辑节奏和视觉韵律\n\n"
            "3. 内容框架：\n"
            "   - 主题提炼和核心信息\n"
            "   - 角色关系和互动\n"
            "   - 时间空间转换\n"
            "   - 整体节奏分析\n\n"
            "请用专业、详细的语言描述，重点关注场景结构和镜头移动等宏观元素，为视频生成提供清晰的叙事框架。"
        )
    
    async def understand_video_content_and_scenes(
        self, 
        video_path: str, 
        fps: int = 5,  # 降低默认帧率，加快处理速度
        slice_limit: int = 0,  # 限制处理的切片数量
        audio_transcription: str = None  # 音频转录结果，用于增强视频理解
    ) -> Dict[str, Any]:
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
            
            # 使用FFmpegService将视频切片
            print(f"[视频理解] 视频文件存在，开始切片处理")
            
            from app.services.ffmpeg_service import FFmpegService
            ffmpeg_service = FFmpegService()
            
            # 异步切片，每个切片4秒（API限制内）
            slice_result = await ffmpeg_service.slice_video(video_path, slice_duration=4, slice_limit=slice_limit)
            
            if not slice_result or 'slices' not in slice_result:
                error_msg = "视频切片失败"
                print(f"[视频理解] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "video_path": os.path.abspath(video_path),
                    "timestamp": datetime.now().isoformat(),
                    "content": None
                }
            
            slices = slice_result['slices']
            
            # 应用切片限制
            if slice_limit > 0 and len(slices) > slice_limit:
                slices = slices[:slice_limit]
                print(f"[视频理解] 应用切片限制：只使用前 {slice_limit} 个切片")
            # 测试模式：只使用前10个切片
            elif len(slices) > 10:
                slices = slices[:10]
                print(f"[视频理解] 测试模式：只使用前10个切片")
            print(f"[视频理解] 视频切片完成，共 {len(slices)} 个切片，每个切片4秒")
            
            # 逐个分析切片
            all_analysis_results = []
            
            # 提取对应切片的音频内容
            slice_audio_content = self._get_slice_audio_content(audio_transcription, slices)
            
            for i, slice_info in enumerate(slices):
                slice_path = slice_info['output_file']
                slice_start = slice_info['start_time']
                slice_duration = slice_info['duration']
                slice_keyframes = slice_info.get('keyframes', [])  # 获取关键帧信息
                slice_preview = slice_info.get('preview_file', '')  # 获取预览图
                current_slice_audio = slice_audio_content.get(i, '')  # 获取当前切片对应的音频内容
                
                print(f"\n[视频理解] 开始分析切片 {i+1}/{len(slices)}: {slice_path}")
                print(f"[视频理解] 切片时间范围: {slice_start:.1f}s - {slice_start+slice_duration:.1f}s")
                print(f"[视频理解] 切片关键帧数量: {len(slice_keyframes)}")
                print(f"[视频理解] 切片音频内容长度: {len(current_slice_audio)}")
                
                # 构建增强的系统提示词，包含音频内容的重要性
                enhanced_system_prompt = self.system_prompt + "\n\n特别重要：请结合提供的音频转录内容，确保视觉分析与音频内容保持一致，提高内容理解的准确性。"
                
                # 构建消息链 - 分析单个切片，结合音频内容
                messages = [
                    SystemMessage(content=enhanced_system_prompt),
                    HumanMessage(
                        content=f"请深度分析这个视频切片，重点关注：1）切片的内容和情节；2）画面中的具体元素、人物、环境；3）色彩、光线、氛围等细节。\n\n切片信息：第{i+1}/{len(slices)}个切片，原视频时间范围 {slice_start:.1f}s - {slice_start+slice_duration:.1f}s\n\n切片对应的音频内容：{current_slice_audio}",
                        additional_kwargs={
                            'video_path': slice_path,
                            'fps': fps,
                            'keyframes': slice_keyframes  # 传递关键帧信息
                        }
                    )
                ]
                
                # 调用LangChain模型分析切片
                slice_result = self.llm.generate([messages])
                slice_analysis = slice_result.generations[0][0].message.content
                
                all_analysis_results.append({
                    'slice_index': i,
                    'start_time': slice_start,
                    'end_time': slice_start + slice_duration,
                    'analysis': slice_analysis,
                    'keyframes': slice_keyframes,  # 保存关键帧信息
                    'preview_file': slice_preview,  # 保存预览图
                    'slice_path': slice_path,  # 保存切片路径
                    'audio_content': current_slice_audio  # 保存对应音频内容
                })
                
                print(f"[视频理解] 切片 {i+1} 分析完成，结果长度: {len(slice_analysis)}")
            
            # 整合所有切片的分析结果
            print(f"\n[视频理解] 开始整合 {len(all_analysis_results)} 个切片的分析结果")
            
            # 构建整合后的分析结果，包含音频转录信息
            integrated_analysis = f"  # 视频整体分析结果\n\n"
            integrated_analysis += f"  # # 基本信息\n"
            integrated_analysis += f"- 视频路径: {video_path}\n"
            integrated_analysis += f"- 分析模型: {self.llm.model_name}\n"
            integrated_analysis += f"- 切片数量: {len(all_analysis_results)}\n"
            integrated_analysis += f"- 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            if audio_transcription:
                integrated_analysis += f"- 音频转录内容长度: {len(audio_transcription)}\n"
            integrated_analysis += "\n"
            
            integrated_analysis += "  # # 切片分析结果\n\n"
            for i, slice_data in enumerate(all_analysis_results):
                integrated_analysis += f"## 切片 {i+1}\n\n"
                integrated_analysis += f"**音频内容**: {slice_data['audio_content'][:100]}...\n\n" if slice_data['audio_content'] else "\n"
                integrated_analysis += slice_data['analysis'] + "\n\n"
            
            # 调用模型生成整体总结，强调音视频一致性
            print(f"[视频理解] 生成整体视频总结，强调音视频一致性")
            summary_messages = [
                SystemMessage(content="你是一个专业的视频内容整合专家，请将多个视频切片的分析结果整合成一个连贯的、完整的视频分析报告。\n\n要求：\n1. 总结视频的整体内容和故事情节\n2. 保持内容的连贯性和逻辑性\n3. 突出视频的重点和亮点\n4. 确保视觉内容与音频内容的一致性\n5. 使用流畅自然的语言\n6. 不要重复切片间的过渡内容\n7. 整体结构清晰，易于理解"),
                HumanMessage(content=f"请根据以下各个切片的分析结果，生成一个完整的视频分析报告：\n\n{integrated_analysis}")
            ]
            
            summary_result = self.llm.generate([summary_messages])
            final_analysis = summary_result.generations[0][0].message.content
            
            time_cost = time.time() - start_time
            print(f"[视频理解] 视频分析完成，总耗时: {time_cost:.2f}秒")
            print(f"[视频理解] 最终分析结果长度: {len(final_analysis)}")
            
            # 保存结果，包含关键帧信息和音频转录
            result_data = {
                "success": True,
                "video_path": os.path.abspath(video_path),
                "analysis_type": "video_content_and_scenes_understanding",
                "model_used": self.llm.model_name,
                "fps": fps,
                "time_cost": round(time_cost, 2),
                "content": final_analysis,
                "timestamp": datetime.now().isoformat(),
                "slice_count": len(all_analysis_results),
                "raw_slices": all_analysis_results,
                "slices": slices,  # 保存完整的切片信息，包含关键帧
                "audio_transcription": audio_transcription  # 保存音频转录结果
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
    
    def _get_slice_audio_content(self, full_transcription: str, slices: List[Dict]) -> Dict[int, str]:
        if not full_transcription:
            return {}
        
        # 简单的实现：将转录文本平均分配到各个切片
        # 更复杂的实现可以根据时间戳匹配，但需要音频转录时包含时间信息
        slice_audio_content = {}
        words = full_transcription.split()
        total_words = len(words)
        
        if total_words == 0:
            return {i: "" for i in range(len(slices))}
        
        # 计算每个切片应分配的单词数量
        words_per_slice = max(1, total_words // len(slices))
        
        for i in range(len(slices)):
            start_idx = i * words_per_slice
            end_idx = (i + 1) * words_per_slice if i < len(slices) - 1 else total_words
            slice_words = words[start_idx:end_idx]
            slice_audio_content[i] = " ".join(slice_words)
        
        return slice_audio_content

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


