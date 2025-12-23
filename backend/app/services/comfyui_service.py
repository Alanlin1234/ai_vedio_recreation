# ComfyUI集成服务

import requests
import json
import os
import time
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ComfyUIService:
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "base_url": "http://localhost:8188",
            "timeout": 60,
            "keyframe_workflow_id": "keyframe_generation",
            "video_workflow_id": "video_from_keyframes",
            "poll_interval": 2,
            "check_timeout": 10  # 服务检查超时时间
        }
        
        self.config = config or default_config
        self.base_url = self.config.get("base_url", "http://localhost:8188")
        self.timeout = self.config.get("timeout", 60)
        self.check_timeout = self.config.get("check_timeout", 10)
        self.keyframe_workflow_id = self.config.get("keyframe_workflow_id", "keyframe_generation")
        self.video_workflow_id = self.config.get("video_workflow_id", "video_from_keyframes")
        self.poll_interval = self.config.get("poll_interval", 2)
        
        logger.info(f"ComfyUI服务初始化，基础URL: {self.base_url}")
        logger.info(f"ComfyUI配置: timeout={self.timeout}, check_timeout={self.check_timeout}, poll_interval={self.poll_interval}")
    
    def check_service_status(self) -> Dict[str, Any]:
        try:
            logger.info(f"正在检查ComfyUI服务状态，URL: {self.base_url}")
            
            # 检查服务器是否响应
            response = requests.get(
                f"{self.base_url}/system_stats",
                timeout=self.check_timeout
            )
            
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"ComfyUI服务状态正常，系统信息: {stats}")
                return {
                    "success": True,
                    "status": "running",
                    "system_stats": stats,
                    "message": "ComfyUI服务运行正常"
                }
            else:
                error_msg = f"ComfyUI服务响应异常，状态码: {response.status_code}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "status": "error",
                    "error": error_msg
                }
        except requests.ConnectionError:
            error_msg = f"无法连接到ComfyUI服务: {self.base_url}"
            logger.error(error_msg)
            return {
                "success": False,
                "status": "unreachable",
                "error": error_msg
            }
        except requests.Timeout:
            error_msg = f"ComfyUI服务超时: {self.base_url}"
            logger.error(error_msg)
            return {
                "success": False,
                "status": "timeout",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"检查ComfyUI服务状态失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "status": "error",
                "error": error_msg
            }
    
    def generate_keyframes(self, prompt: Dict[str, Any], num_keyframes: int = 5) -> Dict[str, Any]:
        try:
            logger.info(f"=== 开始生成关键帧流程 ===")
            logger.info(f"生成参数: 数量={num_keyframes}, 提示词长度={len(str(prompt))}")
            
            # 1. 检查服务状态
            service_status = self.check_service_status()
            if not service_status["success"]:
                logger.error(f"关键帧生成失败: ComfyUI服务状态异常 - {service_status['error']}")
                return {
                    "success": False,
                    "error": f"ComfyUI服务状态异常: {service_status['error']}",
                    "service_status": service_status
                }
            
            # 2. 构建ComfyUI工作流数据
            workflow_data = self._build_keyframe_workflow(prompt, num_keyframes)
            logger.debug(f"构建的工作流数据: {json.dumps(workflow_data, indent=2, ensure_ascii=False)[:500]}...")
            
            # 3. 验证工作流模板
            validation_result = self._validate_workflow(workflow_data)
            if not validation_result["success"]:
                logger.error(f"关键帧生成失败: 工作流验证失败 - {validation_result['error']}")
                return {
                    "success": False,
                    "error": f"工作流验证失败: {validation_result['error']}",
                    "workflow_validation": validation_result
                }
            
            # 4. 发送生成请求
            logger.info(f"发送关键帧生成请求到: {self.base_url}/prompt")
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow_data},
                timeout=self.timeout
            )
            
            logger.info(f"关键帧生成请求响应状态: {response.status_code}")
            logger.debug(f"响应头: {dict(response.headers)}")
            logger.debug(f"响应内容: {response.text[:1000]}...")
            
            if response.status_code != 200:
                error_msg = f"生成关键帧失败: HTTP {response.status_code} - {response.text[:500]}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "status_code": response.status_code,
                    "response_content": response.text
                }
            
            result = response.json()
            logger.info(f"关键帧生成请求返回结果: {json.dumps(result)}")
            
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                error_msg = "生成关键帧失败: 未返回prompt_id"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response_data": result
                }
            
            logger.info(f"获取到prompt_id: {prompt_id}，开始轮询结果")
            
            # 5. 轮询结果
            keyframe_result = self._poll_comfyui_result(prompt_id)
            
            if keyframe_result.get("success"):
                logger.info(f"=== 关键帧生成成功 ===, prompt_id: {prompt_id}")
                return keyframe_result
            else:
                logger.error(f"=== 关键帧生成失败 ===, prompt_id: {prompt_id}, 错误: {keyframe_result.get('error')}")
                return keyframe_result
                
        except requests.exceptions.RequestException as e:
            error_msg = f"生成关键帧网络异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "RequestException"
            }
        except json.JSONDecodeError as e:
            error_msg = f"生成关键帧JSON解析异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": "JSONDecodeError"
            }
        except Exception as e:
            error_msg = f"生成关键帧异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "exception_type": type(e).__name__
            }
    
    def generate_video_from_keyframes(self, keyframe_urls: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"=== 开始从关键帧生成视频流程 ===")
            logger.info(f"生成参数: 关键帧数量={len(keyframe_urls)}, 提示词长度={len(str(prompt))}")
            
            # 1. 检查服务状态
            service_status = self.check_service_status()
            if not service_status["success"]:
                logger.error(f"视频生成失败: ComfyUI服务状态异常 - {service_status['error']}")
                return {
                    "success": False,
                    "error": f"ComfyUI服务状态异常: {service_status['error']}",
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
            
            # 3. 构建ComfyUI工作流数据
            workflow_data = self._build_video_workflow(keyframe_urls, prompt)
            logger.debug(f"构建的视频生成工作流数据: {json.dumps(workflow_data, indent=2, ensure_ascii=False)[:500]}...")
            
            # 4. 验证工作流模板
            validation_result = self._validate_workflow(workflow_data)
            if not validation_result["success"]:
                logger.error(f"视频生成失败: 工作流验证失败 - {validation_result['error']}")
                return {
                    "success": False,
                    "error": f"工作流验证失败: {validation_result['error']}",
                    "workflow_validation": validation_result
                }
            
            # 5. 发送生成请求
            logger.info(f"发送视频生成请求到: {self.base_url}/prompt")
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow_data},
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
            
            prompt_id = result.get("prompt_id")
            
            if not prompt_id:
                error_msg = "生成视频失败: 未返回prompt_id"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response_data": result
                }
            
            logger.info(f"获取到prompt_id: {prompt_id}，开始轮询结果")
            
            # 6. 轮询结果
            video_result = self._poll_comfyui_result(prompt_id)
            
            if video_result.get("success"):
                logger.info(f"=== 视频生成成功 ===, prompt_id: {prompt_id}")
                return video_result
            else:
                logger.error(f"=== 视频生成失败 ===, prompt_id: {prompt_id}, 错误: {video_result.get('error')}")
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
    
    def _validate_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始验证工作流，工作流节点数量: {len(workflow)}")
            
            # 基本验证
            if not isinstance(workflow, dict):
                return {
                    "success": False,
                    "error": "工作流必须是字典类型"
                }
            
            if len(workflow) == 0:
                return {
                    "success": False,
                    "error": "工作流不能为空"
                }
            
            # 检查关键节点
            required_nodes = {
                "keyframe_generation": ["CheckpointLoaderSimple", "KSampler", "SaveImage"],
                "video_from_keyframes": ["LoadImagesFromURL", "VideoFromImages", "SaveVideo"]
            }
            
            # 检查每个节点是否有必要的字段
            node_classes = []
            for node_id, node_config in workflow.items():
                if not isinstance(node_config, dict):
                    return {
                        "success": False,
                        "error": f"节点 {node_id} 必须是字典类型"
                    }
                
                # 检查class_type字段
                if "class_type" not in node_config:
                    return {
                        "success": False,
                        "error": f"节点 {node_id} 缺少class_type字段"
                    }
                
                node_classes.append(node_config["class_type"])
                
                # 检查inputs字段
                if "inputs" not in node_config:
                    return {
                        "success": False,
                        "error": f"节点 {node_id} 缺少inputs字段"
                    }
            
            logger.info(f"工作流节点类型: {node_classes}")
            
            # 验证成功
            return {
                "success": True,
                "message": "工作流验证通过",
                "node_count": len(workflow),
                "node_classes": node_classes
            }
            
        except Exception as e:
            error_msg = f"工作流验证异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg
            }
    
    def _build_keyframe_workflow(self, prompt: Dict[str, Any], num_keyframes: int) -> Dict[str, Any]:
        try:
            logger.info(f"开始构建关键帧工作流，关键帧数量: {num_keyframes}")
            
            # 从JSON提示词中提取关键信息
            scene_description = prompt.get("description", "")
            video_prompt = prompt.get("video_prompt", "")
            style_elements = prompt.get("style_elements", {})
            
            # 提取技术参数
            technical_params = prompt.get("technical_params", {})
            width = technical_params.get("width", 1024)
            height = technical_params.get("height", 1024)
            steps = technical_params.get("steps", 20)
            cfg_scale = technical_params.get("cfg_scale", 8.0)
            sampler_name = technical_params.get("sampler_name", "euler")
            scheduler = technical_params.get("scheduler", "normal")
            
            logger.info(f"工作流技术参数: width={width}, height={height}, steps={steps}, cfg_scale={cfg_scale}")
            logger.info(f"使用的提示词: {video_prompt[:100]}...")
            
            # 基础ComfyUI工作流模板
            workflow = {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": cfg_scale,
                        "denoise": 1,
                        "latent_image": ["5", 0],
                        "model": ["4", 0],
                        "negative": ["7", 0],
                        "positive": ["6", 0],
                        "sampler_name": sampler_name,
                        "scheduler": scheduler,
                        "seed": int(time.time()),  # 使用时间戳作为随机种子
                        "steps": steps
                    }
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": "sd_xl_base_1.0.safetensors"
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "batch_size": num_keyframes,
                        "height": height,
                        "width": width
                    }
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": video_prompt  # 使用视频提示词
                    }
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": "bad quality, blurry, low resolution, distorted, ugly, deformed, watermark, text"
                    }
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2]
                    }
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": f"keyframe_{int(time.time())}",
                        "images": ["8", 0]
                    }
                }
            }
            
            logger.info(f"关键帧工作流构建完成，节点数量: {len(workflow)}")
            return workflow
            
        except Exception as e:
            logger.error(f"构建关键帧工作流异常: {str(e)}", exc_info=True)
            # 返回简化的默认工作流作为 fallback
            logger.warning("使用默认工作流作为fallback")
            return {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": 8,
                        "denoise": 1,
                        "latent_image": ["5", 0],
                        "model": ["4", 0],
                        "negative": ["7", 0],
                        "positive": ["6", 0],
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "seed": 8566257, "steps": 20
                    }
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": "sd_xl_base_1.0.safetensors"
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "batch_size": num_keyframes,
                        "height": 1024, "width": 1024
                    }
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": prompt.get("video_prompt", "A beautiful scene")
                    }
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": "bad quality, blurry, low resolution"
                    }
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2]
                    }
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "keyframe",
                        "images": ["8", 0]
                    }
                }
            }
    
    def _build_video_workflow(self, keyframe_urls: List[str], prompt: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始构建视频生成工作流，关键帧数量: {len(keyframe_urls)}")
            
            # 从提示词中提取视频参数
            video_params = prompt.get("video_params", {})
            frame_rate = video_params.get("frame_rate", 24)
            resolution = video_params.get("resolution", "1024x768")
            duration = video_params.get("duration", 10)
            
            logger.info(f"视频生成参数: frame_rate={frame_rate}, resolution={resolution}, duration={duration}s")
            logger.info(f"关键帧URL示例: {keyframe_urls[:2]}...")
            
            # 构建视频生成工作流
            workflow = {
                "1": {
                    "class_type": "LoadImagesFromURL",
                    "inputs": {
                        "urls": json.dumps(keyframe_urls),
                        "batch_size": len(keyframe_urls)
                    }
                },
                "2": {
                    "class_type": "VideoFromImages",
                    "inputs": {
                        "frame_rate": frame_rate,
                        "images": ["1", 0],
                        "loop_count": 1,
                        "resolution": resolution
                    }
                },
                "3": {
                    "class_type": "SaveVideo",
                    "inputs": {
                        "filename_prefix": f"scene_video_{int(time.time())}",
                        "video": ["2", 0],
                        "format": "mp4"
                    }
                }
            }
            
            logger.info(f"视频生成工作流构建完成，节点数量: {len(workflow)}")
            return workflow
            
        except Exception as e:
            error_msg = f"构建视频生成工作流异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # 返回简化的默认工作流作为 fallback
            logger.warning("使用默认视频工作流作为fallback")
            return {
                "1": {
                    "class_type": "LoadImagesFromURL",
                    "inputs": {
                        "urls": json.dumps(keyframe_urls)
                    }
                },
                "2": {
                    "class_type": "VideoFromImages",
                    "inputs": {
                        "frame_rate": 24,
                        "images": ["1", 0],
                        "loop_count": 1
                    }
                },
                "3": {
                    "class_type": "SaveVideo",
                    "inputs": {
                        "filename_prefix": "scene_video",
                        "video": ["2", 0]
                    }
                }
            }
    
    def _poll_comfyui_result(self, prompt_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        elapsed_time = 0
        attempt_count = 0
        
        logger.info(f"=== 开始轮询ComfyUI结果 ===")
        logger.info(f"轮询参数: prompt_id={prompt_id}, max_wait_time={max_wait_time}s, poll_interval={self.poll_interval}s")
        
        while elapsed_time < max_wait_time:
            attempt_count += 1
            elapsed_time = time.time() - start_time
            
            try:
                logger.debug(f"轮询尝试 {attempt_count}，已耗时: {elapsed_time:.2f}s")
                
                response = requests.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=self.timeout
                )
                
                logger.debug(f"轮询响应状态: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"轮询响应状态异常: {response.status_code}，内容: {response.text[:500]}...")
                    time.sleep(self.poll_interval)
                    continue
                
                # 解析响应内容
                try:
                    history = response.json()
                    logger.debug(f"轮询响应JSON解析成功")
                except json.JSONDecodeError as e:
                    logger.error(f"轮询响应JSON解析失败: {str(e)}，响应内容: {response.text[:1000]}...")
                    time.sleep(self.poll_interval)
                    continue
                
                # 检查prompt_id是否在历史记录中
                if prompt_id not in history:
                    logger.info(f"轮询: prompt_id {prompt_id} 尚未生成完成，继续等待...")
                    time.sleep(self.poll_interval)
                    continue
                
                item = history[prompt_id]
                logger.debug(f"轮询: 找到prompt_id {prompt_id} 的历史记录")
                
                # 检查生成状态
                if "status" in item:
                    logger.info(f"轮询: 当前状态 - {item['status']}")
                    if item['status'] == "error":
                        error_msg = item.get("error", "未知错误")
                        logger.error(f"轮询: 生成失败 - {error_msg}")
                        return {
                            "success": False,
                            "error": f"生成失败: {error_msg}",
                            "prompt_id": prompt_id,
                            "status": item['status']
                        }
                
                # 检查输出
                if "outputs" in item and item["outputs"]:
                    logger.info(f"轮询: 生成完成，找到输出结果！")
                    
                    # 解析输出
                    outputs = item["outputs"]
                    result = {
                        "success": True,
                        "prompt_id": prompt_id,
                        "outputs": outputs,
                        "node_results": {},
                        "total_time": elapsed_time,
                        "attempts": attempt_count,
                        "status": item.get("status", "completed")
                    }
                    
                    # 提取生成的文件
                    generated_files = []
                    for node_id, node_output in outputs.items():
                        logger.debug(f"轮询: 处理节点 {node_id} 的输出")
                        
                        if "images" in node_output:
                            images = node_output["images"]
                            result["node_results"][node_id] = images
                            for img in images:
                                generated_files.append({
                                    "type": "image",
                                    "filename": img.get("filename", ""),
                                    "path": img.get("path", ""),
                                    "width": img.get("width", 0),
                                    "height": img.get("height", 0)
                                })
                        elif "videos" in node_output:
                            videos = node_output["videos"]
                            result["node_results"][node_id] = videos
                            for video in videos:
                                generated_files.append({
                                    "type": "video",
                                    "filename": video.get("filename", ""),
                                    "path": video.get("path", ""),
                                    "duration": video.get("duration", 0)
                                })
                    
                    logger.info(f"轮询: 成功提取 {len(generated_files)} 个生成文件")
                    result["generated_files"] = generated_files
                    
                    logger.info(f"=== 轮询完成 ===")
                    logger.info(f"轮询结果: 成功={result['success']}, 总耗时={elapsed_time:.2f}s, 尝试次数={attempt_count}, 生成文件数={len(generated_files)}")
                    
                    return result
                
                # 继续等待
                remaining_time = max_wait_time - elapsed_time
                logger.info(f"轮询: 输出尚未生成，继续等待... 剩余时间: {remaining_time:.2f}s")
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
        
        error_msg = f"生成超时，超过 {max_wait_time} 秒，尝试次数: {attempt_count}"
        logger.error(f"=== 轮询失败 ===")
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "prompt_id": prompt_id,
            "total_time": max_wait_time,
            "attempts": attempt_count
        }
    
    def get_workflow_template(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        # 这里可以从配置文件或数据库加载预定义工作流
        workflow_templates = {
            "keyframe_generation": self._build_keyframe_workflow({}, 5),
            "video_from_keyframes": self._build_video_workflow([], {})
        }
        
        return workflow_templates.get(workflow_id)

