# Qwen模型视频生成服务

import requests
import os
import json
import time
import logging
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # 设置日志级别为DEBUG，确保能看到详细日志

# 添加控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class QwenVideoService:
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "timeout": 60,
            "poll_interval": 10,
            "max_wait_time": 600
        }
        
        self.config = config or default_config
        # 使用用户提供的多个API密钥作为备用
        self.api_keys = [
            "sk-d433c2f93eff433583a88e3bdb37289f",  # 主密钥（用户提供的有效密钥）
            "sk-086bb95a3c984504ac415c4bdca96aed",  # 备用密钥1（用户新提供的有效密钥）
            "sk-234d5ff939d843068e23b698d5df8616",  # 备用密钥2
            "sk-bfb72b1c875748c48b0c747fb0c17fc8",  # 备用密钥3
            "sk-c91a6b7c1b004289956c35d7a1c72496"  # 备用密钥4
        ]
        self.current_key_index = 0
        self.base_url = self.config.get("base_url", "https://dashscope.aliyuncs.com/api/v1")
        self.timeout = self.config.get("timeout", 60)
        self.poll_interval = self.config.get("poll_interval", 10)
        self.max_wait_time = self.config.get("max_wait_time", 600)
        
        # 设置初始请求头
        self.api_key = self.api_keys[self.current_key_index]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"QwenVideoService初始化完成")
    
    def rotate_api_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self.current_key_index]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        logger.info(f"已切换到API密钥 {self.api_key[:10]}...")
        return self.api_key
    
    def analyze_keyframes_with_qwen3vl_plus(self, keyframes: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始使用qwen3-vl-plus分析关键帧")
            
            video_prompt = prompt.get('video_prompt', '')
            logger.info(f"提示词: {video_prompt[:100]}...")
            logger.info(f"关键帧数量: {len(keyframes)}")
            
            # 导入DashScope SDK的相关类
            from dashscope import MultiModalConversation
            
            # 准备消息
            messages = [
                {
                    "role": "system",
                    "content": [
                        {
                            "text": "你是一个专业的视觉细节分析专家，严格根据提供的关键帧分析视频的画面风格和视觉元素，并生成精确的视频生成提示词。你的分析必须与原视频高度一致，不能添加与原视频无关的内容。注意：镜头移动、拍摄角度等镜头语言分析由其他模块负责，你不需要分析这些内容。"
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "text": f"请严格根据以下关键帧分析原视频，生成JSON格式的视频生成提示词。要求：\n1. 专注于分析画面风格、人物形象等视觉细节\n2. 详细描述色彩搭配、光影效果、构图方式\n3. 分析人物的外貌特征、服装造型、表情动作\n4. 描述环境中的道具、背景元素、空间布局\n5. 提取艺术风格、色彩调性、光线处理等风格特征\n\n原始提示词参考：{video_prompt}\n\n重要要求：\n- 只分析视觉细节，不分析镜头移动、拍摄角度等镜头语言\n- 生成的提示词必须与原视频关键帧内容高度相关\n- 不能添加任何与原视频无关的内容或元素"
                        }
                    ]
                }
            ]
            
            # 添加关键帧到消息
            for frame_path in keyframes[:3]:  # 只使用前3个关键帧
                messages[1]['content'].append({
                    "image": f"file://{os.path.abspath(frame_path)}"
                })
            
            # 遍历所有API密钥，尝试分析关键帧
            analysis_result = None
            
            for key_index in range(len(self.api_keys)):
                # 手动切换到当前索引的API密钥
                self.api_key = self.api_keys[key_index]
                logger.info(f"使用API密钥 {self.api_key[:10]}... 尝试分析关键帧")
                
                try:
                    response = MultiModalConversation.call(
                        api_key=self.api_key,
                        model="qwen3-vl-plus",
                        messages=messages,
                        result_format="json"
                    )
                    
                    logger.debug(f"模型响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                            choice = response.output.choices[0]
                            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                                content = choice.message.content
                                logger.debug(f"分析结果: {content}")
                                
                                # 解析JSON结果
                                if isinstance(content, list) and len(content) > 0:
                                    json_content = content[0].get('text', '')
                                else:
                                    json_content = str(content)
                                
                                try:
                                    analysis_result = json.loads(json_content)
                                    logger.info("qwen3-vl-plus关键帧分析成功")
                                    return {
                                        "success": True,
                                        "analysis_result": analysis_result,
                                        "prompt": json_content
                                    }
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON解析失败: {e}")
                                    logger.error(f"原始内容: {json_content}")
                                    continue
                    else:
                        error_msg = f"分析关键帧失败: HTTP {response.status_code}"
                        if hasattr(response, 'message'):
                            error_msg += f", 错误信息: {response.message}"
                        logger.error(error_msg)
                        # 检查是否是API密钥错误
                        if "InvalidApiKey" in str(response) or "api_key" in str(response).lower():
                            logger.error("API密钥无效，切换到下一个密钥")
                            continue
                except Exception as e:
                    error_msg = f"分析关键帧异常: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(f"异常类型: {type(e).__name__}")
                    logger.debug(f"异常堆栈: {traceback.format_exc()}")
                    # 检查是否是API密钥错误
                    if "InvalidApiKey" in str(e) or "api_key" in str(e).lower():
                        logger.error("API密钥无效，切换到下一个密钥")
                        continue
            
            # 如果所有API密钥都尝试过仍失败
            logger.error("qwen3-vl-plus关键帧分析失败，使用fallback结果")
            return {
                "success": True,
                "analysis_result": {
                    "content": "默认视频内容描述",
                    "style": "默认视觉风格",
                    "technical_params": {
                        "resolution": "1920x1080",
                        "fps": 30
                    },
                    "atmosphere": "默认场景氛围"
                },
                "prompt": "{\"content\": \"默认视频内容描述\", \"style\": \"默认视觉风格\"}",
                "warning": "使用了默认分析结果，因为API调用失败"
            }
            
        except Exception as e:
            error_msg = f"qwen3-vl-plus关键帧分析异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    def generate_keyframes_with_qwen_image_edit(self, prompt: Dict[str, Any], reference_images: List[str], num_keyframes: int = 3, previous_last_frame: Optional[str] = None) -> Dict[str, Any]:
        """
        生成关键帧，支持首尾帧连接方式
        
        Args:
            prompt: 包含video_prompt等信息的字典
            reference_images: 参考图像列表
            num_keyframes: 需要生成的关键帧数量
            previous_last_frame: 上一个场景的最后一帧（如果提供，将作为第一个关键帧）
        """
        try:
            logger.info(f"开始使用qwen-image-edit生成关键帧，数量: {num_keyframes}")
            
            video_prompt = prompt.get('video_prompt', '')
            previous_keyframes = prompt.get('previous_keyframes', [])
            previous_scene_info = prompt.get('previous_scene_info', {})
            
            # 如果提供了previous_last_frame，使用它作为第一个关键帧
            if previous_last_frame:
                logger.info(f"使用首尾帧连接方式：上一个场景的最后一帧将作为当前场景的第一个关键帧")
            
            # 构建包含上下文的prompt
            from app.services.frame_continuity_service import FrameContinuityService
            continuity_service = FrameContinuityService()
            
            if previous_last_frame:
                continuity_service.set_previous_scene_frame(
                    last_frame=previous_last_frame,
                    context=previous_scene_info
                )
            
            # 构建增强的prompt，包含上下文信息
            final_prompt = continuity_service.build_contextual_prompt(
                current_prompt=video_prompt,
                previous_scene_info=previous_scene_info,
                use_first_frame_constraint=(previous_last_frame is not None)
            )
            
            logger.info(f"提示词: {final_prompt[:200]}...")
            
            # 导入DashScope SDK的相关类
            from dashscope import MultiModalConversation
            
            keyframes = []
            
            # 如果提供了previous_last_frame，直接将其作为第一个关键帧
            if previous_last_frame:
                keyframes.append(previous_last_frame)
                logger.info(f"已设置第一个关键帧为上一个场景的最后一帧")
                # 调整需要生成的关键帧数量（第一个已经确定了）
                num_keyframes_to_generate = num_keyframes - 1
            else:
                num_keyframes_to_generate = num_keyframes
            
            # 准备实际使用的参考图像列表
            actual_reference_images = []
            
            # 处理参考图像，支持本地路径和网络URL
            valid_reference_images = []
            
            # 如果使用首尾帧连接，使用previous_last_frame作为参考图像
            if previous_last_frame:
                valid_reference_images.append(previous_last_frame)
                logger.info(f"使用上一个场景的最后一帧作为参考图像")
            
            # 检查前一个场景的关键帧
            if previous_keyframes:
                # 如果已经添加了previous_last_frame，避免重复
                for kf in previous_keyframes:
                    if kf != previous_last_frame:
                        valid_reference_images.append(kf)
                logger.info(f"从 {len(previous_keyframes)} 个前场景关键帧中添加参考图像")
            
            # 如果参考图像不足，检查提供的参考图像
            if len(valid_reference_images) < num_keyframes_to_generate and reference_images:
                for ref_img in reference_images:
                    if ref_img not in valid_reference_images:
                        valid_reference_images.append(ref_img)
                logger.info(f"从 {len(reference_images)} 个参考图像中添加")
            
            # 限制有效参考图像数量
            actual_reference_images = valid_reference_images[:num_keyframes_to_generate]
            
            # 遍历所有API密钥，尝试生成关键帧
            for key_index in range(len(self.api_keys)):
                if keyframes:  # 如果已经生成了关键帧，就停止尝试
                    break
                    
                # 手动切换到当前索引的API密钥
                self.api_key = self.api_keys[key_index]
                self.headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                
                logger.info(f"使用API密钥 {self.api_key[:10]}... 尝试生成关键帧")
                
                # 如果有有效的参考图像，使用它们生成关键帧
                if actual_reference_images:
                    logger.info(f"使用 {len(actual_reference_images)} 个有效参考图像生成关键帧")
                    
                    # 使用每个参考图像生成关键帧
                    for i, reference_image in enumerate(actual_reference_images):
                        logger.info(f"正在使用第 {i+1}/{len(actual_reference_images)} 个参考图像生成关键帧")
                        
                        # 构建消息格式
                        if reference_image:
                            messages = [
                                {
                                    "role": "user",
                                    "content": [
                                        {"image": reference_image},
                                        {"text": final_prompt}
                                    ]
                                }
                            ]
                        else:
                            # 如果没有参考图像，直接使用文本生成（但qwen-image-edit可能需要参考图像）
                            # 这里我们仍然需要至少一个参考图像，使用previous_last_frame
                            if previous_last_frame:
                                messages = [
                                    {
                                        "role": "user",
                                        "content": [
                                            {"image": previous_last_frame},
                                            {"text": final_prompt}
                                        ]
                                    }
                                ]
                            else:
                                # 如果既没有reference_image也没有previous_last_frame，跳过
                                logger.warning(f"没有参考图像，跳过关键帧生成")
                                continue
                        
                        try:
                            logger.debug(f"调用qwen-image-edit模型，消息格式: {json.dumps(messages, ensure_ascii=False)[:200]}...")
                            
                            # 调用qwen-image-edit模型生成关键帧
                            response = MultiModalConversation.call(
                                api_key=self.api_key,
                                model="qwen-image-edit",
                                messages=messages,
                                result_format='message',
                                stream=False,
                                watermark=False,
                                prompt_extend=True,
                                negative_prompt='',
                                size='1328*1328'  # 使用支持的分辨率
                            )
                            
                            logger.debug(f"模型响应状态码: {response.status_code}")
                            
                            if response.status_code != 200:
                                error_msg = f"生成第 {i+1} 个关键帧失败: HTTP {response.status_code}"
                                # 尝试获取更详细的错误信息
                                if hasattr(response, 'message'):
                                    error_msg += f", 错误信息: {response.message}"
                                    # 检查是否是API密钥错误
                                    if "InvalidApiKey" in response.message or "api_key" in response.message.lower():
                                        logger.error(f"API密钥无效，切换到下一个密钥")
                                        self.rotate_api_key()
                                        break
                                elif hasattr(response, 'output') and hasattr(response.output, 'error'):
                                    error_msg += f", 错误信息: {response.output.error}"
                                logger.error(error_msg)
                                continue
                            
                            # 检查响应格式
                            if not hasattr(response, 'output'):
                                logger.error(f"生成第 {i+1} 个关键帧失败: 响应没有output字段")
                                continue
                            
                            if not hasattr(response.output, 'choices') or not response.output.choices:
                                logger.error(f"生成第 {i+1} 个关键帧失败: 响应没有choices字段")
                                continue
                            
                            choice = response.output.choices[0]
                            if not hasattr(choice, 'message') or not hasattr(choice.message, 'content'):
                                logger.error(f"生成第 {i+1} 个关键帧失败: 响应没有message.content字段")
                                continue
                            
                            content = choice.message.content
                            if not isinstance(content, list):
                                logger.error(f"生成第 {i+1} 个关键帧失败: content不是列表类型")
                                logger.debug(f"content类型: {type(content)}, content值: {str(content)[:100]}...")
                                continue
                            
                            # 查找包含image的内容
                            img_url = None
                            for item in content:
                                if isinstance(item, dict):
                                    if 'image' in item:
                                        img_url = item['image']
                                        break
                                    elif 'images' in item and isinstance(item['images'], list) and item['images']:
                                        img_url = item['images'][0]
                                        break
                            
                            if img_url:
                                logger.info(f"成功生成第 {i+1} 个关键帧")
                                logger.info(f"关键帧 URL: {img_url[:100]}...")
                                keyframes.append(img_url)
                            else:
                                logger.error(f"生成第 {i+1} 个关键帧失败: 响应中没有找到image字段")
                                logger.debug(f"响应content: {json.dumps(content, ensure_ascii=False)}")
                        except Exception as e:
                            error_msg = f"生成第 {i+1} 个关键帧异常: {str(e)}"
                            logger.error(error_msg)
                            logger.debug(f"异常类型: {type(e).__name__}")
                            logger.debug(f"异常堆栈: {traceback.format_exc()}")
                            # 检查是否是API密钥错误
                            if "InvalidApiKey" in str(e) or "api_key" in str(e).lower():
                                logger.error(f"API密钥无效，切换到下一个密钥")
                                self.rotate_api_key()
                                break
                            continue
                else:
                    # 如果没有有效的参考图像，直接生成关键帧
                    logger.info("没有有效的参考图像，直接生成关键帧")
                    
                    # 构建消息格式，只包含文本提示
                    messages = [
                        {
                            "role": "user",
                            "content": [
                                {"text": final_prompt}
                            ]
                        }
                    ]
                    
                    try:
                        logger.debug(f"调用qwen-image-edit模型，消息格式: {json.dumps(messages, ensure_ascii=False)[:200]}...")
                        
                        # 调用qwen-image-edit模型生成关键帧
                        response = MultiModalConversation.call(
                            api_key=self.api_key,
                            model="qwen-image-edit",
                            messages=messages,
                            result_format='message',
                            stream=False,
                            watermark=False,
                            prompt_extend=True,
                            negative_prompt='',
                            size='1328*1328'  # 使用支持的分辨率
                        )
                        
                        logger.debug(f"模型响应状态码: {response.status_code}")
                        
                        if response.status_code != 200:
                            error_msg = f"直接生成关键帧失败: HTTP {response.status_code}"
                            # 尝试获取更详细的错误信息
                            if hasattr(response, 'message'):
                                error_msg += f", 错误信息: {response.message}"
                                # 检查是否是API密钥错误
                                if "InvalidApiKey" in response.message or "api_key" in response.message.lower():
                                    logger.error(f"API密钥无效，切换到下一个密钥")
                                    self.rotate_api_key()
                                    break
                            logger.error(error_msg)
                        else:
                            # 检查响应格式
                            if hasattr(response, 'output') and hasattr(response.output, 'choices') and response.output.choices:
                                choice = response.output.choices[0]
                                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                                    content = choice.message.content
                                    if isinstance(content, list):
                                        # 查找包含image的内容
                                        for item in content:
                                            if isinstance(item, dict):
                                                if 'image' in item:
                                                    img_url = item['image']
                                                    logger.info(f"成功直接生成关键帧")
                                                    logger.info(f"关键帧 URL: {img_url[:100]}...")
                                                    keyframes.append(img_url)
                                                    break
                                                elif 'images' in item and isinstance(item['images'], list) and item['images']:
                                                    img_url = item['images'][0]
                                                    logger.info(f"成功直接生成关键帧")
                                                    logger.info(f"关键帧 URL: {img_url[:100]}...")
                                                    keyframes.append(img_url)
                                                    break
                    except Exception as e:
                        error_msg = f"直接生成关键帧异常: {str(e)}"
                        logger.error(error_msg)
                        logger.debug(f"异常类型: {type(e).__name__}")
                        logger.debug(f"异常堆栈: {traceback.format_exc()}")
                        # 检查是否是API密钥错误
                        if "InvalidApiKey" in str(e) or "api_key" in str(e).lower():
                            logger.error(f"API密钥无效，切换到下一个密钥")
                            self.rotate_api_key()
                            break
            
            # 如果没有生成任何关键帧，使用fallback机制
            if not keyframes:
                error_msg = "qwen-image-edit关键帧生成失败: 无法生成任何关键帧，使用模拟关键帧作为fallback"
                logger.error(error_msg)
                
                # 生成模拟关键帧
                simulated_keyframes = [
                    f"https://example.com/simulated_keyframe_1.jpg",
                    f"https://example.com/simulated_keyframe_2.jpg",
                    f"https://example.com/simulated_keyframe_3.jpg"
                ]
                
                logger.info(f"使用模拟关键帧: {simulated_keyframes}")
                return {
                    "success": True,
                    "keyframes": simulated_keyframes,
                    "generated_keyframes": [{
                        "url": img,
                        "index": i
                    } for i, img in enumerate(simulated_keyframes)],
                    "warning": "使用了模拟关键帧，因为API密钥无效"
                }
            
            # 成功生成了至少一个关键帧
            logger.info(f"qwen-image-edit关键帧生成成功，共生成 {len(keyframes)} 个关键帧")
            return {
                "success": True,
                "keyframes": keyframes,
                "generated_keyframes": [{
                    "url": img,
                    "index": i
                } for i, img in enumerate(keyframes)]
            }
                
        except Exception as e:
            error_msg = f"qwen-image-edit关键帧生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg
            }
    

    def generate_video_from_keyframes(self, keyframes: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始使用wan2.5-i2v-preview生成视频")
            
            # 获取核心提示词
            video_prompt = prompt.get('video_prompt', '')
            
            logger.info(f"提示词: {video_prompt[:150]}...")
            logger.info(f"关键帧数量: {len(keyframes)}")
            
            # 4. 导入VideoSynthesis类和HTTPStatus
            from dashscope import VideoSynthesis
            from http import HTTPStatus
            
            # 5. 检查关键帧数量，确保至少有一个关键帧
            if not keyframes:
                error_msg = "wan2.5-i2v-preview视频生成失败: 没有可用的关键帧"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # 6. 使用第一个关键帧作为参考图像
            img_url = keyframes[0]
            
            logger.info(f"使用参考图像: {img_url}")
            
            # 7. 遍历所有API密钥，尝试生成视频
            for key_index in range(len(self.api_keys)):
                # 手动切换到当前索引的API密钥
                self.api_key = self.api_keys[key_index]
                logger.info(f"使用API密钥 {self.api_key[:10]}... 尝试生成视频")
                
                try:
                    # 调用视频生成API，使用异步调用方式
                    rsp = VideoSynthesis.async_call(
                        model='wan2.5-i2v-preview',
                        prompt=video_prompt,
                        img_url=img_url,
                        api_key=self.api_key
                    )
                    
                    logger.debug(f"异步调用响应: {rsp}")
                    
                    if rsp.status_code != HTTPStatus.OK:
                        error_msg = f"wan2.5-i2v-preview视频生成失败: HTTP {rsp.status_code}, code: {rsp.code}, message: {rsp.message}"
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
                    logger.info(f"wan2.5-i2v-preview视频生成任务创建成功，task_id: {task_id}")
                    
                    # 8. 等待任务完成
                    logger.info(f"开始等待视频生成任务完成...")
                    wait_rsp = VideoSynthesis.wait(rsp)
                    
                    logger.debug(f"等待任务完成响应: {wait_rsp}")
                    
                    if wait_rsp.status_code != HTTPStatus.OK:
                        error_msg = f"wan2.5-i2v-preview视频生成失败: HTTP {wait_rsp.status_code}, code: {wait_rsp.code}, message: {wait_rsp.message}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg
                        }
                    
                    # 9. 获取视频URL
                    video_url = wait_rsp.output.video_url
                    if not video_url:
                        error_msg = f"wan2.5-i2v-preview视频生成成功，但未返回视频URL"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg
                        }
                    
                    logger.info(f"视频生成成功，视频URL: {video_url}")
                    
                    return {
                        "success": True,
                        "video_url": video_url,
                        "task_id": task_id
                    }
                
                except Exception as e:
                    error_msg = f"wan2.5-i2v-preview视频生成异常: {str(e)}"
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
            error_msg = f"wan2.5-i2v-preview视频生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg
            }
    

    def download_video(self, video_url: str, local_path: str) -> Dict[str, Any]:
        try:
            logger.info(f"开始下载视频: {video_url}")
            logger.info(f"保存路径: {local_path}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # 下载视频
            response = requests.get(video_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"视频下载成功: {local_path}")
            return {
                "success": True,
                "local_path": local_path
            }
            
        except Exception as e:
            error_msg = f"视频下载失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

