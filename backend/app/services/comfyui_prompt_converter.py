# ComfyUI提示词转换器服务

import json
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ComfyUIPromptConverter:
    
    def __init__(self):
        logger.info("ComfyUI提示词转换器初始化")
    
    def convert_to_comfyui_prompt(self, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"开始转换场景 {scene_data.get('scene_id', 'unknown')} 到ComfyUI格式")
            
            # 从场景数据中提取关键信息
            scene_id = scene_data.get('scene_id', 1)
            scene_description = scene_data.get('description', '')
            video_prompt = scene_data.get('video_prompt', '')
            style_elements = scene_data.get('style_elements', {})
            technical_params = scene_data.get('technical_params', {})
            
            # 构建ComfyUI提示词
            comfyui_prompt = {
                "scene_id": scene_id,
                "description": scene_description,
                "video_prompt": video_prompt,
                "style_elements": style_elements,
                "technical_params": technical_params,
                "comfyui_positive_prompt": self._build_positive_prompt(video_prompt, style_elements),
                "comfyui_negative_prompt": self._build_negative_prompt(),
                "seed": self._generate_seed(scene_id),
                "width": technical_params.get("width", 1024),
                "height": technical_params.get("height", 1024),
                "steps": technical_params.get("steps", 20),
                "cfg": technical_params.get("cfg", 8),
                "sampler_name": technical_params.get("sampler", "euler"),
                "scheduler": technical_params.get("scheduler", "normal")
            }
            
            logger.info(f"场景 {scene_id} 转换完成")
            return comfyui_prompt
            
        except Exception as e:
            logger.error(f"转换场景失败: {str(e)}")
            raise
    
    def convert_scenes_to_comfyui(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted_prompts = []
        
        for scene in scenes:
            try:
                converted_prompt = self.convert_to_comfyui_prompt(scene)
                converted_prompts.append(converted_prompt)
            except Exception as e:
                logger.error(f"转换场景 {scene.get('scene_id', 'unknown')} 失败: {str(e)}")
                # 跳过转换失败的场景，继续处理其他场景
                continue
        
        logger.info(f"成功转换 {len(converted_prompts)}/{len(scenes)} 个场景")
        return converted_prompts
    
    def _build_positive_prompt(self, video_prompt: str, style_elements: Dict[str, Any]) -> str:
        # 基础提示词
        positive_prompt = video_prompt
        
        # 添加风格元素
        characters = style_elements.get("characters", "")
        environment = style_elements.get("environment", "")
        visual_style = style_elements.get("visual_style", "")
        camera_movement = style_elements.get("camera_movement", "")
        
        # 如果有额外的风格元素，添加到提示词中
        if characters:
            positive_prompt += f", {characters}"
        if environment:
            positive_prompt += f", {environment}"
        if visual_style:
            positive_prompt += f", {visual_style}"
        if camera_movement:
            positive_prompt += f", {camera_movement}"
        
        # 添加高质量关键词
        positive_prompt += ", best quality, masterpiece, ultra high res, detailed, beautiful lighting, cinematic, professional"
        
        return positive_prompt.strip()
    
    def _build_negative_prompt(self) -> str:
        return (
            "worst quality, low quality, blurry, pixelated, deformed, ugly, bad anatomy, "
            "bad proportions, extra limbs, missing limbs, floating limbs, disconnected limbs, "
            "mutation, mutated, disfigured, poorly drawn face, bad hands, extra fingers, "
            "missing fingers, extra arms, missing arms, extra legs, missing legs, text, watermark"
        )
    
    def _generate_seed(self, scene_id: int) -> int:
        # 使用场景ID生成一个相对唯一的种子
        import time
        return (scene_id * 1000000) + int(time.time() % 1000000)
    
    def validate_comfyui_prompt(self, prompt: Dict[str, Any]) -> bool:
        required_fields = ["video_prompt", "comfyui_positive_prompt", "comfyui_negative_prompt"]
        
        for field in required_fields:
            if field not in prompt or not prompt[field]:
                logger.error(f"ComfyUI提示词缺少必填字段: {field}")
                return False
        
        return True
    
    def format_for_keyframe_generation(self, prompt: Dict[str, Any], num_keyframes: int = 5) -> Dict[str, Any]:
        keyframe_prompt = prompt.copy()
        keyframe_prompt["num_keyframes"] = num_keyframes
        keyframe_prompt["task_type"] = "keyframe_generation"
        
        return keyframe_prompt
    
    def format_for_video_generation(self, prompt: Dict[str, Any], keyframe_urls: List[str]) -> Dict[str, Any]:
        video_prompt = prompt.copy()
        video_prompt["keyframe_urls"] = keyframe_urls
        video_prompt["task_type"] = "video_generation"
        
        return video_prompt

