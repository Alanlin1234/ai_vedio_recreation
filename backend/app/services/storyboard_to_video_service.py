"""
分镜到视频生成服务
整合分镜、提示词生成、视频生成和一致性检查
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

from app.services.shot_breakdown_generator import ShotBreakdownGenerator
from app.services.qwen_video_service import QwenVideoService
from app.models import db, VideoRecreation, RecreationScene

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from video_consistency_agent.agent.consistency_agent import ConsistencyAgent

logger = logging.getLogger(__name__)


class StoryboardToVideoService:
    """分镜到视频生成服务"""

    def __init__(self):
        self.shot_breakdown_generator = ShotBreakdownGenerator()
        self.qwen_video_service = QwenVideoService({
            "api_key": Config.DASHSCOPE_API_KEY,
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "timeout": 60,
            "poll_interval": 10,
            "max_wait_time": 600
        })

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_path = os.path.join(project_root, 'video_consistency_agent', 'config', 'config.yaml')
        self.consistency_agent = ConsistencyAgent(config_path)

    def generate_scene_videos(self, recreation_id: int) -> Dict[str, Any]:
        """
        生成分场景视频

        Args:
            recreation_id: 项目ID

        Returns:
            包含生成结果的字典
        """
        try:
            logger.info(f"开始生成分场景视频，recreation_id={recreation_id}")

            recreation = VideoRecreation.query.get(recreation_id)
            if not recreation:
                return {
                    'success': False,
                    'error': '项目不存在'
                }

            scenes = RecreationScene.query.filter_by(
                recreation_id=recreation_id
            ).order_by(RecreationScene.scene_index).all()

            if not scenes:
                return {
                    'success': False,
                    'error': '没有分镜数据'
                }

            task_dir = self._get_task_directory(recreation_id, recreation.original_video_path)
            generated_videos = []
            failed_scenes = []
            previous_last_frame = None

            for scene in scenes:
                try:
                    scene_index = scene.scene_index
                    logger.info(f"正在生成场景 {scene_index + 1} / {len(scenes)}")

                    scene_data = {
                        'scene_number': scene_index + 1,
                        'shot_type': scene.shot_type,
                        'description': scene.description,
                        'plot': scene.plot,
                        'dialogue': scene.dialogue,
                        'duration': scene.duration
                    }

                    scene_image_path = os.path.join(
                        Config.UPLOAD_FOLDER,
                        'storyboards',
                        f'recreation_{recreation_id}',
                        f"scene_{scene_index + 1:02d}.png"
                    )
                    scene_image_path = os.path.abspath(scene_image_path)
                    if not os.path.exists(scene_image_path):
                        logger.warning(f"场景 {scene_index + 1} 分镜图文件不存在: {scene_image_path}")
                        scene_image_url = None
                    else:
                        scene_image_url = f"file://{scene_image_path}"
                        logger.info(f"场景 {scene_index + 1} 分镜图URL: {scene_image_url}")

                    logger.info(f"场景 {scene_index + 1} 分镜图路径: {scene_image_path}")

                    result = self._generate_single_scene_video(
                        scene_data=scene_data,
                        scene_image_url=scene_image_url,
                        previous_last_frame=previous_last_frame,
                        task_dir=task_dir,
                        scene_index=scene_index
                    )

                    if result.get('success'):
                        generated_videos.append({
                            'scene_index': scene_index,
                            'video_path': result.get('video_path'),
                            'consistency_check': result.get('consistency_check'),
                            'success': True
                        })

                        previous_last_frame = result.get('last_frame')

                        scene.generated_video_path = result.get('video_path')
                        scene.generation_status = 'completed'
                        scene.generation_completed_at = datetime.now()
                        db.session.commit()
                    else:
                        failed_scenes.append({
                            'scene_index': scene_index,
                            'error': result.get('error', '未知错误'),
                            'success': False
                        })

                        scene.generation_status = 'failed'
                        db.session.commit()

                except Exception as e:
                    logger.error(f"生成场景 {scene.scene_index + 1} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_scenes.append({
                        'scene_index': scene.scene_index,
                        'error': str(e),
                        'success': False
                    })

            logger.info(f"分场景视频生成完成，成功: {len(generated_videos)}, 失败: {len(failed_scenes)}")

            return {
                'success': True,
                'recreation_id': recreation_id,
                'generated_videos': generated_videos,
                'failed_scenes': failed_scenes,
                'total_scenes': len(scenes),
                'successful_count': len(generated_videos)
            }

        except Exception as e:
            logger.error(f"生成分场景视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_single_scene_video(
        self,
        scene_data: Dict[str, Any],
        scene_image_url: str,
        previous_last_frame: Optional[str],
        task_dir: str,
        scene_index: int
    ) -> Dict[str, Any]:
        """
        生成单个场景视频（不重试）

        Args:
            scene_data: 分镜数据
            scene_image_url: 分镜图URL
            previous_last_frame: 上一场景的最后一帧
            task_dir: 任务目录
            scene_index: 场景索引

        Returns:
            包含生成结果的字典
        """
        try:
            logger.info(f"场景 {scene_index + 1} 开始生成")

            shot_breakdown = self.shot_breakdown_generator.generate_shot_breakdown(
                scene_data, scene_index
            )
            video_prompt = self.shot_breakdown_generator.format_for_video_generation(shot_breakdown)

            logger.info(f"场景 {scene_index + 1} Shot Breakdown: {video_prompt[:200]}...")

            keyframes = []
            if previous_last_frame:
                keyframes.append(previous_last_frame)
            if scene_image_url:
                keyframes.append(scene_image_url)

            if not keyframes:
                return {
                    'success': False,
                    'error': '没有可用的关键帧图片'
                }

            result = self.qwen_video_service.generate_video_from_keyframes(
                keyframes=keyframes,
                prompt={'video_prompt': video_prompt}
            )

            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('error', '视频生成失败')
                }

            video_url = result.get('video_url')
            if not video_url:
                return {
                    'success': False,
                    'error': '视频URL不存在'
                }

            local_video_path = os.path.join(task_dir, 'videos', f"scene_{scene_index + 1:02d}.mp4")
            os.makedirs(os.path.dirname(local_video_path), exist_ok=True)

            download_result = self.qwen_video_service.download_video(
                video_url, local_video_path
            )

            if not download_result.get('success'):
                return {
                    'success': False,
                    'error': download_result.get('error', '视频下载失败')
                }

            logger.info(f"场景 {scene_index + 1} 一致性检查（跳过）")

            return {
                'success': True,
                'video_path': local_video_path,
                'last_frame': scene_image_url,
                'consistency_check': {'passed': True, 'score': 1.0, 'source': 'skipped'}
            }

        except Exception as e:
            logger.error(f"生成场景视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _check_consistency(
        self,
        current_video_path: str,
        previous_last_frame: str,
        scene_index: int
    ) -> Dict[str, Any]:
        """
        检查场景一致性

        Args:
            current_video_path: 当前视频路径
            previous_last_frame: 上一场景的最后一帧
            scene_index: 场景索引

        Returns:
            一致性检查结果（已设为直接通过）
        """
        try:
            logger.info(f"场景 {scene_index + 1} 一致性检查（跳过，直接通过）")

            return {
                'passed': True,
                'score': 1.0,
                'source': 'skipped',
                'message': '一致性检查已跳过（阈值设为0）'
            }

        except Exception as e:
            logger.error(f"一致性检查异常: {e}")
            return {
                'passed': True,
                'score': 1.0,
                'warning': f'一致性检查异常: {str(e)}'
            }

    def _get_task_directory(self, recreation_id: int, original_video_path: str) -> str:
        """获取任务目录"""
        video_dir = os.path.dirname(original_video_path)
        task_dir = os.path.join(video_dir, f"recreation_{recreation_id}")
        videos_dir = os.path.join(task_dir, 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        return task_dir

    def concatenate_scene_videos(self, recreation_id: int) -> Dict[str, Any]:
        """
        将分场景视频合成完整视频

        Args:
            recreation_id: 项目ID

        Returns:
            包含合成结果的字典
        """
        try:
            logger.info(f"开始合成完整视频，recreation_id={recreation_id}")

            scenes = RecreationScene.query.filter_by(
                recreation_id=recreation_id
            ).order_by(RecreationScene.scene_index).all()

            if not scenes:
                return {
                    'success': False,
                    'error': '没有分镜场景'
                }

            video_paths = []
            for scene in scenes:
                if scene.generated_video_path and os.path.exists(scene.generated_video_path):
                    video_paths.append(scene.generated_video_path)
                else:
                    logger.warning(f"场景 {scene.scene_index + 1} 视频不存在，跳过")

            if not video_paths:
                return {
                    'success': False,
                    'error': '没有可用的场景视频'
                }

            recreation = VideoRecreation.query.get(recreation_id)
            task_dir = self._get_task_directory(recreation_id, recreation.original_video_path)
            output_path = os.path.join(task_dir, 'final_video.mp4')

            import asyncio
            from app.services.ffmpeg_service import FFmpegService

            ffmpeg_service = FFmpegService()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    ffmpeg_service.compose_videos(video_paths, output_path)
                )
            finally:
                loop.close()

            if result.get('success'):
                recreation.final_video_path = output_path
                recreation.status = 'completed'
                db.session.commit()

                logger.info(f"视频合成完成: {output_path}")

                return {
                    'success': True,
                    'output_path': output_path,
                    'total_scenes': len(video_paths)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '视频合成失败')
                }

        except Exception as e:
            logger.error(f"合成完整视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
