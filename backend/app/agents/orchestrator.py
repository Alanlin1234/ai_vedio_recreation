#视频创作编排器 - 从端到端的流程控制

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from .hotspot_agent import HotspotAgent
from .script_agent import ScriptAgent
from .storyboard_agent import StoryboardAgent
from .image_generation_agent import ImageGenerationAgent
from .consistency_agent import ConsistencyAgent
from .video_synthesis_agent import VideoSynthesisAgent
from .regeneration_agent import RegenerationAgent
from .tracking_manager import TrackingManager
import logging

logger = logging.getLogger(__name__)


class VideoCreationOrchestrator:
    """端到端视频创作流程编排器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 初始化追踪管理器
        tracking_file = self.config.get("tracking_file", "agent_tracking.json")
        self.tracking_manager = TrackingManager(tracking_file)
        
        # 初始化所有Agent
        self.hotspot_agent = HotspotAgent(config)
        self.script_agent = ScriptAgent(config)
        self.storyboard_agent = StoryboardAgent(config)
        self.image_generation_agent = ImageGenerationAgent(config)
        self.consistency_agent = ConsistencyAgent(config)
        self.regeneration_agent = RegenerationAgent(config)
        self.video_synthesis_agent = VideoSynthesisAgent(config)
        
        self.logger = logging.getLogger("VideoCreationOrchestrator")
        
    async def create_video(self, input_params: Dict[str, Any]) -> Dict[str, Any]:
        #开始运行完整的流程
        session_id = None
        result = {
            'success': True,
            'stages': {},
            'errors': [],
            'session_id': None
        }
        
        try:
            # 开始追踪会话
            session_id = self.tracking_manager.start_session(input_params)
            result['session_id'] = session_id
            
            self.logger.info("=" * 50)
            self.logger.info("开始视频创作流程")
            self.logger.info("=" * 50)
            
            # 阶段1: 获取抖音热点
            self.logger.info("\n[阶段1] 获取抖音热点：")
            hotspot_result = await self._execute_with_retry(
                agent=self.hotspot_agent,
                stage="hotspot",
                input_data={
                    'keywords': input_params.get('keywords', []),
                    'count': input_params.get('hotspot_count', 10)
                },
                max_retries=2
            )
            
            if not hotspot_result['success']:
                return self._handle_error("hotspot", hotspot_result, result)
            
            result['stages']['hotspot'] = hotspot_result['data']
            selected_hotspot = hotspot_result['data']['selected_hotspot']
            
            # 阶段2: 脚本拆解
            self.logger.info("\n[阶段2] 脚本拆解")
            script_result = await self._execute_with_retry(
                agent=self.script_agent,
                stage="script",
                input_data={
                    'hotspot': selected_hotspot,
                    'style': input_params.get('style', 'commentary'),
                    'duration': input_params.get('duration', 60)
                },
                max_retries=2
            )
            
            if not script_result['success']:
                return self._handle_error("script", script_result, result)
            
            result['stages']['script'] = script_result['data']
            scenes = script_result['data']['scenes']
            
            # 阶段3: 分镜规划
            self.logger.info("\n[阶段3] 分镜/镜头规划")
            storyboard_result = await self._execute_with_retry(
                agent=self.storyboard_agent,
                stage="storyboard",
                input_data={
                    'scenes': scenes,
                    'style': input_params.get('style', 'cinematic')
                },
                max_retries=2
            )
            
            if not storyboard_result['success']:
                return self._handle_error("storyboard", storyboard_result, result)
            
            result['stages']['storyboard'] = storyboard_result['data']
            shots = storyboard_result['data']['shots']
            
            # 阶段4: 关键帧生成 (使用 Flux 模型)
            self.logger.info("\n[阶段4] 关键帧生成 (Flux)")
            keyframe_result = await self._execute_with_retry(
                agent=self.image_generation_agent,
                stage="keyframe_generation",
                input_data={
                    'shots_with_references': shots,
                    'workflow': {
                        **input_params.get('comfyui_workflow', {}),
                        'type': 'flux'
                    },
                    'batch_size': input_params.get('batch_size', 1)
                },
                max_retries=3
            )
            
            if not keyframe_result['success']:
                return self._handle_error("keyframe_generation", keyframe_result, result)
            
            result['stages']['keyframe_generation'] = keyframe_result['data']
            generated_keyframes = keyframe_result['data']['generated_images']
            
            # 阶段5: 图像生成 (使用标准工作流)
            self.logger.info("\n[阶段5] 图像生成 (标准工作流)")
            image_generation_result = await self._execute_with_retry(
                agent=self.image_generation_agent,
                stage="image_generation",
                input_data={
                    'shots_with_references': generated_keyframes,
                    'workflow': {
                        **input_params.get('comfyui_workflow', {}),
                        'type': 'standard'
                    },
                    'batch_size': input_params.get('batch_size', 1)
                },
                max_retries=3
            )
            
            if not image_generation_result['success']:
                return self._handle_error("image_generation", image_generation_result, result)
            
            result['stages']['image_generation'] = image_generation_result['data']
            generated_images = image_generation_result['data']['generated_images']
            
            # 阶段6: 一致性检验
            self.logger.info("\n[阶段6] 图像一致性检验")
            consistency_result = await self._execute_with_retry(
                agent=self.consistency_agent,
                stage="consistency",
                input_data={
                    'generated_images': generated_images,
                    'storyboard': storyboard_result['data']['storyboard']
                },
                max_retries=2
            )
            
            if not consistency_result['success']:
                return self._handle_error("consistency", consistency_result, result)
            
            result['stages']['consistency'] = consistency_result['data']
            passed_images = consistency_result['data']['passed_images']
            failed_images = consistency_result['data']['failed_images']
            
            # 阶段6.5: 重新生成失败的场景（一致性 < 0.85）
            if failed_images and input_params.get('retry_failed', True):
                self.logger.info(f"\n[阶段6.5] 重新生成 {len(failed_images)} 个未通过检验的镜头...")
                self.logger.info(f"一致性阈值: 0.85")
                
                # 按场景分组
                scene_groups = self._group_images_by_scene(generated_images)
                
                regeneration_result = await self._execute_with_retry(
                    agent=self.regeneration_agent,
                    stage="regeneration",
                    input_data={
                        'failed_images': failed_images,
                        'scene_groups': scene_groups,
                        'original_shots': shots,
                        'workflow_config': input_params.get('comfyui_workflow', {}),
                        'image_generation_agent': self.image_generation_agent,  # 使用 ImageGenerationAgent 生成
                        'consistency_agent': self.consistency_agent
                    },
                    max_retries=2
                )
                
                if regeneration_result['success']:
                    result['stages']['regeneration'] = regeneration_result['data']
                    
                    # 合并重新生成的通过图像
                    regenerated_passed = regeneration_result['data']['final_passed_images']
                    passed_images.extend(regenerated_passed)
                    
                    retry_stats = regeneration_result['data']['retry_stats']
                    self.logger.info(
                        f"重新生成完成: {retry_stats['successful_regenerations']}/"
                        f"{retry_stats['total_scenes']} 场景成功, "
                        f"总重试次数: {retry_stats['total_retries']}"
                    )
                    
                    # 记录失败的场景
                    still_failed = regeneration_result['data']['failed_scenes']
                    if still_failed:
                        self.logger.warning(
                            f": {len(still_failed)} 个场景在多次重试后仍未达到一致性要求"
                        )
                        result['stages']['regeneration']['warning'] = (
                            f"{len(still_failed)} 个场景未达到一致性要求 (0.85)"
                        )
                else:
                    self.logger.error(f"重新生成失败: {regeneration_result.get('error')}")
                    result['errors'].append({
                        'stage': 'regeneration',
                        'error': regeneration_result.get('error')
                    })
            
            # 阶段7: 视频合成
            self.logger.info("\n[阶段7] 视频合成...")
            synthesis_result = await self._execute_with_retry(
                agent=self.video_synthesis_agent,
                stage="synthesis",
                input_data={
                    'passed_images': passed_images,
                    'narration_audio': input_params.get('narration_audio'),
                    'background_music': input_params.get('background_music'),
                    'output_filename': input_params.get('output_filename', 'final_video.mp4')
                },
                max_retries=2
            )
            
            if not synthesis_result['success']:
                return self._handle_error("synthesis", synthesis_result, result)
            
            result['stages']['synthesis'] = synthesis_result['data']
            
            # 完成
            self.logger.info("\n" + "=" * 50)
            self.logger.info("视频创作流程完成!")
            self.logger.info(f"输出路径: {synthesis_result['data']['video_path']}")
            self.logger.info("=" * 50)
            
            result['final_video'] = synthesis_result['data']['video_path']
            
            # 结束追踪会话
            self.tracking_manager.end_session(result)
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"流程执行失败: {str(e)}"
            error_details = traceback.format_exc()
            self.logger.error(f"{error_msg}\n{error_details}")
            
            # 记录错误并结束追踪会话
            result['success'] = False
            result['error'] = error_msg
            result['error_details'] = error_details
            
            if session_id:
                self.tracking_manager.record_error({'exception': error_msg, 'traceback': error_details})
                self.tracking_manager.end_session(result)
            
            return result
    
    async def _execute_with_retry(self, agent, stage: str, input_data: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        带重试机制的Agent执行方法
        
        Args:
            agent: Agent实例
            stage: 阶段名称
            input_data: 输入数据
            max_retries: 最大重试次数
            
        Returns:
            Agent执行结果
        """
        retry_count = 0
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    self.logger.warning(f"[{stage}] 第 {retry_count} 次重试...")
                    # 重试前等待一段时间，避免立即重试
                    import asyncio
                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                
                result = await agent.execute(input_data)
                if result['success'] or retry_count == max_retries:
                    return result
                
                self.logger.warning(f"[{stage}] 执行失败，准备重试: {result.get('error')}")
                retry_count += 1
                
            except Exception as e:
                import traceback
                self.logger.error(f"[{stage}] 执行异常，准备重试: {str(e)}")
                self.logger.debug(f"异常详情: {traceback.format_exc()}")
                retry_count += 1
                if retry_count > max_retries:
                    return {
                        'success': False,
                        'error': f"执行失败，已达到最大重试次数: {str(e)}",
                        'exception': str(e)
                    }
        
        return {
            'success': False,
            'error': f"执行失败，已达到最大重试次数 ({max_retries})",
            'stage': stage
        }
    
    def _handle_error(self, stage: str, error_result: Dict, result: Dict) -> Dict:
        """处理阶段错误"""
        self.logger.error(f"阶段 [{stage}] 失败: {error_result.get('error')}")
        result['success'] = False
        result['failed_stage'] = stage
        result['error'] = error_result.get('error')
        return result
    
    def _group_images_by_scene(self, images: list) -> dict:
        #按场景分组图像
        scene_groups = {}
        for img in images:
            scene_id = img.get('scene_id', 0)
            if scene_id not in scene_groups:
                scene_groups[scene_id] = []
            scene_groups[scene_id].append(img)
        return scene_groups
    
    async def get_stage_status(self) -> Dict[str, Any]:
        #各阶段情况
        return {
            'agents': [
                {'name': 'HotspotAgent', 'status': 'ready'},
                {'name': 'ScriptAgent', 'status': 'ready'},
                {'name': 'StoryboardAgent', 'status': 'ready'},
                {'name': 'ImageGenerationAgent', 'status': 'ready'},
                {'name': 'ConsistencyAgent', 'status': 'ready'},
                {'name': 'RegenerationAgent', 'status': 'ready'},
                {'name': 'VideoSynthesisAgent', 'status': 'ready'}
            ]
        }
