# 视频创意重构系统主控制器

from typing import Dict, Any
import asyncio
import json
from .base_agent import BaseAgent
from app.services.douyin_service import DouyinService
from app.services.ffmpeg_service import FFmpegService
from app.services.comfyui_service import ComfyUIService
from app.services.qwen_vl_service import QwenVLService
from app.services.qwen72b_service import Qwen72BService


class VideoReconstructionAgent(BaseAgent):
    """视频创意重构系统主控制器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("VideoReconstructionAgent", config)
        
        # 初始化各个服务
        self.douyin_service = DouyinService()
        self.ffmpeg_service = FFmpegService()
        self.comfyui_service = ComfyUIService()
        
        # 获取配置并传递给AI服务
        from app.config.video_reconstruction_config import get_config
        config = get_config()
        
        # 初始化AI服务，传递正确的配置
        self.qwen_vl_service = QwenVLService(config.get("qwen_vl"))
        self.qwen72b_service = Qwen72BService(config.get("qwen_72b"))
        
        # 工作流状态跟踪
        self.workflow_state = {
            "video_acquired": False,
            "video_preprocessed": False,
            "content_analyzed": False,
            "story_reconstructed": False,
            "images_generated": False,
            "videos_generated": False,
            "final_synthesized": False
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行视频创意重构工作流
        
        工作流步骤：
        1. 视频获取和预处理（FFmpeg切片）
        2. 视频内容分析（Qwen-VL）
        3. 故事重构和扩展（Qwen-72B）
        4. 图像生成准备
        5. 图像和视频生成（ComfyUI）
        6. 最终视频合成（FFmpeg）
        """
        
        try:
            self.log_execution("start", "开始视频创意重构工作流")
            
            # 1. 视频获取和预处理
            video_data = await self._acquire_and_preprocess_video(input_data)
            if not video_data:
                return self.create_result(False, error="视频获取和预处理失败")
            
            self.workflow_state["video_acquired"] = True
            self.workflow_state["video_preprocessed"] = True
            
            # 2. 视频内容分析
            analysis_result = await self._analyze_video_content(video_data)
            if not analysis_result:
                return self.create_result(False, error="视频内容分析失败")
            
            video_data.update(analysis_result)
            self.workflow_state["content_analyzed"] = True
            
            # 3. 故事重构和扩展
            story_data = await self._reconstruct_story(video_data)
            if not story_data:
                return self.create_result(False, error="故事重构失败")
            
            video_data.update(story_data)
            self.workflow_state["story_reconstructed"] = True
            
            # 4. 图像生成准备
            image_generation_tasks = await self._prepare_image_generation(video_data)
            if not image_generation_tasks:
                return self.create_result(False, error="图像生成准备失败")
            
            video_data["image_generation_tasks"] = image_generation_tasks
            
            # 5. 图像和视频生成
            generation_result = await self._generate_images_and_videos(video_data)
            if not generation_result:
                return self.create_result(False, error="图像和视频生成失败")
            
            video_data.update(generation_result)
            self.workflow_state["images_generated"] = True
            self.workflow_state["videos_generated"] = True
            
            # 6. 最终视频合成
            final_result = await self._synthesize_final_video(video_data)
            if not final_result:
                return self.create_result(False, error="最终视频合成失败")
            
            video_data.update(final_result)
            self.workflow_state["final_synthesized"] = True
            
            self.log_execution("complete", "视频创意重构工作流执行成功")
            
            return self.create_result(True, {
                "video_data": video_data,
                "workflow_state": self.workflow_state,
                "final_video_path": final_result.get("final_video_path", ""),
                "reconstruction_success": True
            })
            
        except Exception as e:
            self.logger.error(f"视频创意重构工作流执行失败: {str(e)}")
            return self.create_result(False, error=str(e), context={"workflow_state": self.workflow_state})
    
    async def _acquire_and_preprocess_video(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """视频获取和预处理"""
        self.log_execution("step1", "开始视频获取和预处理")
        
        try:
            # 1. 获取视频来源
            video_source = input_data.get("video_source", "")
            video_url = input_data.get("video_url", "")
            local_file_path = input_data.get("local_file_path", "")
            
            video_info = None
            
            # 2. 根据来源获取视频
            if (video_source == "douyin" or video_source == "tiktok") and video_url:
                # 从抖音或TikTok获取视频
                video_info = await self._acquire_video_from_douyin(video_url)  # 暂时复用抖音获取逻辑，后续可扩展为独立方法
            elif local_file_path:
                # 使用本地视频文件
                video_info = {
                    "local_file_path": local_file_path,
                    "video_id": f"local_{hash(local_file_path)}",
                    "title": "本地视频",
                    "description": "本地视频文件"
                }
            else:
                self.logger.error(f"无效的视频来源或URL: source={video_source}, url={video_url}, local_path={local_file_path}")
                return None
            
            if not video_info:
                self.logger.error("无法获取视频信息")
                return None
            
            # 3. 视频预处理 - 检查是否需要重新切片
            skip_slicing = input_data.get("skip_slicing", False)
            existing_slices = input_data.get("video_slices", [])
            
            if skip_slicing and existing_slices:
                # 直接使用已有的切片数据
                self.logger.info("使用已有的切片数据，跳过FFmpeg切片步骤")
                preprocessed_data = {
                    "video_slices": existing_slices,
                    "audio_path": "",  # 暂时不处理音频
                    "slice_info": {}
                }
            else:
                # 使用FFmpeg进行视频切片
                preprocessed_data = await self._preprocess_video(video_info)
                if not preprocessed_data:
                    self.logger.error("视频预处理失败")
                    return None
            
            video_info.update(preprocessed_data)
            self.logger.info(f"视频获取和预处理成功: {video_info.get('title', '未知视频')}")
            
            return video_info
        except Exception as e:
            self.logger.error(f"视频获取和预处理失败: {str(e)}")
            return None
    
    async def _acquire_video_from_douyin(self, video_url: str, max_retries=3, retry_delay=2) -> Dict[str, Any]:
        """从抖音获取视频，带有重试机制"""
        for retry in range(max_retries):
            try:
                # 使用抖音服务获取视频信息（直接使用爬虫服务的API，避免异步事件循环冲突）
                from app.services.douyin_service import DouyinCrawlerClient
                from crawler_config.crawler_config import crawler_config
                
                client = DouyinCrawlerClient()
                
                # 直接将完整URL传递给get_video_info方法，无需提取ID
                # 该方法会自动处理完整URL和视频ID两种情况
                self.logger.info(f"尝试获取视频信息 (重试 {retry+1}/{max_retries}): {video_url}")
                video_info = await client.get_video_info(video_url, max_retries=2, retry_delay=1)
                
                if not video_info:
                    if retry < max_retries - 1:
                        self.logger.warning(f"获取抖音视频信息失败，{retry_delay}秒后重试...")
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        self.logger.error(f"获取抖音视频信息失败: {video_url}")
                        return None
                
                # 转换为系统需要的格式
                converted_info = {
                    'title': video_info.get('desc', ''),
                    'description': video_info.get('desc', ''),
                    'create_time': video_info.get('create_time', 0),
                    'duration': video_info.get('duration', 0),
                    'video_id': video_info.get('aweme_id', ''),
                    'video_url': video_url,  # 使用原始URL，方便后续下载
                    'play_count': video_info.get('play_count', 0),
                    'digg_count': video_info.get('digg_count', 0),
                    'comment_count': video_info.get('comment_count', 0),
                    'share_count': video_info.get('share_count', 0),
                    'collect_count': 0,
                    'author_nickname': video_info.get('author', ''),
                    'author_unique_id': video_info.get('author_id', ''),
                    'author_uid': video_info.get('author_id', ''),
                    'author_signature': '',
                    'author_follower_count': 0,
                    'author_following_count': 0,
                    'author_total_favorited': 0,
                    'dynamic_cover_url': video_info.get('cover_url', ''),
                    'tags': []
                }
                
                # 使用爬虫服务的下载API直接下载视频
                import httpx
                import os
                from datetime import datetime
                
                # 创建下载目录
                download_dir = os.path.join(os.getcwd(), 'downloads')
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir)
                
                # 生成文件名
                aweme_id = video_info.get('aweme_id', 'unknown')
                file_name = f"{aweme_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                local_file_path = os.path.join(download_dir, file_name)
                
                # 使用爬虫服务的下载端点下载视频
                self.logger.info(f"使用爬虫服务下载视频: {video_url}")
                download_api_url = f"{client.base_url}/api/download"
                
                async with httpx.AsyncClient(timeout=60.0) as httpx_client:
                    response = await httpx_client.get(download_api_url, params={
                        "url": video_url,
                        "with_watermark": False
                    })
                    response.raise_for_status()
                    
                    # 保存视频到本地
                    with open(local_file_path, 'wb') as f:
                        f.write(response.content)
                
                self.logger.info(f"视频下载成功: {local_file_path}")
                self.logger.info(f"视频文件大小: {os.path.getsize(local_file_path)} bytes")
                
                converted_info["local_file_path"] = local_file_path
                return converted_info
            except Exception as e:
                if retry < max_retries - 1:
                    self.logger.warning(f"从抖音获取视频失败 (重试 {retry+1}/{max_retries}): {str(e)}，{retry_delay}秒后重试...")
                    await asyncio.sleep(retry_delay)
                else:
                    self.logger.error(f"从抖音获取视频失败: {str(e)}")
                    return None
    
    async def _preprocess_video(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用FFmpeg进行视频预处理"""
        try:
            local_file_path = video_info.get("local_file_path", "")
            if not local_file_path:
                self.logger.error("没有视频文件路径")
                return None
            
            # 使用FFmpeg服务进行视频切片
            slice_result = await self.ffmpeg_service.slice_video(local_file_path)
            if not slice_result:
                self.logger.error("视频切片失败")
                return None
            
            # 提取音频
            audio_result = await self.ffmpeg_service.extract_audio(local_file_path)
            if not audio_result:
                self.logger.warning("音频提取失败，将继续处理")
            
            return {
                "video_slices": slice_result.get("slices", []),
                "audio_path": audio_result.get("audio_path", "") if audio_result else "",
                "slice_info": slice_result.get("slice_info", {})
            }
        except Exception as e:
            self.logger.error(f"视频预处理失败: {str(e)}")
            return None
    
    async def _analyze_video_content(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用Qwen-omni进行视频内容分析，生成完整故事分镜和脚本"""
        self.log_execution("step2", "开始视频内容分析")
        
        try:
            # 1. 获取视频切片
            video_slices = video_data.get("video_slices", [])
            if not video_slices:
                self.logger.error("没有视频切片可以分析")
                return None
            
            # 2. 使用Qwen-omni分析完整视频内容
            analysis_result = await self.qwen_vl_service.analyze_video_content(video_slices)
            if not analysis_result:
                self.logger.error("Qwen-omni视频分析失败")
                return None
            
            self.logger.info("Qwen-omni视频内容分析成功: 生成完整故事分析结果")
            
            # 3. 构建最终分析结果
            final_analysis = {
                "story_analysis": analysis_result[0],  # 使用第一个分析结果（完整故事分析）
                "total_slices_analyzed": len(video_slices)
            }
            
            return final_analysis
        except Exception as e:
            self.logger.error(f"视频内容分析失败: {str(e)}")
            return None
    
    async def _reconstruct_story(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用Qwen-omni生成的完整故事分析结果，无需额外重构"""
        self.log_execution("step3", "使用Qwen-omni生成的完整故事分析结果")
        
        try:
            # 1. 获取Qwen-omni生成的故事分析结果
            story_analysis = video_data.get("story_analysis", {})
            if not story_analysis:
                self.logger.error("没有Qwen-omni故事分析结果")
                return None
            
            self.logger.info("故事分析结果已由Qwen-omni生成，直接使用")
            
            # 2. 返回故事分析结果，包含分镜描述和脚本文本
            return {
                "story_data": story_analysis
            }
        except Exception as e:
            self.logger.error(f"处理故事分析结果失败: {str(e)}")
            return None
    
    async def _prepare_image_generation(self, video_data: Dict[str, Any]) -> list:
        """准备图像生成任务，使用Qwen-omni生成的分镜描述"""
        self.log_execution("step4", "开始图像生成准备")
        
        try:
            # 1. 获取故事分析结果
            story_data = video_data.get("story_data", {})
            if not story_data:
                self.logger.error("没有故事分析结果")
                return None
            
            # 2. 生成图像生成任务列表
            image_tasks = []
            
            # 3. 处理Qwen-omni生成的分镜结构
            storyboards = story_data.get("storyboards", []) or story_data.get("分镜结构", [])
            script_text = story_data.get("script_text", "") or story_data.get("脚本文本", "")
            
            # 如果有分镜结构，使用分镜结构生成图像任务
            if storyboards:
                for i, storyboard in enumerate(storyboards):
                    # 提取分镜描述
                    description = storyboard.get("description", "") or storyboard.get("分镜描述", "")
                    
                    # 生成图像生成任务
                    image_task = {
                        "task_id": f"storyboard_{i}",
                        "scene_description": description,
                        "prompt": description,  # 使用分镜描述作为prompt
                        "negative_prompt": "模糊, 低质量, 变形, 噪点, 过度曝光, 色彩失真, 比例失调",
                        "style": "realistic",
                        "aspect_ratio": "16:9",
                        "scene_order": i
                    }
                    image_tasks.append(image_task)
            
            # 如果没有分镜结构但有脚本文本，尝试从脚本文本中提取场景
            elif script_text:
                # 简单的脚本分割，实际项目中可能需要更复杂的解析
                scenes = script_text.split("\n\n")
                for i, scene in enumerate(scenes):
                    if scene.strip():
                        image_task = {
                            "task_id": f"script_scene_{i}",
                            "scene_description": scene.strip(),
                            "prompt": scene.strip(),  # 使用场景描述作为prompt
                            "negative_prompt": "模糊, 低质量, 变形, 噪点, 过度曝光, 色彩失真, 比例失调",
                            "style": "realistic",
                            "aspect_ratio": "16:9",
                            "scene_order": i
                        }
                        image_tasks.append(image_task)
            
            # 如果都没有，使用原始故事分析结果
            else:
                image_task = {
                    "task_id": "story_analysis",
                    "scene_description": json.dumps(story_data, ensure_ascii=False),
                    "prompt": json.dumps(story_data, ensure_ascii=False),
                    "negative_prompt": "模糊, 低质量, 变形, 噪点, 过度曝光, 色彩失真, 比例失调",
                    "style": "realistic",
                    "aspect_ratio": "16:9",
                    "scene_order": 0
                }
                image_tasks.append(image_task)
            
            self.logger.info(f"图像生成准备完成: 生成 {len(image_tasks)} 个图像任务")
            return image_tasks
        except Exception as e:
            self.logger.error(f"图像生成准备失败: {str(e)}")
            return None
    
    async def _generate_images_and_videos(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用ComfyUI生成图像和视频"""
        self.log_execution("step5", "开始图像和视频生成")
        
        try:
            # 1. 获取图像生成任务
            image_tasks = video_data.get("image_generation_tasks", [])
            if not image_tasks:
                self.logger.error("没有图像生成任务")
                return None
            
            # 2. 使用ComfyUI生成图像
            generated_images = []
            for task in image_tasks:
                image_result = await self.comfyui_service.generate_image(task)
                if image_result:
                    generated_images.append(image_result)
            
            if not generated_images:
                self.logger.error("图像生成失败")
                return None
            
            # 3. 使用ComfyUI生成视频片段
            generated_videos = []
            for image in generated_images:
                video_result = await self.comfyui_service.generate_video_from_image(image)
                if video_result:
                    generated_videos.append(video_result)
            
            if not generated_videos:
                self.logger.error("视频生成失败")
                return None
            
            self.logger.info(f"图像和视频生成成功: {len(generated_images)} 张图像, {len(generated_videos)} 个视频片段")
            
            return {
                "generated_images": generated_images,
                "generated_videos": generated_videos
            }
        except Exception as e:
            self.logger.error(f"图像和视频生成失败: {str(e)}")
            return None
    
    async def _synthesize_final_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用FFmpeg合成最终视频"""
        self.log_execution("step6", "开始最终视频合成")
        
        try:
            # 1. 获取生成的视频片段
            generated_videos = video_data.get("generated_videos", [])
            if not generated_videos:
                self.logger.error("没有生成的视频片段可以合成")
                return None
            
            # 2. 获取原始音频
            original_audio_path = video_data.get("audio_path", "")
            
            # 3. 使用FFmpeg合成最终视频
            final_video_path = await self.ffmpeg_service.synthesize_final_video(
                generated_videos,
                original_audio_path,
                video_data.get("story_data", {})
            )
            
            if not final_video_path:
                self.logger.error("最终视频合成失败")
                return None
            
            self.logger.info(f"最终视频合成成功: {final_video_path}")
            
            return {
                "final_video_path": final_video_path,
                "reconstructed_video_success": True
            }
        except Exception as e:
            self.logger.error(f"最终视频合成失败: {str(e)}")
            return None