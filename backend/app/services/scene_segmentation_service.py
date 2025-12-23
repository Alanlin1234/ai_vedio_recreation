import cv2
import numpy as np
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
import json
import dashscope
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config import config

class SceneSegmentationService:
    
    #场景分割服务类
    
    
    
    def __init__(self, min_scene_duration: float = 2.0, similarity_threshold: float = 0.8):
        """
        初始化场景分割服务
        
        
            min_scene_duration: 最小场景时长（秒）
            similarity_threshold: 相似度阈值，用于判断场景变化
        """
        self.min_scene_duration = min_scene_duration
        self.similarity_threshold = similarity_threshold
        
        # 使用用户提供的多个API密钥作为备用
        self.api_keys = [
            "sk-d433c2f93eff433583a88e3bdb37289f",  # 主密钥（用户提供的有效密钥）
            "sk-234d5ff939d843068e23b698d5df8616",   # 备用密钥1
            "sk-bfb72b1c875748c48b0c747fb0c17fc8",   # 备用密钥2
            "sk-c91a6b7c1b004289956c35d7a1c72496"     # 备用密钥3
        ]
        self.current_key_index = 0
        
        # 初始化日志记录器
        import logging
        self.logger = logging.getLogger(__name__)
        
        # 设置初始API密钥
        self.set_current_api_key()
        
    def set_current_api_key(self):
        """
        设置当前API密钥
        """
        self.current_api_key = self.api_keys[self.current_key_index]
        dashscope.api_key = self.current_api_key
        self.logger.info(f"使用API密钥 {self.current_api_key[:10]}...")
        
    def rotate_api_key(self):
        """
        轮换到下一个API密钥
        """
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.set_current_api_key()
        return self.current_api_key
    
    def segment_video_scenes(self, video_path: str, method: str = "intelligent") -> List[Dict[str, Any]]:
        """
        对视频进行场景分割
        
        Args:
            video_path: 视频文件路径
            method: 分割方法，"intelligent" 或 "traditional"
        
        Returns:
            场景分割结果列表
        """
        try:
            # 提取视频理解和音频文本（这里应该从其他服务获取，暂时使用默认值）
            video_understanding = ""
            audio_text = ""
            
            if method == "intelligent":
                # 调用智能场景分割
                result = self.intelligent_scene_segmentation(video_path, video_understanding, audio_text)
                if result.get('success', False):
                    return result['scenes']
                else:
                    print(f"智能场景分割失败，回退到传统分割: {result.get('error', '未知错误')}")
                    return self.traditional_scene_segmentation(video_path)
            else:
                return self.traditional_scene_segmentation(video_path)
        except Exception as e:
            print(f"场景分割失败，回退到传统分割: {e}")
            return self.traditional_scene_segmentation(video_path)
    
    def optimize_json_prompt(self, json_prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用qwen-plus模型优化JSON格式的提示词
        
        Args:
            json_prompt: 需要优化的JSON提示词
            
        Returns:
            优化后的JSON提示词
        """
        try:
            print("正在调用qwen-plus模型优化JSON提示词...")
            
            # 构建优化提示词
            prompt = f"""
            请优化以下JSON格式的视频场景提示词，确保每个场景的描述更详细、更适合视频生成，同时保持原有结构不变：
            
            {json.dumps(json_prompt, ensure_ascii=False, indent=2)}
            
            请返回优化后的完整JSON内容，不要添加任何额外的解释或说明。
            """
            
            # 调用qwen-plus-latest模型
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的视频内容优化专家，擅长优化视频场景提示词，使其更适合生成高质量视频。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=8000
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                
                # 提取纯JSON部分
                import re
                json_start = result_text.find('{')
                json_end = result_text.rfind('}')
                if json_start != -1 and json_end != -1:
                    json_str = result_text[json_start:json_end+1]
                    optimized_json = json.loads(json_str)
                    print("JSON提示词优化成功")
                    return optimized_json
                else:
                    print("无法提取优化后的JSON内容，返回原始内容")
                    return json_prompt
            else:
                print("JSON提示词优化失败，返回原始内容")
                return json_prompt
        except Exception as e:
            print(f"JSON提示词优化异常: {e}，返回原始内容")
            return json_prompt
    
    def json_to_text_prompt(self, json_prompt: Dict[str, Any]) -> str:
        """
        将JSON格式的提示词转换为适合qwen-image模型的文本格式
        
        Args:
            json_prompt: JSON格式的提示词
            
        Returns:
            文本格式的提示词
        """
        try:
            # 增强的JSON到文本转换，确保提取所有信息
            text_prompt_parts = []
            
            # 1. 首先提取顶层的video_prompt字段（如果是字符串直接使用）
            if 'video_prompt' in json_prompt:
                video_prompt_content = json_prompt['video_prompt']
                # 如果video_prompt是字符串，直接作为主要描述
                if isinstance(video_prompt_content, str):
                    text_prompt_parts.append(video_prompt_content)
                # 如果video_prompt是字典，提取其中的video_prompt字段
                elif isinstance(video_prompt_content, dict):
                    if 'video_prompt' in video_prompt_content and isinstance(video_prompt_content['video_prompt'], str):
                        text_prompt_parts.append(video_prompt_content['video_prompt'])
                    # 同时提取video_prompt字典中的其他字段
                    for key, value in video_prompt_content.items():
                        if key != 'video_prompt':
                            if isinstance(value, dict):
                                # 如果是嵌套字典，详细处理
                                nested_parts = []
                                for sub_key, sub_value in value.items():
                                    nested_parts.append(f"{sub_key}: {sub_value}")
                                if nested_parts:
                                    text_prompt_parts.append(f"{key}: {', '.join(nested_parts)}")
                            else:
                                text_prompt_parts.append(f"{key}: {value}")
            
            # 2. 提取顶层的description字段（如果有）
            if 'description' in json_prompt and isinstance(json_prompt['description'], str):
                if not text_prompt_parts:  # 如果还没有主要描述，使用description
                    text_prompt_parts.append(json_prompt['description'])
                else:  # 否则作为补充信息
                    text_prompt_parts.append(f"描述: {json_prompt['description']}")
            
            # 3. 提取顶层的style_elements字段
            if 'style_elements' in json_prompt and isinstance(json_prompt['style_elements'], dict):
                style_parts = []
                style_elements = json_prompt['style_elements']
                
                if 'characters' in style_elements and style_elements['characters']:
                    style_parts.append(f"人物: {style_elements['characters']}")
                if 'environment' in style_elements and style_elements['environment']:
                    style_parts.append(f"环境: {style_elements['environment']}")
                if 'visual_style' in style_elements and style_elements['visual_style']:
                    style_parts.append(f"视觉风格: {style_elements['visual_style']}")
                if 'camera_movement' in style_elements and style_elements['camera_movement']:
                    style_parts.append(f"摄像机运动: {style_elements['camera_movement']}")
                if 'style' in style_elements and style_elements['style']:
                    style_parts.append(f"风格: {style_elements['style']}")
                if 'quality' in style_elements and style_elements['quality']:
                    style_parts.append(f"质量: {style_elements['quality']}")
                if 'motion' in style_elements and style_elements['motion']:
                    style_parts.append(f"运动: {style_elements['motion']}")
                
                # 添加其他未显式处理的风格元素
                other_style_elements = [k for k in style_elements.keys() 
                                      if k not in ['characters', 'environment', 'visual_style', 'camera_movement', 'style', 'quality', 'motion']]
                for key in other_style_elements:
                    style_parts.append(f"{key}: {style_elements[key]}")
                
                if style_parts:
                    text_prompt_parts.append(f"风格元素: {'; '.join(style_parts)}")
            
            # 4. 提取顶层的technical_params字段
            if 'technical_params' in json_prompt and isinstance(json_prompt['technical_params'], dict):
                tech_parts = []
                technical_params = json_prompt['technical_params']
                
                if 'aspect_ratio' in technical_params and technical_params['aspect_ratio']:
                    tech_parts.append(f"宽高比: {technical_params['aspect_ratio']}")
                if 'fps' in technical_params and technical_params['fps']:
                    tech_parts.append(f"帧率: {technical_params['fps']}fps")
                if 'quality' in technical_params and technical_params['quality']:
                    tech_parts.append(f"质量: {technical_params['quality']}")
                if 'resolution' in technical_params and technical_params['resolution']:
                    tech_parts.append(f"分辨率: {technical_params['resolution']}")
                if 'width' in technical_params and technical_params['width']:
                    tech_parts.append(f"宽度: {technical_params['width']}")
                if 'height' in technical_params and technical_params['height']:
                    tech_parts.append(f"高度: {technical_params['height']}")
                if 'duration' in technical_params and technical_params['duration']:
                    tech_parts.append(f"时长: {technical_params['duration']}秒")
                
                # 添加其他未显式处理的技术参数
                other_tech_params = [k for k in technical_params.keys() 
                                   if k not in ['aspect_ratio', 'fps', 'quality', 'resolution', 'width', 'height', 'duration']]
                for key in other_tech_params:
                    tech_parts.append(f"{key}: {technical_params[key]}")
                
                if tech_parts:
                    text_prompt_parts.append(f"技术参数: {'; '.join(tech_parts)}")
            
            # 5. 提取顶层的scene_info字段
            if 'scene_info' in json_prompt and isinstance(json_prompt['scene_info'], dict):
                scene_parts = []
                scene_info = json_prompt['scene_info']
                
                for key, value in scene_info.items():
                    scene_parts.append(f"{key}: {value}")
                
                if scene_parts:
                    text_prompt_parts.append(f"场景信息: {', '.join(scene_parts)}")
            
            # 6. 处理其他顶层字段
            other_fields = ['scenes', 'video_understanding', 'audio_text']
            for key in json_prompt.keys():
                if key not in ['video_prompt', 'description', 'style_elements', 'technical_params', 'scene_info'] + other_fields:
                    value = json_prompt[key]
                    if isinstance(value, (str, int, float, bool)):
                        text_prompt_parts.append(f"{key}: {value}")
                    elif isinstance(value, dict):
                        # 对其他字典类型字段进行递归处理
                        dict_parts = []
                        for sub_key, sub_value in value.items():
                            dict_parts.append(f"{sub_key}: {sub_value}")
                        if dict_parts:
                            text_prompt_parts.append(f"{key}: {', '.join(dict_parts)}")
            
            # 如果没有提取到任何信息，返回原始JSON的字符串表示
            if not text_prompt_parts:
                return json.dumps(json_prompt, ensure_ascii=False, indent=2)
            
            # 合并所有部分，确保信息完整
            text_prompt = "\n".join(text_prompt_parts)
            
            # 去除重复的空行
            lines = [line.strip() for line in text_prompt.split('\n') if line.strip()]
            text_prompt = "\n".join(lines)
            
            return text_prompt
        except Exception as e:
            print(f"JSON转文本提示词异常: {e}")
            import traceback
            traceback.print_exc()
            # 发生异常时，返回原始JSON的字符串表示，确保不丢失任何信息
            return json.dumps(json_prompt, ensure_ascii=False, indent=2)
    
    def intelligent_scene_segmentation(self, video_path: str, video_understanding: str = "", audio_text: str = "") -> Dict[str, Any]:
        """
        基于大模型的智能场景分割
        
        
            video_path: 视频文件路径（用于获取视频时长等基本信息）
            video_understanding: 视频理解内容
            audio_text: 音频转录文本
        
       
        """
        try:
            # 获取视频基本信息
            video_info = self._get_video_info(video_path)
            
            # 构建智能分割的提示词
            prompt = self._build_intelligent_segmentation_prompt_with_content(
                video_understanding, audio_text, video_info['duration']
            )
            
            print("正在调用qwen-plus-latest模型进行智能场景分割...")
            
            # 使用 dashscope 库调用 qwen-plus-latest 模型
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的视频内容分析师，擅长根据视频理解内容和音频文本进行智能场景分割，并生成高质量的英文文生视频提示词。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=8000
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                
                # 提取纯JSON部分
                import re
                # 找到JSON的开始和结束位置
                json_start = result_text.find('{')
                json_end = result_text.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    # 提取纯JSON
                    pure_json_text = result_text[json_start:json_end + 1]
                    print(f"[DEBUG] 提取到纯JSON，长度: {len(pure_json_text)}")
                else:
                    pure_json_text = result_text
                    print(f"[DEBUG] 未找到明确的JSON边界，使用完整文本")
                
                scenes = self._parse_intelligent_segmentation_result(pure_json_text)
                
                print(f"[DEBUG] 解析出 {len(scenes)} 个场景")
                
                # 保存生成的场景和prompt到文件
                self._save_prompts_to_file(video_path, scenes, pure_json_text, "intelligent_segmentation")
                
                return {
                    'success': True,
                    'scenes': scenes,
                    'method': 'intelligent',
                    'processing_time': 0,
                    'model_response': result_text
                }
            else:
                error_msg = response.message if hasattr(response, 'message') else '未知错误'
                raise Exception(f"大模型响应错误: {error_msg}")
                
        except Exception as e:
            print(f"智能场景分割失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'method': 'intelligent_failed'
            }
    
    def create_scenes_from_slices(self, video_slices: List[Dict[str, Any]], slice_analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据视频切片创建场景，实现切片和场景的一一对应
        
        Args:
            video_slices: 视频切片列表
            slice_analyses: 切片分析结果列表
        
        Returns:
            场景列表，每个场景对应一个切片
        """
        try:
            print(f"开始根据 {len(video_slices)} 个切片创建场景...")
            scenes = []
            
            # 确保切片和分析结果数量一致
            if len(video_slices) != len(slice_analyses):
                print(f"警告：切片数量 ({len(video_slices)}) 与分析结果数量 ({len(slice_analyses)}) 不一致，将使用可用的数据")
            
            # 遍历切片，为每个切片创建一个场景
            for i in range(min(len(video_slices), len(slice_analyses))):
                slice_info = video_slices[i]
                slice_analysis = slice_analyses[i]
                
                # 从切片分析结果中提取场景信息
                scene_description = slice_analysis.get("description", f"场景 {i+1}")
                video_prompt = slice_analysis.get("video_prompt", "")
                style_elements = slice_analysis.get("style_elements", {})
                
                # 如果没有video_prompt，尝试从其他字段提取
                if not video_prompt:
                    raw_analysis = slice_analysis.get("raw_analysis", "")
                    if raw_analysis:
                        # 简单处理raw_analysis，提取关键信息
                        video_prompt = raw_analysis[:200] + "..." if len(raw_analysis) > 200 else raw_analysis
                    else:
                        # 使用切片信息生成基本提示词
                        video_prompt = f"Scene {i+1}: Video slice from {slice_info['start_time']:.1f}s to {slice_info['start_time']+slice_info['duration']:.1f}s"
                
                # 创建场景
                scene = {
                    "scene_id": i + 1,
                    "start_time": slice_info["start_time"],
                    "end_time": slice_info["start_time"] + slice_info["duration"],
                    "duration": slice_info["duration"],
                    "description": scene_description,
                    "video_prompt": video_prompt,
                    "style_elements": style_elements,
                    "slice_id": slice_info["slice_id"]
                }
                
                scenes.append(scene)
                print(f"创建场景 {i+1}: {scene_description[:50]}...")
            
            print(f"成功创建 {len(scenes)} 个场景，与切片一一对应")
            return scenes
        except Exception as e:
            print(f"根据切片创建场景失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def combine_prompts(self, qwen_omni_prompt: Dict[str, Any], qwen_vl_prompt: Dict[str, Any]) -> Dict[str, Any]:
        """
        结合qwen-omni-turbo和qwen3-vl生成的prompt
        
        Args:
            qwen_omni_prompt: qwen-omni-turbo生成的prompt
            qwen_vl_prompt: qwen3-vl生成的prompt
            
        Returns:
            结合后的完整prompt
        """
        try:
            logger.info("开始结合qwen-omni-turbo和qwen3-vl生成的prompt")
            
            # 1. 确保输入是字典格式
            if not isinstance(qwen_omni_prompt, dict):
                qwen_omni_prompt = json.loads(qwen_omni_prompt) if isinstance(qwen_omni_prompt, str) else {}
            
            if not isinstance(qwen_vl_prompt, dict):
                qwen_vl_prompt = json.loads(qwen_vl_prompt) if isinstance(qwen_vl_prompt, str) else {}
            
            # 2. 构建结合后的prompt
            combined_prompt = {
                "video_prompt": "",
                "scene_info": {},
                "style_elements": {},
                "technical_params": {},
                "objects": [],
                "people": [],
                "actions": [],
                "emotions": [],
                "atmosphere": ""
            }
            
            # 3. 合并场景信息
            scene_info_omni = qwen_omni_prompt.get("scene_info", {})
            scene_info_vl = qwen_vl_prompt.get("scene_info", {})
            combined_prompt["scene_info"] = {**scene_info_omni, **scene_info_vl}
            
            # 4. 合并风格元素
            style_omni = qwen_omni_prompt.get("style_elements", {})
            style_vl = qwen_vl_prompt.get("style_elements", {})
            combined_prompt["style_elements"] = {**style_omni, **style_vl}
            
            # 5. 合并技术参数
            tech_omni = qwen_omni_prompt.get("technical_params", {})
            tech_vl = qwen_vl_prompt.get("technical_params", {})
            combined_prompt["technical_params"] = {**tech_omni, **tech_vl}
            
            # 6. 合并物体、人物、动作等列表信息
            for key in ["objects", "people", "actions", "emotions"]:
                combined_prompt[key] = list(set(qwen_omni_prompt.get(key, []) + qwen_vl_prompt.get(key, [])))
            
            # 7. 合并氛围描述
            combined_prompt["atmosphere"] = qwen_omni_prompt.get("atmosphere", "") or qwen_vl_prompt.get("atmosphere", "")
            
            # 8. 构建最终的视频提示词
            video_prompt_parts = []
            
            # 从qwen-omni获取的文本描述
            omni_video_prompt = qwen_omni_prompt.get("video_prompt", "")
            if omni_video_prompt:
                video_prompt_parts.append(omni_video_prompt)
            
            # 从qwen-vl获取的视觉描述
            vl_video_prompt = qwen_vl_prompt.get("video_prompt", "")
            if vl_video_prompt:
                video_prompt_parts.append(vl_video_prompt)
            
            # 添加风格和氛围信息
            style_desc = qwen_vl_prompt.get("style", "") or qwen_omni_prompt.get("style", "")
            if style_desc:
                video_prompt_parts.append(f"视觉风格: {style_desc}")
            
            # 合并所有部分
            combined_prompt["video_prompt"] = " ".join(video_prompt_parts)
            
            # 9. 确保所有必要字段存在
            if not combined_prompt["video_prompt"]:
                # 兜底方案：从场景描述生成提示词
                scene_desc = combined_prompt["scene_info"].get("description", "")
                if scene_desc:
                    combined_prompt["video_prompt"] = scene_desc
                else:
                    combined_prompt["video_prompt"] = "A scene from the video"
            
            logger.info("成功结合两个模型的prompt")
            return {
                "success": True,
                "prompt": combined_prompt
            }
            
        except Exception as e:
            logger.error(f"结合prompt失败: {e}")
            import traceback
            traceback.print_exc()
            # 失败时返回qwen-omni的prompt作为兜底
            return {
                "success": False,
                "error": str(e),
                "prompt": qwen_omni_prompt
            }
    
    def generate_video_prompt_for_scene(self, scene: Dict[str, Any], video_understanding: str, 
                                       audio_text: str, scene_index: int, output_format: str = "json",
                                       previous_scene_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        为单个场景生成视频提示词
        
        Args:
            scene: 场景信息
            video_understanding: 视频理解内容
            audio_text: 音频转录文本
            scene_index: 场景索引
            output_format: 输出格式，可选值："text"（纯文本）、"json"（JSON格式，默认）
            previous_scene_info: 上一个场景的信息，包含关键帧和风格等
        
        Returns:
            包含视频提示词的字典
        """
        try:
            # 提取原始视频的风格信息（如动画风格）
            style_info = ""
            if "动画" in video_understanding or "cartoon" in video_understanding.lower():
                style_info = "\n非常重要：视频必须是动画风格，保持与原始视频一致的卡通风格。"
            
            # 添加统一的字幕生成指令
            subtitle_instruction = "\n非常重要：视频必须生成清晰的中文字幕，字体美观，位置居中，确保观众能够清晰阅读。字幕内容应与场景的音频内容一致。"
            
            # 添加上一场景的参考信息（如果有）
            previous_info = ""
            if previous_scene_info:
                previous_info = f"\n\n上一个场景的信息：\n- 上一场景风格：{previous_scene_info.get('style_elements', {}).get('visual_style', '')}\n- 上一场景人物：{previous_scene_info.get('style_elements', {}).get('characters', '')}\n- 上一场景环境：{previous_scene_info.get('style_elements', {}).get('environment', '')}\n\n非常重要：当前场景必须与上一个场景保持视觉连贯性，包括风格、人物和环境的一致性。"            
            
            # 根据输出格式构建不同的提示词
            if output_format == "json":
                prompt = f"""
基于以下信息为场景 {scene_index + 1} 生成详细的英文文生视频提示词，并按指定JSON格式返回结果：

场景信息：
- 开始时间: {scene['start_time']:.1f}秒
- 结束时间: {scene['end_time']:.1f}秒
- 时长: {scene['duration']:.1f}秒
- 描述: {scene.get('description', '')}

视频理解内容：
{video_understanding}

音频转录文本：
{audio_text}
{previous_info}

请生成一个详细的英文文生视频提示词，包含：
1. 人物描述（外观、服装、表情、动作）
2. 环境场景（背景、道具、氛围）
3. 视觉风格（色彩、光线、画面质感）
4. 摄像机运动（角度、运动方式、景别）
5. 技术参数（画质、特效等）

要求：
- 提示词要具体详细，便于AI视频生成
- 保持与整体视频风格的一致性{style_info}
- 长度控制在100-200个英文单词
- 使用专业的视频制作术语
- 确保生成的内容与原始视频内容高度相关
- 如果是动画视频，必须保持动画风格
- 必须包含生成清晰中文字幕的指令{subtitle_instruction}

请严格按照以下JSON格式返回结果，不要添加任何其他解释，不要包含任何markdown格式（如```json等）：
{{
  "video_prompt": "详细的英文视频提示词",
  "scene_info": {{
    "scene_id": {scene_index + 1},
    "start_time": {scene['start_time']:.1f},
    "end_time": {scene['end_time']:.1f},
    "duration": {scene['duration']:.1f}
  }},
  "style_elements": {{
    "characters": "人物描述",
    "environment": "环境描述",
    "visual_style": "视觉风格",
    "camera_movement": "摄像机运动"
  }},
  "technical_params": {{
    "aspect_ratio": "16:9",
    "fps": 24,
    "quality": "high"
  }}
}}
"""
            else:
                prompt = f"""
基于以下信息为场景 {scene_index + 1} 生成详细的英文文生视频提示词：

场景信息：
- 开始时间: {scene['start_time']:.1f}秒
- 结束时间: {scene['end_time']:.1f}秒
- 时长: {scene['duration']:.1f}秒
- 描述: {scene.get('description', '')}

视频理解内容：
{video_understanding}

音频转录文本：
{audio_text}
{previous_info}

请生成一个详细的英文文生视频提示词，包含：
1. 人物描述（外观、服装、表情、动作）
2. 环境场景（背景、道具、氛围）
3. 视觉风格（色彩、光线、画面质感）
4. 摄像机运动（角度、运动方式、景别）
5. 技术参数（画质、特效等）

要求：
- 提示词要具体详细，便于AI视频生成
- 保持与整体视频风格的一致性{style_info}
- 长度控制在100-200个英文单词
- 使用专业的视频制作术语
- 确保生成的内容与原始视频内容高度相关

请直接返回英文提示词，不需要其他解释。
"""
            
            # 使用 dashscope 库调用 qwen-plus-latest 模型
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的视频制作专家，擅长生成高质量的英文文生视频提示词。必须严格按照要求的格式返回结果，不要添加任何额外的解释或格式。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,  # 降低温度，减少随机性
                max_tokens=800  # 增加最大token数，确保完整生成
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                model_response = response.output.choices[0].message.content.strip()
                
                if output_format == "json":
                    try:
                        # 增强的JSON提取逻辑
                        import json
                        import re
                        
                        # 1. 清理和预处理模型响应
                        # 去除各种可能的代码块标记
                        cleaned_response = re.sub(r'^```(json|text|)\n|\n```$', '', model_response).strip()
                        # 处理特殊字符
                        cleaned_response = re.sub(r'[\x00-\x1F\x7F]', '', cleaned_response)
                        # 替换中文引号和标点为英文格式
                        cleaned_response = re.sub(r'“|”', '"', cleaned_response)
                        cleaned_response = re.sub(r'，', ',', cleaned_response)
                        cleaned_response = re.sub(r'：', ':', cleaned_response)
                        # 移除多余空格
                        cleaned_response = re.sub(r'\s+', ' ', cleaned_response)
                        
                        # 2. 尝试多种JSON解析方式
                        prompt_json = None
                        
                        # 方式1: 直接解析
                        try:
                            prompt_json = json.loads(cleaned_response)
                            print(f"[DEBUG] 直接解析JSON成功")
                        except json.JSONDecodeError:
                            # 方式2: 提取最外层JSON
                            print(f"[DEBUG] 直接解析失败，尝试提取最外层JSON")
                            json_start = cleaned_response.find('{')
                            json_end = cleaned_response.rfind('}')
                            if json_start != -1 and json_end != -1:
                                json_str = cleaned_response[json_start:json_end+1]
                                try:
                                    prompt_json = json.loads(json_str)
                                    print(f"[DEBUG] 提取最外层JSON成功")
                                except json.JSONDecodeError:
                                    # 方式3: 更宽松的解析，移除可能的错误字符
                                    print(f"[DEBUG] 提取最外层JSON失败，尝试宽松解析")
                                    # 移除所有非JSON字符，只保留基本的JSON结构字符
                                    relaxed_str = re.sub(r'[^\x00-\x7F]', '', json_str)
                                    relaxed_str = re.sub(r'[^\{\}\[\],:".\w\s\d-]', '', relaxed_str)
                                    try:
                                        prompt_json = json.loads(relaxed_str)
                                        print(f"[DEBUG] 宽松解析成功")
                                    except json.JSONDecodeError:
                                        # 所有解析方法都失败
                                        raise json.JSONDecodeError("无法提取有效的JSON", cleaned_response, 0)
                        
                        # 3. JSON结构验证
                        if not isinstance(prompt_json, dict):
                            raise ValueError("JSON不是字典格式")
                        
                        # 4. 关键字段验证和补全
                        # 确保所有必要字段存在
                        required_fields = ['video_prompt', 'scene_info', 'style_elements', 'technical_params']
                        for field in required_fields:
                            if field not in prompt_json:
                                # 补全缺失的字段
                                if field == 'video_prompt':
                                    prompt_json['video_prompt'] = prompt_json.get('description', '') or prompt_json.get('content', '') or f"Scene {scene_index + 1} video prompt"
                                elif field == 'scene_info':
                                    prompt_json['scene_info'] = {
                                        'scene_id': scene_index + 1,
                                        'start_time': scene['start_time'],
                                        'end_time': scene['end_time'],
                                        'duration': scene['duration']
                                    }
                                elif field == 'style_elements':
                                    prompt_json['style_elements'] = {
                                        'characters': prompt_json.get('characters', ''),
                                        'environment': prompt_json.get('environment', ''),
                                        'visual_style': prompt_json.get('visual_style', ''),
                                        'camera_movement': prompt_json.get('camera_movement', '')
                                    }
                                elif field == 'technical_params':
                                    prompt_json['technical_params'] = {
                                        'aspect_ratio': '16:9',
                                        'fps': 24,
                                        'quality': 'high'
                                    }
                        
                        # 5. 子字段验证和补全
                        # 验证scene_info字段
                        if isinstance(prompt_json['scene_info'], dict):
                            scene_info = prompt_json['scene_info']
                            if 'scene_id' not in scene_info:
                                scene_info['scene_id'] = scene_index + 1
                            if 'start_time' not in scene_info:
                                scene_info['start_time'] = scene['start_time']
                            if 'end_time' not in scene_info:
                                scene_info['end_time'] = scene['end_time']
                            if 'duration' not in scene_info:
                                scene_info['duration'] = scene['duration']
                        
                        # 验证style_elements字段
                        if isinstance(prompt_json['style_elements'], dict):
                            style_elements = prompt_json['style_elements']
                            if 'characters' not in style_elements:
                                style_elements['characters'] = ''
                            if 'environment' not in style_elements:
                                style_elements['environment'] = ''
                            if 'visual_style' not in style_elements:
                                style_elements['visual_style'] = ''
                            if 'camera_movement' not in style_elements:
                                style_elements['camera_movement'] = ''
                        
                        # 验证technical_params字段
                        if isinstance(prompt_json['technical_params'], dict):
                            technical_params = prompt_json['technical_params']
                            if 'aspect_ratio' not in technical_params:
                                technical_params['aspect_ratio'] = '16:9'
                            if 'fps' not in technical_params:
                                technical_params['fps'] = 24
                            if 'quality' not in technical_params:
                                technical_params['quality'] = 'high'
                        
                        print(f"[DEBUG] JSON验证和补全完成")
                        
                        # 6. 构建场景提示词数据
                        scene_prompt_data = {
                            'success': True,
                            'video_prompt': prompt_json.get('video_prompt', ''),
                            'scene_info': prompt_json.get('scene_info', {}),
                            'style_elements': prompt_json.get('style_elements', {}),
                            'technical_params': prompt_json.get('technical_params', {}),
                            'duration': scene['duration'],
                            'raw_response': model_response
                        }
                        
                        return scene_prompt_data
                    except Exception as e:
                        # 如果JSON解析失败，降级处理，但保留更多信息
                        self.logger.warning(f"JSON解析失败，使用增强的纯文本格式: {e}")
                        self.logger.debug(f"原始响应: {model_response}")
                        
                        # 从原始响应中提取关键信息
                        video_prompt = model_response
                        
                        # 尝试从响应中提取可能的视频提示词
                        if ':' in model_response:
                            # 简单的键值对提取
                            for line in model_response.split('\n'):
                                if 'video_prompt' in line.lower() or 'prompt' in line.lower():
                                    parts = line.split(':', 1)
                                    if len(parts) > 1:
                                        video_prompt = parts[1].strip().strip('"').strip("'")
                                        break
                        
                        scene_prompt_data = {
                            'success': True,
                            'video_prompt': video_prompt,
                            'duration': scene['duration'],
                            'technical_params': {
                                'aspect_ratio': '16:9',
                                'fps': 24,
                                'quality': 'high',
                                'style': 'cinematic'
                            },
                            'warning': f'JSON解析失败，使用增强的纯文本格式: {str(e)}',
                            'raw_response': model_response
                        }
                        return scene_prompt_data
                else:
                    # 纯文本格式直接返回
                    scene_prompt_data = {
                        'success': True,
                        'video_prompt': model_response,
                        'duration': scene['duration'],
                        'technical_params': {
                            'aspect_ratio': '16:9',
                            'fps': 24,
                            'quality': 'high',
                            'style': 'cinematic'
                        }
                    }
                    return scene_prompt_data
            else:
                error_msg = response.message if hasattr(response, 'message') else '未知错误'
                raise Exception(f"生成视频提示词失败: {error_msg}")
                
        except Exception as e:
            print(f"生成场景 {scene_index + 1} 视频提示词失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'video_prompt': f"Scene {scene_index + 1}: {scene.get('description', 'Video scene')}"
            }
    
    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        获取视频基本信息
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"无法打开视频文件: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            cap.release()
            
            return {
                'duration': duration,
                'fps': fps,
                'total_frames': total_frames,
                'width': width,
                'height': height,
                'aspect_ratio': f"{width}:{height}"
            }
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return {
                'duration': 30.0,  # 默认值
                'fps': 25.0,
                'total_frames': 750,
                'width': 1920,
                'height': 1080,
                'aspect_ratio': '16:9'
            }
    
    def _build_intelligent_segmentation_prompt_with_content(self, video_understanding: str, 
                                                          audio_text: str, duration: float) -> str:
        """
        基于视频理解内容和音频文本构建智能分割提示词
        """
        prompt = f"""基于以下视频理解内容和音频转录文本，请进行智能场景分割并为每个场景生成详细的英文视频提示词。

视频基本信息：
- 总时长：{duration:.1f} 秒

视频理解内容：
{video_understanding}

音频转录：
{audio_text}

分割要求：
1. 根据逻辑内容变化进行场景分割（如话题转换、情节发展、关键点）
2. 每个场景时长应在2-30秒之间
3. 场景转换要遵循视频的自然节奏
4. 所有场景总时长必须等于视频总长度

提示词生成要求：
1. 为每个场景生成详细的英文视频提示词
2. 包含：人物描述、环境、视觉风格、摄像机运动、技术参数
3. 保持整体风格和人物刻画的一致性
4. 提示词长度控制在80-150个英文单词之间

请按以下JSON格式返回结果：
{{
  "scenes": [
    {{
      "scene_id": 1,
      "start_time": 0.0,
      "end_time": 5.2,
      "duration": 5.2,
      "description": "Scene description in Chinese",
      "video_prompt": "Detailed English video generation prompt",
      "style_elements": {{
        "characters": "Character description",
        "environment": "Environment description",
        "visual_style": "Visual style",
        "camera_movement": "Camera movement"
      }}
    }}
  ]
}}"""
        return prompt
    
    def _save_prompts_to_file(self, video_path: str, scenes: List[Dict[str, Any]], raw_json: str, prompt_type: str):
        """
        保存生成的prompt到文件中
        
        Args:
            video_path: 原始视频路径
            scenes: 生成的场景列表
            raw_json: 原始JSON响应
            prompt_type: prompt类型，用于文件名
        """
        try:
            # 创建保存目录
            video_dir = os.path.dirname(video_path)
            prompts_dir = os.path.join(video_dir, "generated_prompts")
            os.makedirs(prompts_dir, exist_ok=True)
            
            # 生成文件名
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{base_name}_{prompt_type}_{timestamp}.json"
            file_path = os.path.join(prompts_dir, file_name)
            
            # 构建保存内容
            save_data = {
                "video_path": video_path,
                "timestamp": timestamp,
                "prompt_type": prompt_type,
                "scene_count": len(scenes),
                "scenes": scenes,
                "raw_json": raw_json
            }
            
            # 保存到文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 生成的prompt已保存到文件: {file_path}")
        except Exception as e:
            print(f"保存prompt到文件失败: {e}")
    
    def _parse_intelligent_segmentation_result(self, result_text: str) -> List[Dict[str, Any]]:
        """
        解析智能分割结果，增强版JSON解析逻辑
        """
        print("[DEBUG] 开始解析智能分割结果...")
        scenes = []
        
        try:
            # 清理和提取JSON部分
            import re
            
            # 移除可能的前后空格和换行
            cleaned_text = result_text.strip()
            print(f"[DEBUG] 清理后的文本长度: {len(cleaned_text)}")
            
            # 1. 处理各种可能的代码块标记
            # 移除 ```json, ```, ```text 等标记
            json_text = re.sub(r'^```(json|text|)\n|\n```$', '', cleaned_text).strip()
            print(f"[DEBUG] 移除代码块标记后长度: {len(json_text)}")
            
            # 2. 最小化处理特殊字符，只处理影响解析的关键字符
            # 仅替换中文引号和标点，不移除控制字符（可能破坏转义序列）
            # 不统一替换空格（可能破坏JSON结构）
            json_text = re.sub(r'“|”', '"', json_text)  # 替换中文引号为英文引号
            json_text = re.sub(r'，', ',', json_text)   # 替换中文逗号为英文逗号
            json_text = re.sub(r'：', ':', json_text)   # 替换中文冒号为英文冒号
            
            # 3. 尝试直接解析JSON
            print("[DEBUG] 尝试直接解析JSON...")
            try:
                result_data = json.loads(json_text)
                scenes = result_data.get('scenes', [])
                print(f"[DEBUG] 直接解析成功，获取到 {len(scenes)} 个场景")
            except json.JSONDecodeError:
                # 4. 尝试修复JSON格式
                print("[DEBUG] 尝试修复JSON格式...")
                
                # 查找最外层的JSON结构
                json_start = json_text.find('{')
                json_end = json_text.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    # 提取最外层JSON
                    outer_json = json_text[json_start:json_end+1]
                    print(f"[DEBUG] 提取最外层JSON，长度: {len(outer_json)}")
                    
                    try:
                        result_data = json.loads(outer_json)
                        scenes = result_data.get('scenes', [])
                        print(f"[DEBUG] 外层JSON解析成功，获取到 {len(scenes)} 个场景")
                    except json.JSONDecodeError as e:
                        print(f"[DEBUG] 外层JSON解析失败: {e}")
                        
                        # 5. 尝试提取scenes数组
                        print("[DEBUG] 尝试提取scenes数组...")
                        scenes_pattern = r'"scenes"\s*:\s*\[(.*?)\]' 
                        match = re.search(scenes_pattern, outer_json, re.DOTALL)
                        
                        if match:
                            scenes_content = match.group(1)
                            print(f"[DEBUG] 提取到scenes内容，长度: {len(scenes_content)}")
                            
                            # 尝试修复scenes数组的格式
                            # 确保数组元素之间有正确的逗号
                            scenes_content = re.sub(r'\}\s*\{', '}, {', scenes_content)
                            
                            # 尝试解析修复后的scenes数组
                            full_scenes_json = f"[{scenes_content}]"
                            print(f"[DEBUG] 修复后的scenes JSON: {full_scenes_json[:100]}...")
                            
                            try:
                                scenes = json.loads(full_scenes_json)
                                print(f"[DEBUG] scenes数组解析成功，获取到 {len(scenes)} 个场景")
                            except json.JSONDecodeError as inner_e:
                                print(f"[DEBUG] scenes数组解析失败: {inner_e}")
                                
                                # 6. 最后尝试：直接查找所有场景对象
                                print("[DEBUG] 尝试直接提取场景对象...")
                                scene_pattern = r'\{[^}]*"scene_id"[^}]*\}'
                                scene_matches = re.findall(scene_pattern, outer_json, re.DOTALL)
                                print(f"[DEBUG] 找到 {len(scene_matches)} 个场景对象")
                                
                                scenes = []
                                for scene_str in scene_matches:
                                    try:
                                        scene = json.loads(scene_str)
                                        scenes.append(scene)
                                    except json.JSONDecodeError:
                                        # 尝试修复单个场景对象的JSON格式
                                        try:
                                            # 移除多余的逗号
                                            fixed_scene_str = re.sub(r',\s*}', '}', scene_str)
                                            fixed_scene_str = re.sub(r',\s*]', ']', fixed_scene_str)
                                            scene = json.loads(fixed_scene_str)
                                            scenes.append(scene)
                                        except:
                                            continue
                                
                                print(f"[DEBUG] 成功解析 {len(scenes)} 个场景对象")
        
        except Exception as general_error:
            print(f"[DEBUG] 发生通用错误: {general_error}")
            import traceback
            traceback.print_exc()
        
        # 验证和标准化场景数据
        standardized_scenes = []
        for i, scene in enumerate(scenes):
            try:
                standardized_scene = {
                    'scene_id': scene.get('scene_id', i + 1),
                    'start_time': float(scene.get('start_time', 0)),
                    'end_time': float(scene.get('end_time', 0)),
                    'duration': float(scene.get('duration', 0)),
                    'description': scene.get('description', f'场景 {i + 1}'),
                    'video_prompt': scene.get('video_prompt', ''),
                    'style_elements': scene.get('style_elements', {})
                }
                standardized_scenes.append(standardized_scene)
            except Exception as scene_error:
                print(f"[DEBUG] 标准化场景 {i+1} 失败: {scene_error}")
                continue
        
        # 确保至少返回一个场景，避免空列表
        if not standardized_scenes:
            print("[DEBUG] 标准化后无有效场景，创建默认场景")
            default_scene = {
                'scene_id': 1,
                'start_time': 0.0,
                'end_time': 10.0,
                'duration': 10.0,
                'description': f"默认场景: {result_text[:100]}...",
                'video_prompt': result_text[:200],
                'style_elements': {}
            }
            standardized_scenes = [default_scene]
        
        print(f"[DEBUG] 最终标准化场景数量: {len(standardized_scenes)}")
        return standardized_scenes
    
    # def traditional_scene_segmentation(self, video_path: str) -> List[Dict[str, Any]]:
    #     """
    #     基于视觉特征的传统场景分割
        
    #     Args:
    #         video_path: 视频文件路径
        
    #     Returns:
    #         传统分割的场景列表
    #     """
    #     try:
    #         # 打开视频文件
    #         cap = cv2.VideoCapture(video_path)
    #         if not cap.isOpened():
    #             raise Exception(f"无法打开视频文件: {video_path}")
            
    #         fps = cap.get(cv2.CAP_PROP_FPS)
    #         total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    #         duration = total_frames / fps
            
    #         scenes = []
    #         scene_start = 0
    #         prev_hist = None
    #         frame_count = 0
            
    #         print(f"开始传统场景分割，视频时长: {duration:.2f}秒，帧率: {fps:.2f}")
            
    #         while True:
    #             ret, frame = cap.read()
    #             if not ret:
    #                 break
                
    #             current_time = frame_count / fps
                
    #             # 每隔一定帧数进行分析（减少计算量）
    #             if frame_count % max(1, int(fps / 2)) == 0:
    #                 # 计算直方图
    #                 hist = cv2.calcHist([frame], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
    #                 hist = cv2.normalize(hist, hist).flatten()
                    
    #                 if prev_hist is not None:
    #                     # 计算相似度
    #                     similarity = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                        
    #                     # 如果相似度低于阈值且距离上个场景足够远，则认为是新场景
    #                     if similarity < self.similarity_threshold and (current_time - scene_start) >= self.min_scene_duration:
    #                         # 保存前一个场景
    #                         scenes.append({
    #                             'scene_id': len(scenes) + 1,
    #                             'start_time': scene_start,
    #                             'end_time': current_time,
    #                             'duration': current_time - scene_start,
    #                             'description': f"场景 {len(scenes) + 1}",
    #                             'key_frame_time': (scene_start + current_time) / 2
    #                         })
    #                         scene_start = current_time
                    
    #                 prev_hist = hist
                
    #             frame_count += 1
            
    #         # 添加最后一个场景
    #         if duration - scene_start >= self.min_scene_duration:
    #             scenes.append({
    #                 'scene_id': len(scenes) + 1,
    #                 'start_time': scene_start,
    #                 'end_time': duration,
    #                 'duration': duration - scene_start,
    #                 'description': f"场景 {len(scenes) + 1}",
    #                 'key_frame_time': (scene_start + duration) / 2
    #             })
            
    #         cap.release()
            
    #         # 优化场景分割结果
    #         scenes = self._optimize_scenes(scenes)
            
    #         print(f"传统场景分割完成，共分割出 {len(scenes)} 个场景")
    #         return scenes
            
    #     except Exception as e:
    #         if 'cap' in locals():
    #             cap.release()
    #         raise Exception(f"传统场景分割失败: {e}")
    
    # def _optimize_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     """
    #     优化场景分割结果
    #     """
    #     if not scenes:
    #         return scenes
        
    #     optimized_scenes = []
    #     current_scene = scenes[0].copy()
        
    #     for i in range(1, len(scenes)):
    #         scene = scenes[i]
            
    #         # 如果当前场景太短，合并到前一个场景
    #         if current_scene['duration'] < self.min_scene_duration:
    #             current_scene['end_time'] = scene['end_time']
    #             current_scene['duration'] = current_scene['end_time'] - current_scene['start_time']
    #             current_scene['description'] += f" + {scene['description']}"
    #         else:
    #             optimized_scenes.append(current_scene)
    #             current_scene = scene.copy()
        
    #     # 添加最后一个场景
    #     optimized_scenes.append(current_scene)
        
    #     # 重新编号
    #     for i, scene in enumerate(optimized_scenes):
    #         scene['scene_id'] = i + 1
        
    #     return optimized_scenes
