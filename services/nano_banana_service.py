# Nano Banana集成服务

import requests
import json
import time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class NanoBananaService:
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "base_url": "https://api.nanobanana.ai/v1",
            "api_key": "your-nano-banana-api-key",
            "timeout": 60,
            "poll_interval": 5,
            "check_timeout": 10  # 服务检查超时时间
        }
        
        self.config = config or default_config
        self.base_url = self.config.get("base_url", "https://api.nanobanana.ai/v1")
        self.api_key = self.config.get("api_key", "your-nano-banana-api-key")
        self.timeout = self.config.get("timeout", 60)
        self.check_timeout = self.config.get("check_timeout", 10)
        self.poll_interval = self.config.get("poll_interval", 5)
        
        # 设置请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"Nano Banana服务初始化，基础URL: {self.base_url}")
        logger.info(f"Nano Banana配置: timeout={self.timeout}, check_timeout={self.check_timeout}, poll_interval={self.poll_interval}")
    
    def check_service_status(self) -> Dict[str, Any]:
        try:
            logger.info(f"正在检查Nano Banana服务状态，URL: {self.base_url}")
            
            # 发送测试请求到API的健康检查端点
            response = requests.get(
                f"{self.base_url}/health",
                headers=self.headers,
                timeout=self.check_timeout
            )
            
            if response.status_code == 200:
                health_info = response.json()
                logger.info(f"Nano Banana服务状态正常，健康信息: {health_info}")
                return {
                    "success": True,
                    "status": "running",
                    "health_info": health_info,
                    "message": "Nano Banana服务运行正常"
                }
            else:
                error_msg = f"Nano Banana服务响应异常，状态码: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "status": "error",
                    "error": error_msg
                }
        except requests.ConnectionError:
            error_msg = f"无法连接到Nano Banana服务: {self.base_url}"
            logger.error(error_msg)
            return {
                "success": False,
                "status": "unreachable",
                "error": error_msg
            }
        except requests.Timeout:
            error_msg = f"Nano Banana服务超时: {self.base_url}"
            logger.error(error_msg)
            return {
                "success": False,
                "status": "timeout",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"检查Nano Banana服务状态失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "status": "error",
                "error": error_msg
            }
    
    def generate_video_from_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"=== 开始使用Nano Banana生成视频 ===")
            logger.info(f"生成参数: 提示词长度={len(str(prompt))}")
            
            # 1. 检查服务状态
            service_status = self.check_service_status()
            if not service_status["success"]:
                logger.error(f"视频生成失败: Nano Banana服务状态异常 - {service_status['error']}")
                return {
                    "success": False,
                    "error": f"Nano Banana服务状态异常: {service_status['error']}",
                    "service_status": service_status
                }
            
            # 2. 构建API请求数据
            video_data = self._build_video_generation_request(prompt)
            logger.debug(f"构建的API请求数据: {json.dumps(video_data, indent=2, ensure_ascii=False)[:500]}...")
            
            # 3. 发送生成请求
            logger.info(f"发送视频生成请求到: {self.base_url}/videos/generate")
            response = requests.post(
                f"{self.base_url}/videos/generate",
                headers=self.headers,
                json=video_data,
                timeout=self.timeout
            )
            
            logger.info(f"视频生成请求响应状态: {response.status_code}")
            logger.debug(f"响应头: {dict(response.headers)}")
            logger.debug(f"响应内容: {response.text[:1000]}...")
            
            if response.status_code != 200:
                error_msg = f"生成视频失败: HTTP {response.status_code} - {response.text[:500]}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response_content": response.text
                }
            
            result = response.json()
            logger.info(f"视频生成请求返回结果: {json.dumps(result)}")
            
            task_id = result.get("task_id") or result.get("id")
            
            if not task_id:
                error_msg = "生成视频失败: 未返回task_id或id"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response_data": result
                }
            
            logger.info(f"获取到task_id: {task_id}，开始轮询结果")
            
            # 4. 轮询结果
            video_result = self._poll_video_result(task_id)
            
            if video_result.get("success"):
                logger.info(f"=== 视频生成成功 ===, task_id: {task_id}")
                return video_result
            else:
                logger.error(f"=== 视频生成失败 ===, task_id: {task_id}, 错误: {video_result.get('error')}")
                return video_result
                
        except requests.exceptions.RequestException as e:
            error_msg = f"生成视频网络异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "RequestException"
            }
        except json.JSONDecodeError as e:
            error_msg = f"生成视频JSON解析异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "JSONDecodeError"
            }
        except Exception as e:
            error_msg = f"生成视频异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": type(e).__name__
            }
    
    def generate_video_from_keyframes(self, keyframe_urls: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"=== 开始使用Nano Banana从关键帧生成视频 ===")
            logger.info(f"生成参数: 关键帧数量={len(keyframe_urls)}, 提示词长度={len(str(prompt))}")
            
            # 1. 检查服务状态
            service_status = self.check_service_status()
            if not service_status["success"]:
                logger.error(f"视频生成失败: Nano Banana服务状态异常 - {service_status['error']}")
                return {
                    "success": False,
                    "error": f"Nano Banana服务状态异常: {service_status['error']}",
                    "service_status": service_status
                }
            
            # 2. 验证关键帧URLs
            if not keyframe_urls or len(keyframe_urls) == 0:
                error_msg = "视频生成失败: 没有提供关键帧URLs"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            logger.info(f"关键帧URLs验证通过，数量: {len(keyframe_urls)}")
            
            # 3. 构建API请求数据
            video_data = self._build_keyframe_video_request(keyframe_urls, prompt)
            logger.debug(f"构建的关键帧视频请求数据: {json.dumps(video_data, indent=2, ensure_ascii=False)[:500]}...")
            
            # 4. 发送生成请求
            logger.info(f"发送关键帧视频生成请求到: {self.base_url}/videos/generate-from-keyframes")
            response = requests.post(
                f"{self.base_url}/videos/generate-from-keyframes",
                headers=self.headers,
                json=video_data,
                timeout=self.timeout
            )
            
            logger.info(f"关键帧视频生成请求响应状态: {response.status_code}")
            logger.debug(f"响应头: {dict(response.headers)}")
            logger.debug(f"响应内容: {response.text[:1000]}...")
            
            if response.status_code != 200:
                error_msg = f"生成视频失败: HTTP {response.status_code} - {response.text[:500]}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response_content": response.text
                }
            
            result = response.json()
            logger.info(f"关键帧视频生成请求返回结果: {json.dumps(result)}")
            
            task_id = result.get("task_id") or result.get("id")
            
            if not task_id:
                error_msg = "生成视频失败: 未返回task_id或id"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response_data": result
                }
            
            logger.info(f"获取到task_id: {task_id}，开始轮询结果")
            
            # 5. 轮询结果
            video_result = self._poll_video_result(task_id)
            
            if video_result.get("success"):
                logger.info(f"=== 关键帧视频生成成功 ===, task_id: {task_id}")
                return video_result
            else:
                logger.error(f"=== 关键帧视频生成失败 ===, task_id: {task_id}, 错误: {video_result.get('error')}")
                return video_result
                
        except requests.exceptions.RequestException as e:
            error_msg = f"生成视频网络异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "RequestException"
            }
        except json.JSONDecodeError as e:
            error_msg = f"生成视频JSON解析异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "JSONDecodeError"
            }
        except Exception as e:
            error_msg = f"生成视频异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": type(e).__name__
            }
    
    def _build_video_generation_request(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始构建视频生成请求")
            
            # 从JSON提示词中提取关键信息
            scene_description = prompt.get("description", "")
            video_prompt = prompt.get("video_prompt", "")
            style_elements = prompt.get("style_elements", {})
            
            # 提取技术参数
            technical_params = prompt.get("technical_params", {})
            width = technical_params.get("width", 1280)
            height = technical_params.get("height", 720)
            duration = technical_params.get("duration", 10)
            fps = technical_params.get("fps", 24)
            
            logger.info(f"视频技术参数: width={width}, height={height}, duration={duration}s, fps={fps}")
            logger.info(f"使用的提示词: {video_prompt[:100]}...")
            
            # 构建Nano Banana API请求
            video_request = {
                "prompt": video_prompt,
                "description": scene_description,
                "params": {
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "fps": fps,
                    "style": style_elements.get("style", "cinematic"),
                    "quality": style_elements.get("quality", "high"),
                    "motion": style_elements.get("motion", "natural")
                }
            }
            
            # 添加额外参数（如果存在）
            additional_params = prompt.get("additional_params", {})
            if additional_params:
                video_request["params"].update(additional_params)
            
            logger.info(f"视频生成请求构建完成")
            return video_request
            
        except Exception as e:
            logger.error(f"构建视频生成请求异常: {str(e)}", exc_info=True)
            # 返回默认请求作为fallback
            return {
                "prompt": prompt.get("video_prompt", "A beautiful scene"),
                "params": {
                    "width": 1280,
                    "height": 720,
                    "duration": 10,
                    "fps": 24,
                    "style": "cinematic"
                }
            }
    
    def _build_keyframe_video_request(self, keyframe_urls: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始构建关键帧视频生成请求，关键帧数量: {len(keyframe_urls)}")
            
            # 从提示词中提取视频参数
            video_params = prompt.get("video_params", {})
            frame_rate = video_params.get("frame_rate", 24)
            duration = video_params.get("duration", 10)
            
            logger.info(f"视频生成参数: frame_rate={frame_rate}, duration={duration}s")
            logger.info(f"关键帧URL示例: {keyframe_urls[:2]}...")
            
            # 构建关键帧视频请求
            video_request = {
                "keyframes": keyframe_urls,
                "params": {
                    "frame_rate": frame_rate,
                    "duration": duration,
                    "transition_style": "smooth",
                    "motion_blur": "medium"
                }
            }
            
            # 添加场景描述（如果存在）
            scene_description = prompt.get("description", "")
            if scene_description:
                video_request["description"] = scene_description
            
            logger.info(f"关键帧视频请求构建完成")
            return video_request
            
        except Exception as e:
            logger.error(f"构建关键帧视频请求异常: {str(e)}", exc_info=True)
            # 返回默认请求作为fallback
            return {
                "keyframes": keyframe_urls,
                "params": {
                    "frame_rate": 24,
                    "duration": 10
                }
            }
    
    def _poll_video_result(self, task_id: str, max_wait_time: int = 600) -> Dict[str, Any]:
        start_time = time.time()
        elapsed_time = 0
        attempt_count = 0
        
        logger.info(f"=== 开始轮询Nano Banana视频结果 ===")
        logger.info(f"轮询参数: task_id={task_id}, max_wait_time={max_wait_time}s, poll_interval={self.poll_interval}s")
        
        while elapsed_time < max_wait_time:
            attempt_count += 1
            elapsed_time = time.time() - start_time
            
            try:
                logger.debug(f"轮询尝试 {attempt_count}，已耗时: {elapsed_time:.2f}s")
                
                response = requests.get(
                    f"{self.base_url}/videos/{task_id}",
                    headers=self.headers,
                    timeout=self.timeout
                )
                
                logger.debug(f"轮询响应状态: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"轮询响应状态异常: {response.status_code}，内容: {response.text[:500]}...")
                    time.sleep(self.poll_interval)
                    continue
                
                # 解析响应内容
                try:
                    video_info = response.json()
                    logger.debug(f"轮询响应JSON解析成功")
                except json.JSONDecodeError as e:
                    logger.error(f"轮询响应JSON解析失败: {str(e)}，响应内容: {response.text[:1000]}...")
                    time.sleep(self.poll_interval)
                    continue
                
                # 检查任务状态
                status = video_info.get("status", "pending")
                logger.info(f"轮询: 当前状态 - {status}")
                
                if status == "failed":
                    error_msg = video_info.get("error", "未知错误")
                    logger.error(f"轮询: 生成失败 - {error_msg}")
                    return {
                        "success": False,
                        "error": f"生成失败: {error_msg}",
                        "task_id": task_id,
                        "status": status,
                        "video_info": video_info
                    }
                
                if status == "completed":
                    logger.info(f"轮询: 生成完成，找到视频结果！")
                    
                    # 解析输出
                    result = {
                        "success": True,
                        "task_id": task_id,
                        "video_info": video_info,
                        "outputs": {
                            "video_url": video_info.get("video_url"),
                            "thumbnail_url": video_info.get("thumbnail_url"),
                            "metadata": video_info.get("metadata", {})
                        },
                        "total_time": elapsed_time,
                        "attempts": attempt_count,
                        "status": status
                    }
                    
                    logger.info(f"=== 轮询完成 ===")
                    logger.info(f"轮询结果: 成功={result['success']}, 总耗时={elapsed_time:.2f}s, 尝试次数={attempt_count}")
                    logger.info(f"生成的视频URL: {result['outputs']['video_url']}")
                    
                    return result
                
                # 继续等待
                remaining_time = max_wait_time - elapsed_time
                logger.info(f"轮询: 视频生成中，当前状态: {status}，继续等待... 剩余时间: {remaining_time:.2f}s")
                time.sleep(self.poll_interval)
                
            except requests.exceptions.RequestException as e:
                error_msg = f"轮询网络异常: {str(e)}"
                logger.error(error_msg)
                time.sleep(self.poll_interval)
            except json.JSONDecodeError as e:
                error_msg = f"轮询JSON解析异常: {str(e)}"
                logger.error(error_msg)
                time.sleep(self.poll_interval)
            except Exception as e:
                error_msg = f"轮询异常: {str(e)}"
                logger.error(error_msg, exc_info=True)
                time.sleep(self.poll_interval)
        
        error_msg = f"视频生成超时，超过 {max_wait_time} 秒，尝试次数: {attempt_count}"
        logger.error(f"=== 轮询失败 ===")
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "task_id": task_id,
            "total_time": max_wait_time,
            "attempts": attempt_count
        }
    
    def get_video_info(self, video_id: str) -> Dict[str, Any]:
        try:
            logger.info(f"获取视频信息: {video_id}")
            
            response = requests.get(
                f"{self.base_url}/videos/{video_id}",
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                video_info = response.json()
                logger.info(f"成功获取视频信息: {video_id}")
                return {
                    "success": True,
                    "video_info": video_info
                }
            else:
                error_msg = f"获取视频信息失败: HTTP {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
        except Exception as e:
            error_msg = f"获取视频信息异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }

