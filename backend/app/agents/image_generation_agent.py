
#图像生成Agent - ComfyUI接口

from typing import Dict, Any, List
from .base_agent import BaseAgent
import sys
import os

# 添加项目根目录到路径，以便导入配置
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# 导入ComfyUI管理器
from app.utils.comfyui_manager import get_comfyui_manager


class ImageGenerationAgent(BaseAgent):
    """负责调用ComfyUI生成图像"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ImageGenerationAgent", config)
        # 初始化ComfyUI管理器
        self.comfyui_manager = get_comfyui_manager(config)
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            if not self.validate_input(input_data, ['shots_with_references']):
                return self.create_result(False, error="缺少镜头数据")
            
            self.log_execution("start", "开始图像生成")
            
            shots = input_data['shots_with_references']
            workflow = input_data.get('workflow', {})
            batch_size = input_data.get('batch_size', 1)
            
            # 批量生成图像
            generated_images = []
            for i in range(0, len(shots), batch_size):
                batch = shots[i:i + batch_size]
                batch_results = await self._generate_batch(batch, workflow)
                generated_images.extend(batch_results)
            
            self.log_execution("complete", f"生成了{len(generated_images)}张图像")
            
            return self.create_result(True, {
                'generated_images': generated_images,
                'total_images': len(generated_images)
            })
            
        except Exception as e:
            self.logger.error(f"图像生成失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _generate_batch(self, shots: List[Dict], workflow: Dict) -> List[Dict[str, Any]]:
        """批量生成图像"""
        results = []
        
        for shot in shots:
            try:
                image_data = await self._generate_single_image(shot, workflow)
                results.append(image_data)
            except Exception as e:
                self.logger.error(f"生成镜头{shot['shot_id']}图像失败: {str(e)}")
                results.append({
                    'shot_id': shot['shot_id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    async def _generate_single_image(self, shot: Dict, workflow: Dict) -> Dict[str, Any]:
        
        #生成单张图像 - 使用ComfyUI管理器
        
        prompt = shot.get('prompt', '')
        references = shot.get('references', [])
        
        try:
            # 添加mock模式支持，用于测试完整流程
            use_mock = os.environ.get('USE_MOCK_IMAGE_GENERATION', 'false').lower() == 'true'
            
            if use_mock:
                # 模拟图像生成成功，跳过实际的ComfyUI调用
                self.logger.info(f"[Mock模式] 模拟生成镜头 {shot['shot_id']} 图像")
                return {
                    'shot_id': shot['shot_id'],
                    'success': True,
                    'image_url': f"mock_image_{shot['shot_id']}.png",
                    'prompt': prompt,
                    'prompt_id': f"mock_prompt_{shot['shot_id']}",
                    'references_used': [ref['reference_id'] for ref in references] if references else []
                }
            else:
                # 1. 构建ComfyUI工作流请求
                comfyui_request = await self._build_comfyui_workflow(shot, workflow)
                
                # 2. 使用ComfyUI管理器执行工作流
                result = await self.comfyui_manager.execute_workflow(comfyui_request)
                
                # 3. 返回成功结果
                return {
                    'shot_id': shot['shot_id'],
                    'success': True,
                    'image_url': result['image_url'],
                    'prompt': prompt,
                    'prompt_id': result['prompt_id'],
                    'references_used': [ref['reference_id'] for ref in references] if references else []
                }
            
        except Exception as e:
            self.logger.error(f"生成镜头 {shot['shot_id']} 图像失败: {str(e)}")
            return {
                'shot_id': shot['shot_id'],
                'success': False,
                'error': str(e),
                'prompt': prompt
            }
    
    async def _build_comfyui_workflow(self, shot: Dict, workflow: Dict) -> Dict[str, Any]:
        """
        构建ComfyUI工作流请求
        
        支持的工作流：
        - Flux 工作流（用来生成关键帧）
        - 标准 SD/SDXL 工作流（根据参考图生成分镜视频）
        """
        try:
            # 从 workflow 参数中获取配置
            workflow_type = workflow.get('type', 'flux')  # 默认使用 Flux
            
            # 使用ComfyUI管理器构建工作流
            comfyui_workflow = await self.comfyui_manager.build_workflow(shot, workflow_type)
            
            return comfyui_workflow
            
        except Exception as e:
            self.logger.error(f"构建工作流失败: {str(e)}")
            raise
    
    async def _wait_for_completion(self, prompt_id: str, timeout: int = 300) -> str:
        #comfyui生成
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
                                self.logger.info(f"任务 {prompt_id} 生成完成")
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
                            self.logger.info(f"等待任务 {prompt_id} 完成... ({i}s)")
                
                except asyncio.TimeoutError:
                    self.logger.warning(f"查询超时，继续等待...")
                    await asyncio.sleep(1)
                except Exception as e:
                    if i < timeout - 1:  # 不是最后一次尝试
                        self.logger.warning(f"查询出错: {str(e)}，继续等待...")
                        await asyncio.sleep(1)
                    else:
                        raise
        
        raise TimeoutError(f"任务 {prompt_id} 生成超时（{timeout}秒）")
    
    def _extract_image_url(self, outputs: Dict) -> str:
    
        #从ComfyUI输出中提取图像URL
        #图像的访问 URL
    
        
        
        
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
                        
                        self.logger.info(f"提取到图像 URL: {url}")
                        return url
        
        # 如果没有找到，记录所有输出节点以便调试
        self.logger.error(f"无法从输出中提取图像。可用的输出节点: {list(outputs.keys())}")
        
        # 抛出异常而不是返回空字符串
        raise ValueError(f"无法从 ComfyUI 输出中提取图像。输出节点: {list(outputs.keys())}")
