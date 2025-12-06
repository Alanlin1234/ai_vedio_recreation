"""
ComfyUI配置和调用管理器
统一管理所有Agent对ComfyUI的配置和调用
"""
from typing import Dict, Any, Optional
import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)


class ComfyUIManager:
    """ComfyUI配置和调用管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.comfyui_url = self.config.get('comfyui_url', 'http://127.0.0.1:8188')
        self.default_timeout = self.config.get('timeout', 300)  # 默认超时时间300秒
        self.default_batch_size = self.config.get('batch_size', 1)
        
        # 工作流配置
        self.workflow_config = {
            'flux': {
                'width': self.config.get('flux_width', 1920),  # 使用1080p宽度
                'height': self.config.get('flux_height', 1080),  # 使用1080p高度
                'steps': self.config.get('flux_steps', 25),  # 减少采样步数以加快生成速度
                'cfg_scale': self.config.get('flux_cfg_scale', 4.0),  # 降低CFG比例，减少计算量
                'negative_prompt': self.config.get('flux_negative_prompt', 'low quality, blurry, distorted, inconsistent style, watermark, text'),
                'style_prefix': self.config.get('flux_style_prefix', 'cinematic, high quality, detailed, professional lighting'),
                'style_lora': self.config.get('flux_style_lora', None),
                'style_lora_strength': self.config.get('flux_style_lora_strength', 0.8),
                'use_controlnet': self.config.get('flux_use_controlnet', False)
            },
            'standard': {
                'width': self.config.get('standard_width', 1024),
                'height': self.config.get('standard_height', 576),
                'steps': self.config.get('standard_steps', 30),
                'cfg_scale': self.config.get('standard_cfg_scale', 7.5),
                'negative_prompt': self.config.get('standard_negative_prompt', 'low quality, blurry, distorted')
            },
            'wan21': {
                'width': self.config.get('wan21_width', 512),
                'height': self.config.get('wan21_height', 512),
                'steps': self.config.get('wan21_steps', 20),
                'cfg_scale': self.config.get('wan21_cfg_scale', 7.0),
                'negative_prompt': self.config.get('wan21_negative_prompt', 'low quality, blurry, distorted'),
                'fps': self.config.get('wan21_fps', 24),
                'video_length': self.config.get('wan21_video_length', 8),
                'lossless': self.config.get('wan21_lossless', False),
                'quality': self.config.get('wan21_quality', 80)
            }
        }
    
    async def build_workflow(self, shot: Dict, workflow_type: str = 'flux') -> Dict[str, Any]:
        """
        构建ComfyUI工作流
        
        Args:
            shot: 镜头信息
            workflow_type: 工作流类型 ('flux' 或 'standard')
            
        Returns:
            ComfyUI工作流字典
        """
        try:
            # 获取镜头参数
            prompt = shot.get('prompt', '')
            shot_id = shot.get('shot_id', 0)
            
            # 获取工作流配置
            config = self.workflow_config.get(workflow_type, self.workflow_config['flux'])
            
            # 根据工作流类型选择配置函数
            if workflow_type == 'flux':
                # 使用简单的 Flux 工作流（正确的API格式）
                from simple_flux_workflow import get_simple_flux_workflow
                
                # 构建风格一致的提示词
                scene_description = shot.get('scene_description', '')
                style_keywords = shot.get('style_keywords', None)
                
                # 添加风格前缀
                style_prefix = config['style_prefix']
                if style_prefix:
                    prompt = f"{style_prefix}, {prompt}"
                
                comfyui_workflow = get_simple_flux_workflow(
                    positive_prompt=prompt,
                    shot_id=shot_id,
                    negative_prompt=config['negative_prompt'],
                    width=config['width'],
                    height=config['height'],
                    steps=config['steps'],
                    cfg_scale=config['cfg_scale']
                )
                
                logger.info(f"已构建 Flux 工作流 (镜头 {shot_id})")
                
            elif workflow_type == 'wan21':
                # 使用 Wan2.1 视频生成工作流
                from comfyui_wan21_workflow import get_wan21_workflow
                
                comfyui_workflow = get_wan21_workflow(
                    positive_prompt=prompt,
                    video_id=shot_id,
                    width=config['width'],
                    height=config['height'],
                    steps=config['steps'],
                    cfg_scale=config['cfg_scale'],
                    negative_prompt=config['negative_prompt'],
                    seed=-1,  # 随机种子
                    fps=config['fps']
                )
                
                logger.info(f"已构建 Wan2.1 视频生成工作流 (视频 {shot_id})")
                
            else:
                # 使用标准工作流
                from comfyui_workflow_template import get_workflow_with_params
                
                comfyui_workflow = get_workflow_with_params(
                    positive_prompt=prompt,
                    shot_id=shot_id,
                    width=config['width'],
                    height=config['height'],
                    steps=config['steps'],
                    cfg_scale=config['cfg_scale'],
                    negative_prompt=config['negative_prompt'],
                    seed=-1  # 随机种子
                )
                
                logger.info(f"已构建标准工作流 (镜头 {shot_id}): {len(comfyui_workflow)} 个节点")
            
            return comfyui_workflow
            
        except ImportError as e:
            logger.error(f"无法导入工作流配置: {str(e)}")
            raise Exception(
                f"ComfyUI 工作流未配置 (类型: {workflow_type})。\n"
                "请确保已正确配置 ComfyUI 工作流文件。"
            )
        except Exception as e:
            logger.error(f"构建工作流失败: {str(e)}")
            raise
    
    async def execute_workflow(self, workflow: Dict[str, Any], timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        执行ComfyUI工作流
        
        Args:
            workflow: ComfyUI工作流字典
            timeout: 超时时间（秒）
            
        Returns:
            执行结果，包含生成的图像URL
        """
        try:
            timeout = timeout or self.default_timeout
            
            # 提交工作流到ComfyUI
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.comfyui_url}/prompt",
                    json={"prompt": workflow},
                    timeout=timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"ComfyUI API 错误 ({response.status}): {error_text}")
                    
                    result = await response.json()
                    prompt_id = result.get('prompt_id')
                    
                    if not prompt_id:
                        raise Exception(f"未获取到 prompt_id: {result}")
                    
                    logger.info(f"ComfyUI 工作流已提交: {prompt_id}")
            
            # 等待生成完成
            image_url = await self._wait_for_completion(prompt_id, timeout)
            
            return {
                'success': True,
                'image_url': image_url,
                'prompt_id': prompt_id
            }
            
        except Exception as e:
            logger.error(f"执行ComfyUI工作流失败: {str(e)}")
            raise
    
    async def _wait_for_completion(self, prompt_id: str, timeout: int) -> str:
        """
        等待ComfyUI工作流执行完成
        
        Args:
            prompt_id: ComfyUI工作流ID
            timeout: 超时时间（秒）
            
        Returns:
            生成的图像URL
        """
        async with aiohttp.ClientSession() as session:
            for i in range(timeout):
                try:
                    async with session.get(
                        f"{self.comfyui_url}/history/{prompt_id}",
                        timeout=10
                    ) as response:
                        if response.status != 200:
                            logger.warning(f"查询历史失败: {response.status}")
                            await asyncio.sleep(1)
                            continue
                        
                        history = await response.json()
                        
                        # 检查任务是否在历史中
                        if prompt_id in history:
                            task_info = history[prompt_id]
                            status = task_info.get('status', {})
                            
                            # 检查是否完成
                            if status.get('completed'):
                                logger.info(f"ComfyUI 工作流执行完成: {prompt_id}")
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
                            logger.info(f"等待 ComfyUI 执行完成... ({i}s)")
                
                except asyncio.TimeoutError:
                    logger.warning(f"查询超时，继续等待...")
                    await asyncio.sleep(1)
                except Exception as e:
                    if i < timeout - 1:  # 不是最后一次尝试
                        logger.warning(f"查询出错: {str(e)}，继续等待...")
                        await asyncio.sleep(1)
                    else:
                        raise
        
        raise TimeoutError(f"ComfyUI 工作流执行超时（{timeout}秒）")
    
    def _extract_image_url(self, outputs: Dict) -> str:
        """
        从ComfyUI输出中提取图像URL
        
        Args:
            outputs: ComfyUI工作流输出
            
        Returns:
            生成的图像URL
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
                        
                        logger.info(f"提取到图像 URL: {url}")
                        return url
        
        # 如果没有找到，记录所有输出节点以便调试
        logger.error(f"无法从输出中提取图像。可用的输出节点: {list(outputs.keys())}")
        
        raise ValueError(f"无法从 ComfyUI 输出中提取图像。输出节点: {list(outputs.keys())}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            当前配置字典
        """
        return {
            'comfyui_url': self.comfyui_url,
            'default_timeout': self.default_timeout,
            'default_batch_size': self.default_batch_size,
            'workflow_config': self.workflow_config
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        
        # 更新基础配置
        if 'comfyui_url' in new_config:
            self.comfyui_url = new_config['comfyui_url']
        if 'timeout' in new_config:
            self.default_timeout = new_config['timeout']
        if 'batch_size' in new_config:
            self.default_batch_size = new_config['batch_size']
        
        # 更新工作流配置
        for workflow_type in ['flux', 'standard', 'wan21']:
            if workflow_type in new_config:
                workflow_updates = new_config[workflow_type]
                for key, value in workflow_updates.items():
                    if workflow_type in self.workflow_config:
                        self.workflow_config[workflow_type][key] = value


# 创建全局ComfyUIManager实例
comfyui_manager = None


def get_comfyui_manager(config: Dict[str, Any] = None) -> ComfyUIManager:
    """
    获取全局ComfyUIManager实例
    
    Args:
        config: 配置字典
        
    Returns:
        ComfyUIManager实例
    """
    global comfyui_manager
    if comfyui_manager is None:
        comfyui_manager = ComfyUIManager(config)
    elif config:
        comfyui_manager.update_config(config)
    return comfyui_manager
