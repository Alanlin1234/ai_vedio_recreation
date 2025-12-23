# JSON提示词解析服务

import json
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class JSONPromptParser:
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        self.default_config = {
            "default_width": 1024,
            "default_height": 576,
            "default_steps": 25,
            "default_cfg_scale": 7.0,
            "default_sampler": "euler_a",
            "default_scheduler": "normal",
            "default_negative_prompt": "low quality, blurry, distorted, inconsistent style, watermark, text",
            "default_fps": 24
        }
        
        # 更新配置
        if config:
            self.default_config.update(config)
        
        logger.info("JSON提示词解析器初始化完成")
    
    def parse_prompt(self, json_prompt: str, prompt_type: str = "txt2img") -> Dict[str, Any]:
        try:
            logger.info(f"开始解析JSON提示词，类型: {prompt_type}")
            
            # 1. 清理提示词字符串
            cleaned_prompt = json_prompt.strip()
            if not cleaned_prompt:
                logger.error("解析失败: 提示词为空")
                return self._get_default_params(prompt_type)
            
            # 2. 尝试解析JSON字符串
            parsed_json = None
            try:
                parsed_json = json.loads(cleaned_prompt)
                logger.debug(f"解析后的JSON: {parsed_json}")
                
                # 3. 提取基本提示词
                if isinstance(parsed_json, dict):
                    # 直接是JSON对象
                    prompt = parsed_json.get("video_prompt", "") or parsed_json.get("prompt", "")
                else:
                    # 是JSON数组或其他类型
                    prompt = str(parsed_json)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败，将作为纯文本处理: {str(e)}")
                # JSON解析失败，使用原始字符串作为提示词
                prompt = cleaned_prompt
            
            if not prompt:
                logger.error("解析失败: 无法从JSON中提取提示词")
                return self._get_default_params(prompt_type)
            
            # 初始化默认值
            scene_info = {}
            duration = 0
            style_elements = {}
            characters = ""
            environment = ""
            visual_style = ""
            camera_movement = ""
            technical_params = {}
            aspect_ratio = "16:9"
            fps = self.default_config["default_fps"]
            quality = "high"
            width = 0
            height = 0
            steps = self.default_config["default_steps"]
            cfg_scale = self.default_config["default_cfg_scale"]
            sampler_name = self.default_config["default_sampler"]
            scheduler = self.default_config["default_scheduler"]
            negative_prompt = self.default_config["default_negative_prompt"]
            
            # 只有当JSON解析成功时，才提取详细参数
            if parsed_json is not None:
                # 3. 提取场景信息
                if isinstance(parsed_json, dict):
                    scene_info = parsed_json.get("scene_info", {})
                    duration = scene_info.get("duration", 0)
                    
                    # 4. 提取风格元素
                    style_elements = parsed_json.get("style_elements", {})
                    characters = style_elements.get("characters", "")
                    environment = style_elements.get("environment", "")
                    visual_style = style_elements.get("visual_style", "")
                    camera_movement = style_elements.get("camera_movement", "")
                    
                    # 5. 提取技术参数
                    technical_params = parsed_json.get("technical_params", {})
                    aspect_ratio = technical_params.get("aspect_ratio", "16:9")
                    fps = technical_params.get("fps", self.default_config["default_fps"])
                    quality = technical_params.get("quality", "high")
                    
                    # 6. 提取尺寸信息
                    width = technical_params.get("width", 0)
                    height = technical_params.get("height", 0)
                    
                    # 7. 提取采样参数
                    steps = technical_params.get("steps", self.default_config["default_steps"])
                    cfg_scale = technical_params.get("cfg_scale", self.default_config["default_cfg_scale"])
                    sampler_name = technical_params.get("sampler_name", self.default_config["default_sampler"])
                    scheduler = technical_params.get("scheduler", self.default_config["default_scheduler"])
                    
                    # 8. 提取负向提示词
                    negative_prompt = parsed_json.get("negative_prompt", "") or self.default_config["default_negative_prompt"]
            
            # 如果没有指定尺寸，根据默认配置或帧率计算
            if not width or not height:
                width, height = self._calculate_dimensions(aspect_ratio, fps, quality)
            
            # 9. 构建增强提示词（可选）
            enhanced_prompt = self._build_enhanced_prompt(prompt, characters, environment, visual_style, camera_movement)
            
            # 10. 根据提示词类型返回不同的参数
            # 基础参数字典，包含所有解析出的信息
            base_params = {
                "prompt": enhanced_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "scene_info": scene_info,
                "style_elements": style_elements,
                "technical_params": technical_params,
                "objects": parsed_json.get("objects", []) if parsed_json else [],
                "people": parsed_json.get("people", []) if parsed_json else [],
                "actions": parsed_json.get("actions", []) if parsed_json else [],
                "emotions": parsed_json.get("emotions", []) if parsed_json else [],
                "atmosphere": parsed_json.get("atmosphere", "") if parsed_json else ""
            }
            
            if prompt_type == "txt2img":
                return base_params
            elif prompt_type == "img2img":
                base_params["denoising_strength"] = 0.75
                return base_params
            elif prompt_type == "img2video":
                # 视频生成参数
                video_length = int(duration * fps) if duration > 0 else 16
                base_params.update({
                    "length": video_length,
                    "fps": fps
                })
                return base_params
            elif prompt_type == "i2i-preview":
                # wan2.5-i2i-preview 关键帧生成参数
                base_params.update({
                    "reference_images": parsed_json.get("reference_images", []) if parsed_json else [],
                    "style_reference": parsed_json.get("style_reference", "") if parsed_json else "",
                    "denoising_strength": 0.6,  # 关键帧生成推荐值
                    "sampler_name": "dpm_2_a"  # 关键帧生成推荐采样器
                })
                return base_params
            elif prompt_type == "r2v":
                # wan2.6-r2v 视频生成参数
                video_length = int(duration * fps) if duration > 0 else 16
                base_params.update({
                    "length": video_length,
                    "fps": fps,
                    "reference_keyframes": parsed_json.get("reference_keyframes", []) if parsed_json else [],
                    "previous_keyframe": parsed_json.get("previous_keyframe", "") if parsed_json else "",
                    "transition_style": parsed_json.get("transition_style", "smooth") if parsed_json else "smooth"
                })
                return base_params
            else:
                logger.error(f"不支持的提示词类型: {prompt_type}")
                return base_params
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            # 如果JSON解析失败，尝试作为纯文本处理
            return {
                "prompt": json_prompt.strip(),
                **self._get_default_params(prompt_type)
            }
        except Exception as e:
            logger.error(f"解析提示词时发生未知错误: {str(e)}")
            return self._get_default_params(prompt_type)
    
    def batch_parse_prompts(self, json_prompts: List[str], prompt_type: str = "txt2img") -> List[Dict[str, Any]]:
        results = []
        for i, json_prompt in enumerate(json_prompts):
            try:
                parsed_prompt = self.parse_prompt(json_prompt, prompt_type)
                results.append(parsed_prompt)
            except Exception as e:
                logger.error(f"解析第{i+1}个提示词失败: {str(e)}")
                results.append(self._get_default_params(prompt_type))
        return results
    
    def validate_parsed_prompt(self, parsed_prompt: Dict[str, Any]) -> bool:
        required_fields = ["prompt", "width", "height", "steps", "cfg_scale"]
        for field in required_fields:
            if field not in parsed_prompt or not parsed_prompt[field]:
                logger.warning(f"验证失败: 缺少必要参数 {field}")
                return False
        return True
    
    def _get_default_params(self, prompt_type: str) -> Dict[str, Any]:
        default_params = {
            "prompt": "",
            "negative_prompt": self.default_config["default_negative_prompt"],
            "width": self.default_config["default_width"],
            "height": self.default_config["default_height"],
            "steps": self.default_config["default_steps"],
            "cfg_scale": self.default_config["default_cfg_scale"],
            "sampler_name": self.default_config["default_sampler"],
            "scheduler": self.default_config["default_scheduler"],
            "scene_info": {},
            "style_elements": {},
            "technical_params": {},
            "objects": [],
            "people": [],
            "actions": [],
            "emotions": [],
            "atmosphere": ""
        }
        
        if prompt_type == "img2img":
            default_params["denoising_strength"] = 0.75
        elif prompt_type == "img2video":
            default_params.update({
                "length": 16,
                "fps": self.default_config["default_fps"]
            })
        elif prompt_type == "i2i-preview":
            default_params.update({
                "reference_images": [],
                "style_reference": "",
                "denoising_strength": 0.6,
                "sampler_name": "dpm_2_a"
            })
        elif prompt_type == "r2v":
            default_params.update({
                "length": 16,
                "fps": self.default_config["default_fps"],
                "reference_keyframes": [],
                "previous_keyframe": "",
                "transition_style": "smooth"
            })
        
        return default_params
    
    def _calculate_dimensions(self, aspect_ratio: str, fps: int, quality: str) -> tuple:
        try:
            # 解析宽高比
            width_ratio, height_ratio = map(int, aspect_ratio.split(":"))
            
            # 根据质量选择基础宽度
            quality_width = {
                "low": 768,
                "medium": 1024,
                "high": 1280
            }.get(quality, 1024)
            
            # 计算高度
            width = quality_width
            height = int(width * height_ratio / width_ratio)
            
            # 确保高度为偶数
            if height % 2 != 0:
                height += 1
            
            return width, height
        except Exception as e:
            logger.error(f"计算尺寸失败: {str(e)}")
            # 返回默认尺寸
            return self.default_config["default_width"], self.default_config["default_height"]
    
    def _build_enhanced_prompt(self, prompt: str, characters: str, environment: str, 
                              visual_style: str, camera_movement: str) -> str:
        enhanced_prompt = prompt
        
        # 添加角色描述
        if characters:
            enhanced_prompt += f", {characters}"
        
        # 添加环境描述
        if environment:
            enhanced_prompt += f", {environment}"
        
        # 添加视觉风格
        if visual_style:
            enhanced_prompt += f", {visual_style}"
        
        # 添加相机运动
        if camera_movement:
            enhanced_prompt += f", {camera_movement}"
        
        # 添加默认风格前缀
        default_prefix = "cinematic, high quality, detailed, professional lighting"
        if default_prefix not in enhanced_prompt:
            enhanced_prompt = f"{default_prefix}, {enhanced_prompt}"
        
        return enhanced_prompt
    
    def to_comfyui_workflow_params(self, parsed_prompt: Dict[str, Any], workflow_type: str = "flux") -> Dict[str, Any]:
        try:
            logger.info(f"转换为ComfyUI工作流参数，类型: {workflow_type}")
            
            # 基础参数
            comfyui_params = {
                "prompt": parsed_prompt["prompt"],
                "negative_prompt": parsed_prompt.get("negative_prompt", self.default_config["default_negative_prompt"]),
                "width": parsed_prompt["width"],
                "height": parsed_prompt["height"],
                "steps": parsed_prompt["steps"],
                "cfg_scale": parsed_prompt["cfg_scale"],
                "sampler_name": parsed_prompt.get("sampler_name", self.default_config["default_sampler"]),
                "scheduler": parsed_prompt.get("scheduler", self.default_config["default_scheduler"])
            }
            
            # 根据工作流类型添加额外参数
            if workflow_type == "wan21":
                comfyui_params.update({
                    "fps": parsed_prompt.get("fps", 30),
                    "video_length": parsed_prompt.get("length", 16),
                    "lossless": False,
                    "quality": 80
                })
            elif workflow_type == "flux":
                comfyui_params.update({
                    "use_controlnet": parsed_prompt.get("use_controlnet", False),
                    "style_lora": parsed_prompt.get("style_lora", None),
                    "style_lora_strength": parsed_prompt.get("style_lora_strength", 0.8)
                })
            
            return comfyui_params
        except Exception as e:
            logger.error(f"转换为ComfyUI工作流参数失败: {str(e)}")
            return self._get_default_params("txt2img")
    
    def format_for_comfyui_api(self, parsed_prompt: Dict[str, Any], workflow_template: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("格式化提示词为ComfyUI API格式")
            
            # 深拷贝工作流模板
            import copy
            workflow = copy.deepcopy(workflow_template)
            
            # 查找需要替换的节点
            dynamic_nodes = {
                "positive_prompt_node": "6",
                "negative_prompt_node": "7",
                "empty_latent_image_node": "5",
                "ksampler_node": "3"
            }
            
            # 替换正向提示词
            if dynamic_nodes["positive_prompt_node"] in workflow:
                workflow[dynamic_nodes["positive_prompt_node"]]["inputs"]["text"] = parsed_prompt["prompt"]
            
            # 替换负向提示词
            if dynamic_nodes["negative_prompt_node"] in workflow:
                workflow[dynamic_nodes["negative_prompt_node"]]["inputs"]["text"] = parsed_prompt.get("negative_prompt", self.default_config["default_negative_prompt"])
            
            # 替换尺寸
            if dynamic_nodes["empty_latent_image_node"] in workflow:
                workflow[dynamic_nodes["empty_latent_image_node"]]["inputs"]["width"] = parsed_prompt["width"]
                workflow[dynamic_nodes["empty_latent_image_node"]]["inputs"]["height"] = parsed_prompt["height"]
            
            # 替换采样参数
            if dynamic_nodes["ksampler_node"] in workflow:
                workflow[dynamic_nodes["ksampler_node"]]["inputs"]["steps"] = parsed_prompt["steps"]
                workflow[dynamic_nodes["ksampler_node"]]["inputs"]["cfg"] = parsed_prompt["cfg_scale"]
                workflow[dynamic_nodes["ksampler_node"]]["inputs"]["sampler_name"] = parsed_prompt.get("sampler_name", self.default_config["default_sampler"])
                workflow[dynamic_nodes["ksampler_node"]]["inputs"]["scheduler"] = parsed_prompt.get("scheduler", self.default_config["default_scheduler"])
            
            return workflow
        except Exception as e:
            logger.error(f"格式化ComfyUI API请求失败: {str(e)}")
            return workflow_template

