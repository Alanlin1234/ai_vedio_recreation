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
            "default_cfg_scale": 7.0,   #
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
                logger.warning("提示词为空，使用默认提示词")
                result = self._get_default_params(prompt_type)
                result['success'] = True
                result['prompt'] = "A beautiful, high-quality scene"
                return result
            
            # 2. 检测输入格式（JSON或纯文本）
            is_json = self._detect_json_format(cleaned_prompt)
            logger.info(f"检测到格式: {'JSON' if is_json else '纯文本'}")
            
            # 3. 根据格式选择解析策略
            if is_json:
                return self._parse_json_prompt(cleaned_prompt, prompt_type)
            else:
                return self._parse_text_prompt(cleaned_prompt, prompt_type)
        except Exception as e:
            logger.error(f"解析提示词时发生未知错误: {str(e)}")
            result = self._get_default_params(prompt_type)
            result['success'] = True
            result['prompt'] = json_prompt.strip()
            result['error'] = str(e)
            return result
    
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
    
    def _detect_json_format(self, text: str) -> bool:
        """
        检测文本是否为JSON格式
        
        Args:
            text: 输入文本
            
        Returns:
            True if JSON格式, False if 纯文本
        """
        text = text.strip()
        # 检查是否以JSON对象或数组的标记开始和结束
        return (text.startswith('{') and text.endswith('}')) or \
               (text.startswith('[') and text.endswith(']'))
    
    def _parse_json_prompt(self, json_text: str, prompt_type: str) -> Dict[str, Any]:
        """
        解析JSON格式的提示词
        
        Args:
            json_text: JSON格式的文本
            prompt_type: 提示词类型
            
        Returns:
            解析结果字典
        """
        try:
            parsed_json = json.loads(json_text)
            logger.debug(f"成功解析JSON: {parsed_json}")
            
            # 提取基本提示词
            prompt = ""
            if isinstance(parsed_json, dict):
                # 尝试从标准字段提取
                prompt = parsed_json.get("video_prompt", "") or parsed_json.get("prompt", "")
                
                # 如果没有找到标准字段，尝试提取所有文本内容
                if not prompt:
                    for key, value in parsed_json.items():
                        if isinstance(value, str) and value.strip():
                            prompt = value
                            break
            else:
                # 是JSON数组或其他类型，转换为字符串
                prompt = str(parsed_json)
            
            # 如果仍然没有提取到内容，使用原始JSON文本
            if not prompt:
                logger.warning("无法从JSON中提取提示词，使用原始JSON文本")
                prompt = json_text
            
            # 继续原有的详细解析逻辑...
            return self._build_full_result(prompt, parsed_json, prompt_type)
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}，回退到纯文本模式")
            # JSON解析失败，回退到纯文本解析
            return self._parse_text_prompt(json_text, prompt_type)
    
    def _parse_text_prompt(self, text: str, prompt_type: str) -> Dict[str, Any]:
        """
        解析纯文本格式的提示词
        
        Args:
            text: 纯文本提示词
            prompt_type: 提示词类型
            
        Returns:
            解析结果字典
        """
        logger.info(f"使用纯文本模式解析，文本长度: {len(text)}")
        
        # 直接使用文本内容，不进行JSON解析
        prompt = text.strip()
        
        # 构建基本结果
        result = self._get_default_params(prompt_type)
        result['success'] = True
        result['prompt'] = prompt
        result['parsed_json'] = None  # 纯文本模式没有JSON
        
        # 验证内容完整性
        if len(prompt) < len(text) * 0.95:  # 如果丢失超过5%的内容
            logger.warning(f"内容可能被截断: 原始长度={len(text)}, 解析后长度={len(prompt)}")
        
        logger.info(f"纯文本解析完成，提示词长度: {len(prompt)}")
        return result
    
    def _build_full_result(self, prompt: str, parsed_json: Optional[Dict[str, Any]], 
                          prompt_type: str) -> Dict[str, Any]:
        """
        构建完整的解析结果（原有的详细解析逻辑）
        
        Args:
            prompt: 基础提示词
            parsed_json: 解析后的JSON对象
            prompt_type: 提示词类型
            
        Returns:
            完整的解析结果字典
        """
        result = self._get_default_params(prompt_type)
        result['success'] = True
        result['prompt'] = prompt
        result['parsed_json'] = parsed_json
        
        if parsed_json and isinstance(parsed_json, dict):
            if 'scene_info' in parsed_json:
                result['scene_info'] = parsed_json['scene_info']
            if 'style_elements' in parsed_json:
                result['style_elements'] = parsed_json['style_elements']
            if 'technical_params' in parsed_json:
                result['technical_params'] = parsed_json['technical_params']
                tech_params = parsed_json['technical_params']
                if isinstance(tech_params, dict):
                    if 'aspect_ratio' in tech_params:
                        try:
                            width, height = self._calculate_dimensions(
                                tech_params.get('aspect_ratio', '16:9'),
                                tech_params.get('fps', 24),
                                tech_params.get('quality', 'high')
                            )
                            result['width'] = width
                            result['height'] = height
                        except Exception:
                            pass
                    if 'fps' in tech_params:
                        result['fps'] = tech_params['fps']
            
            for field in ['objects', 'people', 'actions', 'emotions', 'atmosphere']:
                if field in parsed_json:
                    result[field] = parsed_json[field]
            
            enhanced_prompt = self._build_enhanced_prompt(prompt, parsed_json)
            result['prompt'] = enhanced_prompt
        
        return result
    
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
    
    def _build_enhanced_prompt(self, prompt: str, parsed_json: Optional[Dict[str, Any]] = None,
                              characters: str = "", environment: str = "", 
                              visual_style: str = "", camera_movement: str = "") -> str:
        """
        构建增强的提示词，包含JSON中的所有重要内容，优先处理关键信息
        
        Args:
            prompt: 基础提示词
            parsed_json: 解析后的JSON对象（可选，如果提供将从中提取更多字段）
            characters: 角色描述
            environment: 环境描述
            visual_style: 视觉风格
            camera_movement: 相机运动
        """
        enhanced_prompt = prompt
        
        # 已处理的字段集合，用于避免重复
        processed_fields = set()
        
        # 如果提供了parsed_json，优先从JSON中提取信息
        if parsed_json and isinstance(parsed_json, dict):
            # 提取所有关键信息，确保95%以上的信息保留
            all_info = {}
            
            # 1. 收集所有关键信息
            # 场景信息
            scene_info = parsed_json.get("scene_info", {})
            if scene_info and isinstance(scene_info, dict):
                all_info.update(scene_info)
            
            # 风格元素
            style_elements = parsed_json.get("style_elements", {})
            if style_elements and isinstance(style_elements, dict):
                all_info.update(style_elements)
            
            # 其他重要字段
            important_fields = ["objects", "people", "actions", "emotions", "atmosphere", 
                              "mood", "time", "location", "rhythm", "speed", "sound_design", 
                              "audio", "music", "dialogue", "camera", "camera_movement"]
            
            for field in important_fields:
                if field in parsed_json:
                    all_info[field] = parsed_json[field]
            
            # 2. 按照优先级构建提示词
            # 优先级顺序：动作、表情 → 镜头类型和角度 → 氛围和情绪 → 时间和地点 → 节奏和速度 → 音效和背景音乐
            priority_groups = {
                "动作表情": ["actions", "emotions", "emotion"],
                "镜头": ["camera", "camera_movement"],
                "氛围情绪": ["atmosphere", "mood"],
                "时间地点": ["time", "location"],
                "节奏速度": ["rhythm", "speed"],
                "音效音乐": ["sound_design", "audio", "music", "dialogue"]
            }
            
            for group_name, fields in priority_groups.items():
                group_info = []
                for field in fields:
                    if field in all_info and all_info[field]:
                        value = all_info[field]
                        if isinstance(value, (list, tuple)):
                            value_text = ", ".join([str(v) for v in value if v])
                        elif isinstance(value, dict):
                            value_text = ", ".join([f"{k}: {v}" for k, v in value.items() if v])
                        else:
                            value_text = str(value).strip()
                        
                        if value_text:
                            group_info.append(value_text)
                            processed_fields.add(field)
                
                if group_info:
                    enhanced_prompt += f", {group_name}: {', '.join(group_info)}"
            
            # 3. 添加其他重要信息
            other_important_fields = ["visual_style", "style", "theme", "scene_description"]
            for field in other_important_fields:
                if field in all_info and all_info[field]:
                    value = all_info[field]
                    if isinstance(value, (list, tuple)):
                        value_text = ", ".join([str(v) for v in value if v])
                    elif isinstance(value, dict):
                        value_text = ", ".join([f"{k}: {v}" for k, v in value.items() if v])
                    else:
                        value_text = str(value).strip()
                    
                    if value_text and value_text not in enhanced_prompt:
                        enhanced_prompt += f", {field}: {value_text}"
                        processed_fields.add(field)
            
            # 4. 添加技术参数（只添加关键技术参数）
            technical_params = parsed_json.get("technical_params", {})
            if technical_params and isinstance(technical_params, dict):
                key_tech_params = ["fps", "resolution", "quality"]
                tech_params_text = []
                for param in key_tech_params:
                    if param in technical_params and technical_params[param]:
                        tech_params_text.append(f"{param}: {technical_params[param]}")
                if tech_params_text:
                    enhanced_prompt += f", technical_parameters: {', '.join(tech_params_text)}"
                processed_fields.add("technical_params")
            
            # 5. 添加负面提示词（明确标记）
            negative_prompt = parsed_json.get("negative_prompt", "")
            if negative_prompt and negative_prompt not in enhanced_prompt:
                enhanced_prompt += f", negative_prompt: {negative_prompt}"
                processed_fields.add("negative_prompt")
            
            # 6. 处理其他额外字段，确保信息完整性
            for key, value in parsed_json.items():
                # 跳过已经处理的字段和已知不需要的字段
                if key not in processed_fields and key not in {
                    "video_prompt", "prompt", "reference_images", "style_reference", 
                    "reference_keyframes", "previous_keyframe", "transition_style"
                }:
                    # 将额外字段转换为文本格式
                    if value:  # 只处理非空值
                        if isinstance(value, (list, tuple)):
                            value_text = ", ".join([str(v) for v in value if v])
                        elif isinstance(value, dict):
                            value_text = ", ".join([f"{k}: {v}" for k, v in value.items() if v])
                        else:
                            value_text = str(value).strip()
                        
                        if value_text and value_text not in enhanced_prompt:
                            enhanced_prompt += f", {key}: {value_text}"
        
        # 添加默认风格前缀（如果还没有）
        default_prefix = "cinematic, high quality, detailed, professional lighting"
        if default_prefix not in enhanced_prompt:
            enhanced_prompt = f"{default_prefix}, {enhanced_prompt}"
        
        # 减少冗余描述，移除重复内容
        enhanced_prompt = ' '.join(dict.fromkeys(enhanced_prompt.split())).strip()
        
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
    
    def parse(self, json_prompt: str) -> Dict[str, Any]:
        """
        解析JSON提示词并转换为文本格式（兼容test_simple_video_process.py的调用方式）
        
        Args:
            json_prompt: JSON格式的提示词字符串
            
        Returns:
            包含success和parsed_content的字典
        """
        try:
            # 使用parse_prompt方法解析
            parsed_result = self.parse_prompt(json_prompt, prompt_type="txt2img")
            
            # 提取增强后的prompt作为文本内容
            parsed_content = parsed_result.get("prompt", "")
            
            # 如果解析成功且有内容，返回success
            if parsed_content:
                return {
                    "success": True,
                    "parsed_content": parsed_content,
                    "full_result": parsed_result  # 包含完整的解析结果
                }
            else:
                return {
                    "success": False,
                    "parsed_content": "",
                    "error": "解析后未找到有效内容"
                }
                
        except Exception as e:
            logger.error(f"parse方法解析失败: {str(e)}")
            return {
                "success": False,
                "parsed_content": json_prompt,  # 失败时返回原始内容
                "error": str(e)
            }
    
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

