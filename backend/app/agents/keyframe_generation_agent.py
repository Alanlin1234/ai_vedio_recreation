"""
关键帧生成 Agent - 使用 ComfyUI Flux 模型

直接使用 Flux 模型生成关键帧图片，不再从图库中选取参考图
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent
import aiohttp
import asyncio


class KeyframeGenerationAgent(BaseAgent):
    """使用 ComfyUI Flux 模型生成关键帧图片"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("KeyframeGenerationAgent", config)
        self.comfyui_url = config.get('comfyui_url', 'http://127.0.0.1:8188') if config else 'http://127.0.0.1:8188'
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用 Flux 模型生成关键帧图片
        
        Args:
            input_data: {
                'shots': List[Dict] - 镜头列表
                'workflow_config': Optional[Dict] - Flux 工作流配置
                'batch_size': Optional[int] - 批处理大小
            }
            
        Returns:
            {
                'generated_keyframes': List[Dict] - 生成的关键帧列表
                'total_generated': int - 生成的图片总数
            }
        """
        try:
            if not self.validate_input(input_data, ['shots']):
                return self.create_result(False, error="缺少镜头数据")
            
            self.log_execution("start", "开始使用 Flux 生成关键帧")
            
            shots = input_data['shots']
            workflow_config = input_data.get('workflow_config', {})
            batch_size = input_data.get('batch_size', 1)
            
            # 批量生成关键帧
            generated_keyframes = []
            for i in range(0, len(shots), batch_size):
                batch = shots[i:i + batch_size]
                batch_results = await self._generate_keyframes_batch(batch, workflow_config)
                generated_keyframes.extend(batch_results)
            
            self.log_execution("complete", f"生成了 {len(generated_keyframes)} 个关键帧")
            
            return self.create_result(True, {
                'generated_keyframes': generated_keyframes,
                'total_generated': len(generated_keyframes)
            })
            
        except Exception as e:
            self.logger.error(f"关键帧生成失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _generate_keyframes_batch(self, shots: List[Dict], workflow_config: Dict) -> List[Dict]:
        """批量生成关键帧"""
        results = []
        
        for shot in shots:
            try:
                keyframe = await self._generate_single_keyframe(shot, workflow_config)
                results.append(keyframe)
            except Exception as e:
                self.logger.error(f"生成镜头 {shot.get('shot_id')} 关键帧失败: {str(e)}")
                results.append({
                    'shot_id': shot.get('shot_id'),
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    async def _generate_single_keyframe(self, shot: Dict, workflow_config: Dict) -> Dict[str, Any]:
        """
        使用 Flux 模型生成单个关键帧
        
        Args:
            shot: 镜头信息
            workflow_config: Flux 工作流配置
            
        Returns:
            生成的关键帧信息
        """
        shot_id = shot.get('shot_id', 0)
        prompt = shot.get('prompt', '')
        visual_desc = shot.get('visual_description', '')
        style = shot.get('style', '')
        scene_description = shot.get('scene_description', '')
        
        # 如果没有提示词，从视觉描述构建
        if not prompt:
            prompt = self._build_prompt_from_shot(shot, workflow_config)
        
        try:
            # 1. 构建 Flux 工作流
            flux_workflow = self._build_flux_workflow(shot, prompt, workflow_config)
            
            # 2. 提交到 ComfyUI
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.comfyui_url}/prompt",
                    json={"prompt": flux_workflow}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ComfyUI API 错误 ({response.status}): {error_text}")
                    
                    result = await response.json()
                    prompt_id = result.get('prompt_id')
                    
                    if not prompt_id:
                        raise Exception(f"未获取到 prompt_id: {result}")
                    
                    self.logger.info(f"Flux 关键帧生成任务已提交: {prompt_id} (镜头 {shot_id})")
            
            # 3. 等待生成完成
            image_url = await self._wait_for_generation(prompt_id)
            
            # 4. 返回关键帧信息
            return {
                'shot_id': shot_id,
                'success': True,
                'keyframe_url': image_url,
                'prompt': prompt,
                'prompt_id': prompt_id,
                'generation_method': 'flux',
                'style': style,
                'scene_description': scene_description
            }
            
        except Exception as e:
            self.logger.error(f"生成镜头 {shot_id} 关键帧失败: {str(e)}")
            return {
                'shot_id': shot_id,
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    def _build_prompt_from_shot(self, shot: Dict, workflow_config: Dict) -> str:
        """
        从镜头信息构建 Flux 提示词
        
        Args:
            shot: 镜头信息
            workflow_config: 工作流配置
            
        Returns:
            优化后的提示词
        """
        visual_desc = shot.get('visual_description', '')
        style = shot.get('style', '')
        shot_type = shot.get('shot_type', '')
        scene_description = shot.get('scene_description', '')
        
        # 获取风格前缀
        style_prefix = workflow_config.get('style_prefix', 'cinematic, high quality, detailed')
        
        # 构建提示词
        prompt_parts = []
        
        # 添加风格前缀
        if style_prefix:
            prompt_parts.append(style_prefix)
        
        # 添加场景描述
        if scene_description:
            prompt_parts.append(scene_description)
        
        # 添加视觉描述
        if visual_desc:
            prompt_parts.append(visual_desc)
        
        # 添加镜头类型描述
        shot_type_desc = self._get_shot_type_description(shot_type)
        if shot_type_desc:
            prompt_parts.append(shot_type_desc)
        
        # 添加风格关键词
        if style:
            prompt_parts.append(f"{style} style")
        
        # 组合提示词
        prompt = ', '.join(prompt_parts)
        
        return prompt
    
    def _get_shot_type_description(self, shot_type: str) -> str:
        """获取镜头类型的描述"""
        shot_type_map = {
            'wide_shot': 'wide angle shot, establishing shot',
            'medium_shot': 'medium shot, waist up',
            'close_up': 'close-up shot, detailed view',
            'extreme_close_up': 'extreme close-up, macro detail',
            'aerial_view': 'aerial view, birds eye perspective',
            'low_angle': 'low angle shot, looking up',
            'high_angle': 'high angle shot, looking down'
        }
        return shot_type_map.get(shot_type, '')
    
    def _build_flux_workflow(self, shot: Dict, prompt: str, workflow_config: Dict) -> Dict[str, Any]:
        """
        构建 Flux 工作流
        
        Args:
            shot: 镜头信息
            prompt: 提示词
            workflow_config: 工作流配置
            
        Returns:
            ComfyUI 工作流字典
        """
        try:
            from comfyui_flux_workflow import get_flux_workflow
            
            shot_id = shot.get('shot_id', 0)
            
            # 获取配置参数
            width = workflow_config.get('width', 1024)
            height = workflow_config.get('height', 576)
            steps = workflow_config.get('steps', 25)
            cfg_scale = workflow_config.get('cfg_scale', 3.5)
            negative_prompt = workflow_config.get('negative_prompt', 'low quality, blurry, distorted')
            seed = workflow_config.get('seed', -1)
            style_lora = workflow_config.get('style_lora', None)
            
            # 生成 Flux 工作流
            flux_workflow = get_flux_workflow(
                positive_prompt=prompt,
                shot_id=shot_id,
                width=width,
                height=height,
                steps=steps,
                cfg_scale=cfg_scale,
                negative_prompt=negative_prompt,
                seed=seed,
                style_lora=style_lora,
                style_lora_strength=workflow_config.get('style_lora_strength', 0.8)
            )
            
            self.logger.info(f"已构建 Flux 工作流 (镜头 {shot_id})")
            return flux_workflow
            
        except ImportError as e:
            self.logger.error(f"无法导入 Flux 工作流配置: {str(e)}")
            raise Exception(
                "Flux 工作流未配置。"
                "请在 backend/comfyui_flux_workflow.py 中配置你的工作流。"
                "参考文档: backend/flux_video_generation_guide.md"
            )
    
    async def _wait_for_generation(self, prompt_id: str, timeout: int = 300) -> str:
        """
        等待 Flux 生成完成
        
        Args:
            prompt_id: ComfyUI 任务 ID
            timeout: 超时时间（秒）
            
        Returns:
            生成的图像 URL
        """
        async with aiohttp.ClientSession() as session:
            for i in range(timeout):
                try:
                    async with session.get(
                        f"{self.comfyui_url}/history/{prompt_id}"
                    ) as response:
                        if response.status != 200:
                            self.logger.warning(f"查询历史失败: {response.status}")
                            await asyncio.sleep(1)
                            continue
                        
                        history = await response.json()
                        
                        # 检查任务是否在历史中
                        if prompt_id in history:
                            task_info = history[prompt_id]
                            status = task_info.get('status', {})
                            
                            # 检查是否完成
                            if status.get('completed'):
                                self.logger.info(f"Flux 关键帧生成完成: {prompt_id}")
                                outputs = task_info.get('outputs', {})
                                return self._extract_image_url(outputs)
                            
                            # 检查是否有错误
                            if 'error' in status:
                                error_msg = status.get('error', 'Unknown error')
                                raise Exception(f"ComfyUI 执行错误: {error_msg}")
                        
                        # 每秒检查一次
                        await asyncio.sleep(1)
                        
                        # 每 10 秒输出一次进度
                        if i > 0 and i % 10 == 0:
                            self.logger.info(f"等待 Flux 生成完成... ({i}s)")
                
                except asyncio.TimeoutError:
                    self.logger.warning(f"查询超时，继续等待...")
                    await asyncio.sleep(1)
                except Exception as e:
                    if i < timeout - 1:
                        self.logger.warning(f"查询出错: {str(e)}，继续等待...")
                        await asyncio.sleep(1)
                    else:
                        raise
        
        raise TimeoutError(f"Flux 生成超时（{timeout}秒）")
    
    def _extract_image_url(self, outputs: Dict) -> str:
        """
        从 ComfyUI 输出中提取图像 URL
        
        Args:
            outputs: ComfyUI 任务的输出字典
            
        Returns:
            图像的访问 URL
        """
        # 尝试常见的输出节点 ID
        possible_node_ids = ["9", "10", "11", "save_image", "output"]
        
        for node_id in possible_node_ids:
            if node_id in outputs:
                node_output = outputs[node_id]
                images = node_output.get("images", [])
                
                if images:
                    # 获取第一张图像的信息
                    image_info = images[0]
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    image_type = image_info.get("type", "output")
                    
                    if filename:
                        # 构建图像 URL
                        url = f"{self.comfyui_url}/view?filename={filename}"
                        if subfolder:
                            url += f"&subfolder={subfolder}"
                        url += f"&type={image_type}"
                        
                        self.logger.info(f"提取到关键帧 URL: {url}")
                        return url
        
        # 如果没有找到，记录所有输出节点以便调试
        self.logger.error(f"无法从输出中提取图像。可用的输出节点: {list(outputs.keys())}")
        
        raise ValueError(f"无法从 ComfyUI 输出中提取图像。输出节点: {list(outputs.keys())}")
