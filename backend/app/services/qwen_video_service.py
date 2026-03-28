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
            "sk-a48e659d43af4009b4dbaa5ae878f473"
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
    
    def analyze_keyframes_with_qwen3vl_plus(
        self,
        keyframes: List[str],
        prompt: Dict[str, Any],
        lang: str = 'zh',
    ) -> Dict[str, Any]:
        try:
            logger.info(f"开始使用qwen3-vl-plus分析关键帧")
            
            video_prompt = prompt.get('video_prompt', '')
            logger.info(f"提示词: {video_prompt[:100]}...")
            logger.info(f"关键帧数量: {len(keyframes)}")
            
            # 导入DashScope SDK的相关类
            from dashscope import MultiModalConversation
            
            if lang == 'en':
                sys_text = (
                    "You are a professional visual-detail analyst. From the keyframes, infer on-screen style "
                    "and visual elements and produce precise video-generation prompts. Stay faithful to what "
                    "is visible; do not invent unrelated content. Camera movement and shot grammar are handled "
                    "elsewhere — do not analyze them."
                )
                user_text = (
                    f"From these keyframes, output a JSON object suitable as video-generation prompts. "
                    f"Requirements:\n"
                    f"1. Focus on visual style, character appearance, and environment.\n"
                    f"2. Describe color, lighting, and composition.\n"
                    f"3. Character looks, outfits, expressions, and actions.\n"
                    f"4. Props, background, spatial layout.\n"
                    f"5. Overall art direction, palette, and light treatment.\n\n"
                    f"Reference prompt: {video_prompt}\n\n"
                    f"Rules: visual details only; prompts must match the keyframes; no unrelated elements."
                )
            else:
                sys_text = (
                    "你是一个专业的视觉细节分析专家，严格根据提供的关键帧分析视频的画面风格和视觉元素，并生成精确的视频生成提示词。"
                    "你的分析必须与原视频高度一致，不能添加与原视频无关的内容。注意：镜头移动、拍摄角度等镜头语言分析由其他模块负责，你不需要分析这些内容。"
                )
                user_text = (
                    f"请严格根据以下关键帧分析原视频，生成JSON格式的视频生成提示词。要求：\n"
                    f"1. 专注于分析画面风格、人物形象等视觉细节\n"
                    f"2. 详细描述色彩搭配、光影效果、构图方式\n"
                    f"3. 分析人物的外貌特征、服装造型、表情动作\n"
                    f"4. 描述环境中的道具、背景元素、空间布局\n"
                    f"5. 提取艺术风格、色彩调性、光线处理等风格特征\n\n"
                    f"原始提示词参考：{video_prompt}\n\n"
                    f"重要要求：\n"
                    f"- 只分析视觉细节，不分析镜头移动、拍摄角度等镜头语言\n"
                    f"- 生成的提示词必须与原视频关键帧内容高度相关\n"
                    f"- 不能添加任何与原视频无关的内容或元素"
                )

            # 准备消息
            messages = [
                {
                    "role": "system",
                    "content": [{"text": sys_text}],
                },
                {
                    "role": "user",
                    "content": [{"text": user_text}],
                },
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
                        model="qwen3-vl-flash",  # 使用qwen3-vl-flash模型
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
            if lang == 'en':
                ar = {
                    "content": "Default video content description",
                    "style": "Default visual style",
                    "technical_params": {"resolution": "1920x1080", "fps": 30},
                    "atmosphere": "Default scene atmosphere",
                }
                pr = '{"content": "Default video content description", "style": "Default visual style"}'
                warn = "Using default analysis because the API call failed"
            else:
                ar = {
                    "content": "默认视频内容描述",
                    "style": "默认视觉风格",
                    "technical_params": {"resolution": "1920x1080", "fps": 30},
                    "atmosphere": "默认场景氛围",
                }
                pr = '{"content": "默认视频内容描述", "style": "默认视觉风格"}'
                warn = "使用了默认分析结果，因为API调用失败"
            return {
                "success": True,
                "analysis_result": ar,
                "prompt": pr,
                "warning": warn,
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
            logger.info(f"开始使用wan2.6-i2v-flash生成视频")
            
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
            
            # 4. 导入VideoSynthesis类和HTTPStatus
            from dashscope import VideoSynthesis
            from http import HTTPStatus
            
            # 5. 检查关键帧数量，确保至少有一个关键帧
            if not keyframes:
                error_msg = "wan2.6-i2v-flash视频生成失败: 没有可用的关键帧"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # 6. 第一个关键帧作为图生视频参考：调用方约定为「当前分镜图」优先，其次可为上一镜尾帧
            img_url = keyframes[0]
            
            logger.info(f"使用参考图像: {img_url}")
            logger.info(f"关键帧数量: {len(keyframes)}（首帧为 wan i2v 主参考图）")
            
            # 7. 只使用第一个API密钥生成视频
            self.api_key = self.api_keys[0]
            logger.info(f"使用API密钥 {self.api_key[:10]}... 生成视频")

            try:
                # 调用视频生成API，使用异步调用方式
                rsp = VideoSynthesis.async_call(
                    model='wan2.6-i2v-flash',
                    prompt=video_prompt,
                    img_url=img_url,
                    api_key=self.api_key,
                    free_tier_only=False
                )

                logger.debug(f"异步调用响应: {rsp}")

                if rsp.status_code != HTTPStatus.OK:
                    error_msg = f"wan2.6-i2v-flash视频生成失败: HTTP {rsp.status_code}, code: {rsp.code}, message: {rsp.message}"
                    logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }

                task_id = rsp.output.task_id
                logger.info(f"wan2.6-i2v-flash视频生成任务创建成功，task_id: {task_id}")

                # 8. 等待任务完成
                logger.info(f"开始等待视频生成任务完成...")

                # 自定义等待逻辑
                max_wait_time = 1800  # 最大等待时间（秒）30分钟
                poll_interval = 15  # 轮询间隔（秒）
                start_time = time.time()

                while time.time() - start_time < max_wait_time:
                    wait_rsp = VideoSynthesis.fetch(rsp, api_key=self.api_key)
                    logger.debug(f"轮询任务状态: {wait_rsp.output.task_status}, 已等待: {time.time() - start_time:.1f}秒")

                    if wait_rsp.status_code != HTTPStatus.OK:
                        error_msg = f"wan2.6-i2v-flash视频生成失败: HTTP {wait_rsp.status_code}, code: {wait_rsp.code}, message: {wait_rsp.message}"
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
                        error_msg = f"wan2.6-i2v-flash视频生成失败: 任务状态为 {task_status}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg
                        }

                    # 任务还在处理中，继续等待
                    logger.info(f"任务状态: {task_status}，继续等待...")
                    time.sleep(poll_interval)

                # 等待超时
                error_msg = f"wan2.6-i2v-flash视频生成超时: 超过 {max_wait_time} 秒仍未完成"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            except Exception as e:
                error_msg = f"wan2.6-i2v-flash视频生成异常: {str(e)}"
                logger.error(error_msg, exc_info=True)
                import traceback
                traceback.print_exc()
                print(f"[ERROR] 视频生成异常: {str(e)}")
                print(f"[ERROR] 异常类型: {type(e).__name__}")
                return {
                    "success": False,
                    "error": error_msg
                }

            return {
                "success": False,
                "error": "视频生成失败"
            }

        except Exception as e:
            error_msg = f"wan2.6-i2v-flash视频生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": error_msg
            }
    
    def optimize_prompt_with_qwen_plus_latest(self, prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        使用qwen-plus-latest模型优化提示词，生成专业的Shot Breakdown表格格式
        
        Args:
            prompt: 原始提示词
            context: 上下文信息，包括音频内容、关键帧信息、shot_breakdown等
            
        Returns:
            优化后的提示词和相关信息
        """
        try:
            logger.info(f"开始使用qwen-plus-latest优化提示词")
            
            system_prompt = """你是一个专业的视频分镜脚本专家。你的任务是将原始视频分析转化为专业的JSON格式Shot Breakdown。

## 输出格式要求

必须严格按照以下JSON格式输出，不要包含任何其他文字：

```json
{
    "shot_breakdown": [
        {
            "shot_number": 1,
            "framing": "景别（英文）",
            "angle": "角度（英文）",
            "movement": "运动（英文）",
            "shot_description": "详细场景描述（中文）",
            "audio": {
                "bgm": "背景音乐描述",
                "sfx": "音效描述",
                "narration": "旁白描述"
            },
            "duration": 3
        }
    ],
    "summary": "整体风格总结，包含视觉风格、色彩、光线、音频风格等（中文）"
}
```

## 字段说明

### framing（景别）
- Extreme Close-up: 极特写（眼睛、嘴唇等局部）
- Close-up: 特写（面部）
- Medium Close-up: 中近景（胸部以上）
- Medium Shot: 中景（腰部以上）
- Medium Wide: 中远景（膝盖以上）
- Wide Shot: 远景（全身）
- Extreme Wide: 极远景（环境为主）

### angle（角度）
- Eye Level: 平视
- Low Angle: 仰视
- High Angle: 俯视
- Bird Eye: 鸟瞰
- Dutch Angle: 倾斜角度

### movement（运动）
- Static: 静止
- Push In: 推镜头
- Pull Out: 拉镜头
- Pan: 摇镜头（水平）
- Tilt: 倾斜镜头（垂直）
- Tracking: 跟踪镜头
- Dolly: 移动镜头
- Zoom: 变焦

### shot_description（场景描述）
详细描述画面内容，包括：
- 人物动作和表情
- 物品和道具
- 光线条件
- 色彩和氛围
- 构图特点

### audio（音频）
- bgm: 背景音乐描述，如果没有则为null
- sfx: 音效描述，如果没有则为null
- narration: 旁白描述，如果没有则为null

### duration（时长）
每个镜头的持续时间（秒），整数

## 优化原则
1. 每个场景生成一个shot对象
2. shot_description要详细生动，体现食物/人物的质感
3. framing/angle/movement使用英文专业术语
4. shot_description和summary使用中文描述
5. 确保与原视频的镜头语言一致
6. 如果提供了关键帧，减少对人物外观的详细描述
7. 只输出JSON，不要包含任何其他文字或markdown标记"""

            user_prompt = f"""请根据以下信息生成专业的JSON格式Shot Breakdown：

【原始提示词】
{prompt}

"""
            
            if context:
                if context.get('audio_content'):
                    user_prompt += f"""【音频内容参考】
{context['audio_content'][:200]}

"""
                
                if context.get('shot_breakdown'):
                    shot = context['shot_breakdown']
                    user_prompt += f"""【分镜信息】
- 景别：{shot.get('framing', 'Medium Shot')}
- 角度：{shot.get('angle', 'Eye Level')}
- 运动：{shot.get('movement', 'Static')}
- 时长：{shot.get('duration', 4)}秒

"""
                
                if context.get('keyframe_quality'):
                    kq = context['keyframe_quality']
                    if kq.get('quality_level') == 'high':
                        user_prompt += """【关键帧质量】高质量，已提供清晰的视觉参考，无需详细描述人物外观。

"""
                    else:
                        user_prompt += """【关键帧质量】中等/低质量，需要补充人物外观描述。

"""
                
                if context.get('needs_character_description') == False:
                    user_prompt += """【重要提示】已使用原视频关键帧作为参考，请减少对人物外观和环境的详细描述，专注于动作、情感和镜头运动。

"""
                
                if context.get('scene_order', 0) > 0:
                    user_prompt += f"""【场景顺序】第{context['scene_order']}个场景，请确保与前一场景的连续性。

"""
                
                if context.get('previous_scene_info'):
                    prev = context['previous_scene_info']
                    if prev.get('shot_breakdown'):
                        prev_shot = prev['shot_breakdown']
                        user_prompt += f"""【上一场景信息】
- 景别：{prev_shot.get('framing', '未知')}
- 动作：{prev_shot.get('shot_description', '未知')[:50]}

请确保当前场景与上一场景自然衔接。

"""
            
            user_prompt += """请生成专业的Shot Breakdown表格和Summary："""

            from dashscope import Generation
            
            optimized_prompt = None
            
            for key_index in range(len(self.api_keys)):
                self.api_key = self.api_keys[key_index]
                logger.info(f"使用API密钥 {self.api_key[:10]}... 尝试优化提示词")
                
                try:
                    response = Generation.call(
                        api_key=self.api_key,
                        model="qwen-plus-latest",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        result_format="message"
                    )
                    
                    logger.debug(f"模型响应状态码: {response.status_code}")
                    
                    if response.status_code == 200:
                        if hasattr(response, 'output') and hasattr(response.output, 'choices'):
                            choice = response.output.choices[0]
                            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                                optimized_prompt = choice.message.content
                                logger.info("qwen-plus-latest提示词优化成功")
                                
                                optimized_prompt = optimized_prompt.strip()
                                
                                shot_description = self._extract_shot_description_from_json(optimized_prompt)
                                summary = self._extract_summary_from_json(optimized_prompt)
                                shot_breakdown = self._parse_shot_breakdown_json(optimized_prompt)
                                
                                return {
                                    "success": True,
                                    "original_prompt": prompt,
                                    "optimized_prompt": optimized_prompt,
                                    "shot_description": shot_description,
                                    "summary": summary,
                                    "shot_breakdown": shot_breakdown,
                                    "model": "qwen-plus-latest",
                                    "prompt_length": len(optimized_prompt)
                                }
                    else:
                        error_msg = f"提示词优化失败: HTTP {response.status_code}"
                        if hasattr(response, 'message'):
                            error_msg += f", 错误信息: {response.message}"
                        logger.error(error_msg)
                        if "InvalidApiKey" in str(response) or "api_key" in str(response).lower():
                            logger.error("API密钥无效，切换到下一个密钥")
                            continue
                except Exception as e:
                    logger.error(f"API密钥 {self.api_key[:10]}... 调用失败: {str(e)}")
                    if key_index < len(self.api_keys) - 1:
                        self.rotate_api_key()
                        continue
                    else:
                        break
            
            logger.warning("所有API密钥都尝试过，使用原始提示词")
            return {
                "success": True,
                "original_prompt": prompt,
                "optimized_prompt": prompt,
                "shot_description": prompt,
                "summary": "",
                "shot_breakdown": [],
                "model": "fallback",
                "note": "使用原始提示词"
            }
            
        except Exception as e:
            error_msg = f"提示词优化异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "optimized_prompt": prompt,
                "shot_description": prompt,
                "summary": "",
                "shot_breakdown": []
            }
    
    def _extract_shot_description_from_json(self, json_prompt: str) -> str:
        """
        从JSON格式的Shot Breakdown中提取Shot Description用于视频生成
        
        Args:
            json_prompt: JSON格式的提示词
            
        Returns:
            提取的Shot Description文本
        """
        try:
            import json
            import re
            
            json_str = json_prompt.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            
            descriptions = []
            shot_breakdown = data.get('shot_breakdown', [])
            
            for shot in shot_breakdown:
                shot_num = shot.get('shot_number', 1)
                framing = shot.get('framing', '')
                angle = shot.get('angle', '')
                movement = shot.get('movement', '')
                shot_desc = shot.get('shot_description', '')
                
                framing_angle = f"{framing}/{angle}" if framing and angle else framing or angle
                descriptions.append(f"Shot {shot_num}: {framing_angle}, {movement}. {shot_desc}")
            
            if descriptions:
                return '\n'.join(descriptions)
            else:
                return json_prompt
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            return json_prompt
        except Exception as e:
            logger.error(f"提取Shot Description失败: {str(e)}")
            return json_prompt
    
    def _extract_summary_from_json(self, json_prompt: str) -> str:
        """
        从JSON格式的提示词中提取Summary部分
        
        Args:
            json_prompt: JSON格式的提示词
            
        Returns:
            Summary文本
        """
        try:
            import json
            
            json_str = json_prompt.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            return data.get('summary', '')
                
        except Exception as e:
            logger.error(f"提取Summary失败: {str(e)}")
            return ""
    
    def _parse_shot_breakdown_json(self, json_prompt: str) -> list:
        """
        从JSON格式的提示词中解析完整的shot_breakdown列表
        
        Args:
            json_prompt: JSON格式的提示词
            
        Returns:
            shot_breakdown列表
        """
        try:
            import json
            
            json_str = json_prompt.strip()
            if json_str.startswith('```json'):
                json_str = json_str[7:]
            if json_str.startswith('```'):
                json_str = json_str[3:]
            if json_str.endswith('```'):
                json_str = json_str[:-3]
            json_str = json_str.strip()
            
            data = json.loads(json_str)
            return data.get('shot_breakdown', [])
                
        except Exception as e:
            logger.error(f"解析shot_breakdown失败: {str(e)}")
            return []
    
    def _extract_shot_description_from_table(self, table_prompt: str) -> str:
        """
        从Shot Breakdown表格中提取Shot Description用于视频生成（兼容旧格式）
        
        Args:
            table_prompt: 完整的表格提示词
            
        Returns:
            提取的Shot Description文本
        """
        try:
            import re
            
            lines = table_prompt.split('\n')
            descriptions = []
            
            for line in lines:
                if '|' in line and not line.strip().startswith('|---') and not line.strip().startswith('| Shot'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 4:
                        shot_num = parts[0]
                        framing_angle = parts[1]
                        movement = parts[2]
                        shot_desc = parts[3] if len(parts) > 3 else ""
                        
                        if shot_desc and not shot_desc.startswith('Shot'):
                            descriptions.append(f"Shot {shot_num}: {framing_angle}, {movement}. {shot_desc}")
            
            if descriptions:
                return '\n'.join(descriptions)
            else:
                return table_prompt
                
        except Exception as e:
            logger.error(f"提取Shot Description失败: {str(e)}")
            return table_prompt
    
    def _extract_summary(self, table_prompt: str) -> str:
        """
        从提示词中提取Summary部分
        
        Args:
            table_prompt: 完整的提示词
            
        Returns:
            Summary文本
        """
        try:
            if '## Summary' in table_prompt:
                parts = table_prompt.split('## Summary')
                if len(parts) > 1:
                    summary = parts[1].strip()
                    if '##' in summary:
                        summary = summary.split('##')[0].strip()
                    return summary
            return ""
        except Exception as e:
            logger.error(f"提取Summary失败: {str(e)}")
            return ""
    
    def _extract_shot_info(self, slice_info: Dict[str, Any], scene_index: int) -> Dict[str, Any]:
        shot_info = {
            "shot_number": scene_index + 1,
            "framing": "Medium Shot",
            "angle": "Eye Level",
            "movement": "Static",
            "duration": slice_info.get('duration', 4)
        }
        
        if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
            vl_result = slice_info['vl_analysis'].get('analysis_result', {})
            camera_info = vl_result.get('camera', '')
            
            framing_keywords = {
                'extreme close-up': 'Extreme Close-up',
                'close-up': 'Close-up',
                'medium close-up': 'Medium Close-up',
                'medium shot': 'Medium Shot',
                'medium wide': 'Medium Wide',
                'wide shot': 'Wide Shot',
                'extreme wide': 'Extreme Wide',
                '全景': 'Wide Shot',
                '中景': 'Medium Shot',
                '近景': 'Close-up',
                '特写': 'Extreme Close-up',
                '远景': 'Extreme Wide'
            }
            
            for keyword, framing in framing_keywords.items():
                if keyword in camera_info.lower():
                    shot_info['framing'] = framing
                    break
            
            if '仰视' in camera_info or 'low angle' in camera_info.lower():
                shot_info['angle'] = 'Low Angle'
            elif '俯视' in camera_info or 'high angle' in camera_info.lower():
                shot_info['angle'] = 'High Angle'
            elif '鸟瞰' in camera_info or 'bird' in camera_info.lower():
                shot_info['angle'] = 'Bird Eye'
            
            movement_keywords = {
                '推': 'Push In',
                '拉': 'Pull Out',
                '摇': 'Pan',
                '移': 'Tracking',
                '跟': 'Following',
                '静止': 'Static',
                '固定': 'Static',
                'push': 'Push In',
                'pull': 'Pull Out',
                'pan': 'Pan',
                'tilt': 'Tilt',
                'tracking': 'Tracking',
                'static': 'Static'
            }
            
            for keyword, movement in movement_keywords.items():
                if keyword in camera_info.lower():
                    shot_info['movement'] = movement
                    break
        
        if 'analysis' in slice_info:
            analysis = slice_info['analysis']
            if isinstance(analysis, dict):
                storyboards = analysis.get('storyboards', [])
                if storyboards:
                    for sb in storyboards[:1]:
                        if isinstance(sb, dict):
                            if sb.get('framing'):
                                shot_info['framing'] = sb['framing']
                            if sb.get('angle'):
                                shot_info['angle'] = sb['angle']
                            if sb.get('movement'):
                                shot_info['movement'] = sb['movement']
        
        return shot_info
    
    def download_video(self, video_url: str, local_path: str) -> Dict[str, Any]:
        try:
            logger.info(f"开始下载视频: {video_url}")
            logger.info(f"保存路径: {local_path}")
            
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
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
    
    def generate_structured_prompt(self, slice_info: Dict[str, Any], scene_index: int, 
                                   previous_scene_info: Dict[str, Any] = None,
                                   global_character_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        生成结构化的视频脚本提示词，包含Shot Breakdown和Summary
        
        Args:
            slice_info: 切片信息，包含analysis, vl_analysis, audio_content等
            scene_index: 场景索引
            previous_scene_info: 上一个场景的信息（用于保持连续性）
            global_character_profile: 全局人物档案（用于保持人物一致性）
            
        Returns:
            结构化的提示词数据
        """
        try:
            logger.info(f"开始生成结构化提示词，场景 {scene_index + 1}")
            
            keyframes = slice_info.get('keyframes', [])
            keyframe_quality = self._assess_keyframe_quality(keyframes)
            
            shot_info = self._extract_shot_info(slice_info, scene_index)
            visual_content = self._extract_visual_content(slice_info, keyframe_quality)
            audio_info = self._extract_audio_info(slice_info)
            
            if global_character_profile and visual_content.get('needs_character_in_prompt'):
                if not visual_content.get('character_anchor'):
                    visual_content['character_anchor'] = global_character_profile
                    visual_content['characters'] = global_character_profile.get('description', '')
            
            shot_breakdown = self._build_shot_breakdown(
                scene_index + 1, shot_info, visual_content, audio_info,
                slice_info.get('duration', 4)
            )
            
            video_prompt = self._build_video_prompt(
                shot_breakdown, scene_index, previous_scene_info,
                visual_content, keyframe_quality
            )
            
            optimize_context = {
                'audio_content': slice_info.get('audio_content', ''),
                'keyframes': keyframes,
                'scene_order': scene_index + 1,
                'shot_breakdown': shot_breakdown,
                'keyframe_quality': keyframe_quality,
                'needs_character_description': keyframe_quality.get('needs_character_description', True),
                'optimization_focus': '镜头语言,动作描述,场景连续性'
            }
            
            if previous_scene_info:
                optimize_context['previous_scene_info'] = previous_scene_info
            
            optimize_result = self.optimize_prompt_with_qwen_plus_latest(video_prompt, optimize_context)
            
            if optimize_result.get('success'):
                optimized_prompt = optimize_result.get('optimized_prompt', video_prompt)
                style_elements = optimize_result.get('style_elements', {})
            else:
                optimized_prompt = video_prompt
                style_elements = {}
            
            return {
                'success': True,
                'scene_id': scene_index + 1,
                'shot_breakdown': shot_breakdown,
                'shot_info': shot_info,
                'visual_content': visual_content,
                'audio_info': audio_info,
                'video_prompt': video_prompt,
                'optimized_prompt': optimized_prompt,
                'style_elements': style_elements,
                'keyframe_quality': keyframe_quality,
                'start_time': slice_info.get('start_time', 0),
                'end_time': slice_info.get('end_time', 0),
                'duration': slice_info.get('duration', 4)
            }
            
        except Exception as e:
            error_msg = f"生成结构化提示词失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _extract_shot_info(self, slice_info: Dict[str, Any], scene_index: int) -> Dict[str, Any]:
        shot_info = {
            "shot_number": scene_index + 1,
            "framing": "Medium Shot",
            "angle": "Eye Level",
            "movement": "Static",
            "duration": slice_info.get('duration', 4)
        }
        
        if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
            vl_result = slice_info['vl_analysis'].get('analysis_result', {})
            camera_info = vl_result.get('camera', '')
            
            framing_keywords = {
                'extreme close-up': 'Extreme Close-up',
                'close-up': 'Close-up',
                'medium close-up': 'Medium Close-up',
                'medium shot': 'Medium Shot',
                'medium wide': 'Medium Wide',
                'wide shot': 'Wide Shot',
                'long shot': 'Long Shot',
                'extreme wide': 'Extreme Wide Shot',
                '全景': 'Wide Shot',
                '中景': 'Medium Shot',
                '近景': 'Close-up',
                '特写': 'Extreme Close-up'
            }
            
            angle_keywords = {
                'eye level': 'Eye Level',
                'low angle': 'Low Angle',
                'high angle': 'High Angle',
                'top-down': 'Top-down',
                'dutch angle': 'Dutch Angle',
                '平视': 'Eye Level',
                '仰视': 'Low Angle',
                '俯视': 'High Angle'
            }
            
            movement_keywords = {
                'static': 'Static',
                'tracking': 'Tracking',
                'pan': 'Pan',
                'tilt': 'Tilt',
                'zoom in': 'Zoom In',
                'zoom out': 'Zoom Out',
                'dolly': 'Dolly',
                'handheld': 'Handheld',
                '静止': 'Static',
                '跟拍': 'Tracking',
                '推': 'Zoom In',
                '拉': 'Zoom Out'
            }
            
            camera_lower = camera_info.lower() if camera_info else ''
            
            for keyword, framing in framing_keywords.items():
                if keyword in camera_lower:
                    shot_info['framing'] = framing
                    break
            
            for keyword, angle in angle_keywords.items():
                if keyword in camera_lower:
                    shot_info['angle'] = angle
                    break
            
            for keyword, movement in movement_keywords.items():
                if keyword in camera_lower:
                    shot_info['movement'] = movement
                    break
        
        return shot_info
    
    def _assess_keyframe_quality(self, keyframes: List[str]) -> Dict[str, Any]:
        """
        评估关键帧质量，判断是否需要补充人物描述
        
        Args:
            keyframes: 关键帧路径列表
            
        Returns:
            质量评估结果
        """
        quality_result = {
            "has_valid_keyframes": False,
            "character_clarity": 0.0,
            "character_detected": False,
            "face_detected": False,
            "quality_level": "low",
            "needs_character_description": True,
            "assessment_details": {}
        }
        
        if not keyframes:
            quality_result["assessment_details"]["reason"] = "没有关键帧"
            return quality_result
        
        valid_keyframes = [kf for kf in keyframes if kf and os.path.exists(kf)]
        if not valid_keyframes:
            quality_result["assessment_details"]["reason"] = "关键帧文件不存在"
            return quality_result
        
        quality_result["has_valid_keyframes"] = True
        
        try:
            from PIL import Image
            import numpy as np
            
            total_clarity = 0.0
            character_detected_count = 0
            face_detected_count = 0
            
            for kf_path in valid_keyframes[:3]:
                try:
                    img = Image.open(kf_path)
                    img_array = np.array(img)
                    
                    brightness = np.mean(img_array)
                    contrast = np.std(img_array)
                    
                    if brightness > 50 and brightness < 200 and contrast > 30:
                        frame_clarity = min(1.0, (contrast / 50.0) * (1 - abs(brightness - 128) / 128))
                    else:
                        frame_clarity = 0.3
                    
                    total_clarity += frame_clarity
                    
                    if 'vl_analysis' in locals() or True:
                        pass
                    
                except Exception as e:
                    logger.debug(f"评估关键帧质量失败: {kf_path}, 错误: {str(e)}")
                    total_clarity += 0.3
            
            quality_result["character_clarity"] = total_clarity / len(valid_keyframes)
            
            if quality_result["character_clarity"] >= 0.7:
                quality_result["quality_level"] = "high"
                quality_result["needs_character_description"] = False
            elif quality_result["character_clarity"] >= 0.4:
                quality_result["quality_level"] = "medium"
                quality_result["needs_character_description"] = True
            else:
                quality_result["quality_level"] = "low"
                quality_result["needs_character_description"] = True
            
            quality_result["assessment_details"] = {
                "valid_keyframe_count": len(valid_keyframes),
                "average_clarity": round(quality_result["character_clarity"], 2),
                "quality_level": quality_result["quality_level"]
            }
            
        except Exception as e:
            logger.error(f"关键帧质量评估失败: {str(e)}")
            quality_result["needs_character_description"] = True
        
        return quality_result
    
    def _extract_visual_content(self, slice_info: Dict[str, Any], 
                                 keyframe_quality: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        提取视觉内容，根据关键帧质量智能决定是否需要人物描述
        
        Args:
            slice_info: 切片信息
            keyframe_quality: 关键帧质量评估结果
            
        Returns:
            视觉内容字典
        """
        visual_content = {
            "characters": "",
            "environment": "",
            "action": "",
            "emotion": "",
            "visual_style": "",
            "atmosphere": "",
            "time": "",
            "location": "",
            "color_notes": "",
            "lighting": "",
            "character_anchor": None,
            "needs_character_in_prompt": True
        }
        
        if keyframe_quality is None:
            keyframes = slice_info.get('keyframes', [])
            keyframe_quality = self._assess_keyframe_quality(keyframes)
        
        visual_content["needs_character_in_prompt"] = keyframe_quality.get("needs_character_description", True)
        
        if 'analysis' in slice_info:
            analysis = slice_info['analysis']
            if isinstance(analysis, dict):
                storyboards = analysis.get('storyboards', [])
                if storyboards:
                    for sb in storyboards[:1]:
                        if isinstance(sb, dict):
                            visual_content['environment'] = sb.get('description', '')
                            visual_content['action'] = sb.get('action', '')
                
                raw_analysis = analysis.get('raw_analysis', '')
                if raw_analysis:
                    visual_content['environment'] = visual_content['environment'] or raw_analysis[:200]
        
        if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
            vl_result = slice_info['vl_analysis'].get('analysis_result', {})
            
            if 'style' in vl_result:
                visual_content['visual_style'] = vl_result['style']
            if 'action' in vl_result:
                visual_content['action'] = vl_result['action']
            if 'emotion' in vl_result:
                visual_content['emotion'] = vl_result['emotion']
            if 'atmosphere' in vl_result:
                visual_content['atmosphere'] = vl_result['atmosphere']
            if 'mood' in vl_result:
                visual_content['emotion'] = visual_content['emotion'] or vl_result['mood']
            if 'time' in vl_result:
                visual_content['time'] = vl_result['time']
            if 'location' in vl_result:
                visual_content['location'] = vl_result['location']
            if 'color' in vl_result:
                visual_content['color_notes'] = vl_result['color']
            if 'lighting' in vl_result:
                visual_content['lighting'] = vl_result['lighting']
            
            if visual_content["needs_character_in_prompt"]:
                character_info = self._extract_character_anchor(vl_result)
                if character_info:
                    visual_content['characters'] = character_info.get('description', '')
                    visual_content['character_anchor'] = character_info
        
        return visual_content
    
    def _extract_character_anchor(self, vl_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从视觉分析结果中提取人物锚点信息
        
        Args:
            vl_result: 视觉分析结果
            
        Returns:
            人物锚点信息
        """
        character_anchor = {
            "description": "",
            "appearance": {},
            "clothing": {},
            "position": ""
        }
        
        if 'characters' in vl_result:
            chars = vl_result['characters']
            if isinstance(chars, str):
                character_anchor['description'] = chars
            elif isinstance(chars, dict):
                character_anchor['description'] = chars.get('description', '')
                character_anchor['appearance'] = {
                    'hair': chars.get('hair', ''),
                    'skin': chars.get('skin', ''),
                    'body_type': chars.get('body_type', ''),
                    'age': chars.get('age', ''),
                    'gender': chars.get('gender', '')
                }
                character_anchor['clothing'] = {
                    'type': chars.get('clothing_type', ''),
                    'color': chars.get('clothing_color', ''),
                    'style': chars.get('clothing_style', '')
                }
                character_anchor['position'] = chars.get('position', 'center')
        
        if 'character' in vl_result and not character_anchor['description']:
            character_anchor['description'] = vl_result['character']
        
        appearance_fields = ['hair', 'skin', 'body_type', 'age', 'gender', 'face', 'eyes']
        for field in appearance_fields:
            if field in vl_result and field not in character_anchor['appearance']:
                character_anchor['appearance'][field] = vl_result[field]
        
        clothing_fields = ['clothing', 'outfit', 'dress', 'clothing_color', 'clothing_style']
        for field in clothing_fields:
            if field in vl_result and field not in character_anchor['clothing']:
                character_anchor['clothing'][field] = vl_result[field]
        
        if not character_anchor['description'] and not character_anchor['appearance'] and not character_anchor['clothing']:
            return None
        
        return character_anchor
    
    def _extract_audio_info(self, slice_info: Dict[str, Any]) -> Dict[str, Any]:
        audio_info = {
            "bgm": "",
            "sfx": [],
            "narration": "",
            "dialogue": ""
        }
        
        audio_content = slice_info.get('audio_content', '')
        if audio_content:
            audio_info['dialogue'] = audio_content
            audio_info['narration'] = audio_content[:100] + "..." if len(audio_content) > 100 else audio_content
        
        if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
            vl_result = slice_info['vl_analysis'].get('analysis_result', {})
            
            if 'bgm' in vl_result:
                audio_info['bgm'] = vl_result['bgm']
            if 'sfx' in vl_result:
                sfx = vl_result['sfx']
                if isinstance(sfx, list):
                    audio_info['sfx'] = sfx
                elif isinstance(sfx, str):
                    audio_info['sfx'] = [sfx]
        
        return audio_info
    
    def _build_shot_breakdown(self, shot_number: int, shot_info: Dict,
                              visual_content: Dict, audio_info: Dict,
                              duration: float) -> Dict[str, Any]:
        shot_description_parts = []
        
        if visual_content.get('environment'):
            shot_description_parts.append(visual_content['environment'])
        if visual_content.get('characters'):
            shot_description_parts.append(f"人物: {visual_content['characters']}")
        if visual_content.get('action'):
            shot_description_parts.append(f"动作: {visual_content['action']}")
        if visual_content.get('emotion'):
            shot_description_parts.append(f"表情: {visual_content['emotion']}")
        
        shot_description = ". ".join(shot_description_parts) if shot_description_parts else "Scene content"
        
        audio_parts = []
        if audio_info.get('bgm'):
            audio_parts.append(f"BGM: {audio_info['bgm']}")
        if audio_info.get('sfx'):
            audio_parts.append(f"SFX: {', '.join(audio_info['sfx'])}")
        if audio_info.get('narration'):
            audio_parts.append(f"Narration: {audio_info['narration']}")
        
        audio_description = "; ".join(audio_parts) if audio_parts else "Background audio"
        
        return {
            "shot_number": shot_number,
            "framing": shot_info.get('framing', 'Medium Shot'),
            "angle": shot_info.get('angle', 'Eye Level'),
            "movement": shot_info.get('movement', 'Static'),
            "shot_description": shot_description,
            "audio": audio_description,
            "duration": duration
        }
    
    def _build_video_prompt(self, shot_breakdown: Dict, scene_index: int, 
                            previous_scene_info: Dict[str, Any] = None,
                            visual_content: Dict[str, Any] = None,
                            keyframe_quality: Dict[str, Any] = None) -> str:
        """
        构建视频生成提示词，根据关键帧质量动态调整内容
        
        Args:
            shot_breakdown: 分镜信息
            scene_index: 场景索引
            previous_scene_info: 上一场景信息
            visual_content: 视觉内容信息
            keyframe_quality: 关键帧质量评估结果
            
        Returns:
            构建好的提示词
        """
        prompt_parts = [
            f"Shot {shot_breakdown['shot_number']}:",
            f"[Camera] {shot_breakdown['framing']} / {shot_breakdown['angle']} / {shot_breakdown['movement']}"
        ]
        
        needs_character = True
        if keyframe_quality:
            needs_character = keyframe_quality.get('needs_character_description', True)
        
        if visual_content and needs_character:
            if visual_content.get('characters'):
                prompt_parts.append(f"[Character] {visual_content['characters']}")
            
            character_anchor = visual_content.get('character_anchor')
            if character_anchor:
                appearance = character_anchor.get('appearance', {})
                clothing = character_anchor.get('clothing', {})
                
                anchor_parts = []
                if appearance.get('hair'):
                    anchor_parts.append(f"hair: {appearance['hair']}")
                if appearance.get('skin'):
                    anchor_parts.append(f"skin: {appearance['skin']}")
                if clothing.get('color') or clothing.get('type'):
                    clothing_desc = f"{clothing.get('color', '')} {clothing.get('type', '')}".strip()
                    if clothing_desc:
                        anchor_parts.append(f"outfit: {clothing_desc}")
                
                if anchor_parts:
                    prompt_parts.append(f"[Character Anchor] {', '.join(anchor_parts)}")
        
        if visual_content:
            if visual_content.get('action'):
                prompt_parts.append(f"[Action] {visual_content['action']}")
            if visual_content.get('emotion'):
                prompt_parts.append(f"[Emotion] {visual_content['emotion']}")
            if visual_content.get('atmosphere'):
                prompt_parts.append(f"[Atmosphere] {visual_content['atmosphere']}")
        
        prompt_parts.append(f"[Duration] {shot_breakdown['duration']}s")
        
        if scene_index > 0 and previous_scene_info:
            prompt_parts.append("[Continuity] Maintain visual consistency with previous shot")
        
        if keyframe_quality and keyframe_quality.get('has_valid_keyframes'):
            if keyframe_quality.get('first_frame_constraint'):
                prompt_parts.append("[Constraint] First frame must match reference keyframe exactly")
        
        return " | ".join(prompt_parts)
    
    def generate_overall_summary(self, scene_prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据所有场景生成整体风格总结
        
        Args:
            scene_prompts: 所有场景的提示词列表
            
        Returns:
            整体风格总结
        """
        try:
            visual_style = {
                "color_palette": [],
                "lighting": "",
                "camera_style": "",
                "description": ""
            }
            audio_style = {
                "bgm_style": "",
                "sfx_style": "",
                "narration_style": "",
                "description": ""
            }
            
            for scene in scene_prompts:
                visual_content = scene.get('visual_content', {})
                audio_info = scene.get('audio_info', {})
                
                if visual_content.get('color_notes'):
                    color = visual_content['color_notes']
                    if color not in visual_style['color_palette']:
                        visual_style['color_palette'].append(color)
                
                if visual_content.get('lighting') and not visual_style['lighting']:
                    visual_style['lighting'] = visual_content['lighting']
                
                if visual_content.get('visual_style') and not visual_style['camera_style']:
                    visual_style['camera_style'] = visual_content['visual_style']
                
                if audio_info.get('bgm') and not audio_style['bgm_style']:
                    audio_style['bgm_style'] = audio_info['bgm']
                
                if audio_info.get('sfx') and not audio_style['sfx_style']:
                    audio_style['sfx_style'] = ", ".join(audio_info['sfx'][:3])
            
            return {
                'success': True,
                'overall_visual_style': {
                    "color_palette": visual_style['color_palette'],
                    "lighting": visual_style['lighting'] or "Standard commercial lighting",
                    "camera_style": visual_style['camera_style'] or "Dynamic but stable, social media aesthetic",
                    "description": "High-saturation color palette with vibrant visuals. Commercial-grade lighting with attention to detail."
                },
                'overall_audio_style': {
                    "bgm_style": audio_style['bgm_style'] or "Upbeat, engaging background music",
                    "sfx_style": audio_style['sfx_style'] or "Natural ambient sounds with accent effects",
                    "narration_style": "Clear, engaging narration matching the visual tone",
                    "description": "Audio designed to complement the visual style with appropriate BGM, SFX, and narration."
                }
            }
            
        except Exception as e:
            error_msg = f"生成整体风格总结失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def build_global_character_profile(self, video_slices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从所有视频切片中构建全局人物档案，确保人物一致性
        
        Args:
            video_slices: 所有视频切片信息列表
            
        Returns:
            全局人物档案
        """
        try:
            logger.info("开始构建全局人物档案")
            
            character_profiles = {}
            main_character = None
            main_character_appearances = 0
            
            for i, slice_info in enumerate(video_slices):
                if 'vl_analysis' in slice_info and slice_info['vl_analysis'].get('success'):
                    vl_result = slice_info['vl_analysis'].get('analysis_result', {})
                    
                    character_info = self._extract_character_anchor(vl_result)
                    
                    if character_info and character_info.get('description'):
                        char_key = self._generate_character_key(character_info)
                        
                        if char_key not in character_profiles:
                            character_profiles[char_key] = {
                                'description': character_info.get('description', ''),
                                'appearance': character_info.get('appearance', {}),
                                'clothing': character_info.get('clothing', {}),
                                'first_appearance': i,
                                'appearance_count': 1,
                                'positions': [character_info.get('position', 'center')]
                            }
                        else:
                            character_profiles[char_key]['appearance_count'] += 1
                            character_profiles[char_key]['positions'].append(character_info.get('position', 'center'))
                            
                            existing_appearance = character_profiles[char_key]['appearance']
                            new_appearance = character_info.get('appearance', {})
                            for key, value in new_appearance.items():
                                if value and not existing_appearance.get(key):
                                    existing_appearance[key] = value
                            
                            existing_clothing = character_profiles[char_key]['clothing']
                            new_clothing = character_info.get('clothing', {})
                            for key, value in new_clothing.items():
                                if value and not existing_clothing.get(key):
                                    existing_clothing[key] = value
            
            for char_key, profile in character_profiles.items():
                if profile['appearance_count'] > main_character_appearances:
                    main_character = char_key
                    main_character_appearances = profile['appearance_count']
            
            if main_character and main_character in character_profiles:
                main_profile = character_profiles[main_character]
                
                description_parts = []
                appearance = main_profile.get('appearance', {})
                clothing = main_profile.get('clothing', {})
                
                if appearance.get('gender'):
                    description_parts.append(appearance['gender'])
                if appearance.get('age'):
                    description_parts.append(f"{appearance['age']} years old")
                if appearance.get('hair'):
                    description_parts.append(f"{appearance['hair']} hair")
                if appearance.get('skin'):
                    description_parts.append(f"{appearance['skin']} skin")
                if clothing.get('color') or clothing.get('type'):
                    clothing_desc = f"{clothing.get('color', '')} {clothing.get('type', '')}".strip()
                    if clothing_desc:
                        description_parts.append(f"wearing {clothing_desc}")
                
                global_profile = {
                    'success': True,
                    'character_id': main_character,
                    'description': ', '.join(description_parts) if description_parts else main_profile.get('description', ''),
                    'appearance': appearance,
                    'clothing': clothing,
                    'appearance_count': main_profile['appearance_count'],
                    'first_appearance': main_profile['first_appearance'],
                    'all_characters': character_profiles
                }
                
                logger.info(f"全局人物档案构建完成，主角色出现 {main_profile['appearance_count']} 次")
                return global_profile
            
            logger.warning("未检测到明确的人物信息")
            return {
                'success': True,
                'character_id': None,
                'description': '',
                'appearance': {},
                'clothing': {},
                'note': 'No clear character detected in video'
            }
            
        except Exception as e:
            error_msg = f"构建全局人物档案失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }
    
    def _generate_character_key(self, character_info: Dict[str, Any]) -> str:
        """
        根据人物特征生成唯一标识键
        
        Args:
            character_info: 人物信息
            
        Returns:
            人物标识键
        """
        appearance = character_info.get('appearance', {})
        key_parts = []
        
        if appearance.get('gender'):
            key_parts.append(appearance['gender'])
        if appearance.get('hair'):
            key_parts.append(appearance['hair'][:20])
        if appearance.get('skin'):
            key_parts.append(appearance['skin'][:10])
        
        if key_parts:
            return '_'.join(key_parts).lower().replace(' ', '_')
        else:
            return 'unknown_character'