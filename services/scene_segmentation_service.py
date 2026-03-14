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
from .json_prompt_parser import JSONPromptParser
from app.utils.subtitle_utils import ensure_utf8_encoding, clean_subtitle_text, prepare_subtitle_prompt

# 初始化JSON解析器
json_parser = JSONPromptParser()

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
            "sk-6feb1f6d41e44107b326e99ac232427a",  # 主密钥（用户新提供的有效密钥）
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
请作为专业视频内容优化专家，对以下JSON格式的视频场景提示词进行全面优化：

{json.dumps(json_prompt, ensure_ascii=False, indent=2)}

## 优化要求：

### 1. 内容深度优化
- **场景描述**：增强叙事连贯性，明确场景目的和情感基调
- **视觉细节**：添加具体的色彩方案、光线效果、构图指导
- **人物刻画**：细化人物外观、动作、表情和互动，但**严格保持人物基本特征不变**（如发型、发色、肤色、性别等）
- **环境氛围**：丰富环境细节，增强空间感和真实感
- **镜头语言**：明确摄像机角度、运动方式和景别变化

### 2. 专业度提升
- 使用专业视频制作术语
- 提供具体的视觉参考（如电影风格、艺术流派）
- 确保技术参数符合视频制作标准
- 添加适当的节奏和剪辑建议

### 3. 结构保持
- 严格保持原始JSON结构不变
- 确保所有字段都有合理的值
- 保持场景之间的逻辑连贯性
- 维持整体风格的一致性

### 4. 格式要求
- 返回完整的优化后JSON内容
- 不要添加任何额外的解释或说明
- 确保JSON格式完全正确可解析
- 保持中文描述的准确性和流畅性

## 优化目标
生成的提示词应能直接用于AI视频生成，确保：
- 视频内容与描述高度一致
- 视觉效果达到专业水准
- 叙事逻辑清晰连贯
- 整体风格统一协调
- **人物基本特征保持一致**（如发型、发色、肤色、性别等）
            """
            
            # 调用qwen-plus-latest模型
            response = dashscope.Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一位顶尖的视频内容优化专家，精通AI视频生成技术和专业视频制作术语。你的专长是：\n1. 深度理解视频场景结构和叙事逻辑\n2. 精准捕捉视觉风格和美学元素\n3. 优化提示词以获得最佳AI视频生成效果\n4. 保持JSON数据结构的完整性和一致性\n5. 提供专业、详细且可执行的视频制作指导\n\n请严格按照要求优化提示词，确保每个场景描述都达到专业视频制作水准。"},
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
            # 使用优化后的JSON解析器
            if isinstance(json_prompt, dict):
                # 将字典转换为JSON字符串
                json_str = json.dumps(json_prompt, ensure_ascii=False)
                # 使用JSON解析器解析
                parse_result = json_parser.parse_prompt(json_str, prompt_type="txt2img")
                # 提取增强后的prompt
                return parse_result.get('prompt', '')
            elif isinstance(json_prompt, str):
                # 直接使用JSON解析器解析字符串
                parse_result = json_parser.parse_prompt(json_prompt, prompt_type="txt2img")
                return parse_result.get('prompt', json_prompt)
            else:
                # 其他类型，转换为字符串
                return str(json_prompt)
        except Exception as e:
            print(f"JSON转文本提示词失败: {e}")
            # 失败时返回原始内容
            if isinstance(json_prompt, dict):
                return json.dumps(json_prompt, ensure_ascii=False)
            else:
                return str(json_prompt)
    
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
            qwen_omni_prompt: qwen-omni-turbo生成的prompt（负责宏观场景和镜头移动分析）
            qwen_vl_prompt: qwen3-vl生成的prompt（负责视觉细节分析）
            
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
                "atmosphere": "",
                "camera_movement": ""  # 新增：专门存储镜头移动信息
            }
            
            # 3. 合并场景信息（优先使用qwen-omni的宏观场景分析）
            scene_info_omni = qwen_omni_prompt.get("scene_info", {})
            scene_info_vl = qwen_vl_prompt.get("scene_info", {})
            combined_prompt["scene_info"] = {**scene_info_omni, **scene_info_vl}
            
            # 4. 合并风格元素（优先使用qwen3-vl的视觉细节）
            style_omni = qwen_omni_prompt.get("style_elements", {})
            style_vl = qwen_vl_prompt.get("style_elements", {})
            # 移除qwen-omni中可能存在的镜头移动相关内容，避免冲突
            if "camera_movement" in style_omni:
                combined_prompt["camera_movement"] = style_omni["camera_movement"]
                del style_omni["camera_movement"]
            combined_prompt["style_elements"] = {**style_omni, **style_vl}
            
            # 5. 提取qwen-omni中的镜头移动信息
            camera_movement = qwen_omni_prompt.get("camera_movement", "") or qwen_omni_prompt.get("camera_movement_analysis", "")
            if camera_movement:
                combined_prompt["camera_movement"] = camera_movement
            
            # 6. 合并技术参数
            tech_omni = qwen_omni_prompt.get("technical_params", {})
            tech_vl = qwen_vl_prompt.get("technical_params", {})
            combined_prompt["technical_params"] = {**tech_omni, **tech_vl}
            
            # 7. 合并物体、人物、动作等列表信息
            for key in ["objects", "people", "actions", "emotions"]:
                combined_prompt[key] = list(set(qwen_omni_prompt.get(key, []) + qwen_vl_prompt.get(key, [])))
            
            # 8. 合并氛围描述（优先使用qwen-omni的宏观氛围）
            combined_prompt["atmosphere"] = qwen_omni_prompt.get("atmosphere", "") or qwen_vl_prompt.get("atmosphere", "")
            
            # 9. 构建最终的视频提示词（结构化分层）
            video_prompt_parts = []
            
            # 第一层：qwen-omni的宏观场景描述
            omni_video_prompt = qwen_omni_prompt.get("video_prompt", "")
            if omni_video_prompt:
                video_prompt_parts.append(f"[整体场景] {omni_video_prompt}")
            
            # 第二层：qwen-omni的镜头移动分析
            if combined_prompt["camera_movement"]:
                video_prompt_parts.append(f"[镜头移动] {combined_prompt['camera_movement']}")
            
            # 第三层：qwen3-vl的视觉细节描述
            vl_video_prompt = qwen_vl_prompt.get("video_prompt", "")
            if vl_video_prompt:
                video_prompt_parts.append(f"[视觉细节] {vl_video_prompt}")
            
            # 第四层：风格和氛围信息
            style_desc = qwen_vl_prompt.get("style", "") or qwen_omni_prompt.get("style", "")
            if style_desc:
                video_prompt_parts.append(f"[视觉风格] {style_desc}")
            
            # 合并所有部分
            combined_prompt["video_prompt"] = " ".join(video_prompt_parts)
            
            # 10. 确保所有必要字段存在
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
            
            # 清理和处理音频文本编码
            cleaned_audio_text = clean_subtitle_text(audio_text)
            
            # 添加统一的字幕生成指令（优化编码处理）
            subtitle_instruction = "\n\n[Subtitle Instructions]\nIMPORTANT: The video must include clear Chinese subtitles with the following specifications:\n1. Subtitle encoding: UTF-8\n2. Font: Clear and readable Chinese font\n3. Position: Centered at the bottom of the screen\n4. Color: White text with black outline for better readability\n5. Content: The subtitles must match the audio content of the scene\n6. Timing: Subtitles should be properly synchronized with the audio\n\n[字幕要求]\n非常重要：视频必须生成清晰的中文字幕，使用UTF-8编码，字体美观，位置居中，确保观众能够清晰阅读。字幕内容应与场景的音频内容一致。"
            
            # 添加上一场景的参考信息（如果有）- 增强版，包含更详细的上下文
            previous_info = ""
            if previous_scene_info:
                previous_prompt = previous_scene_info.get('video_prompt', '')
                previous_style = previous_scene_info.get('style_elements', {})
                previous_scene_data = previous_scene_info.get('scene_info', {})
                
                previous_info = (
                    f"\n\n【上一个场景的详细上下文信息】\n"
                    f"上一场景内容描述: {previous_prompt[:300]}\n"
                    f"上一场景风格: {previous_style.get('visual_style', '')}\n"
                    f"上一场景人物: {previous_style.get('characters', '')}\n"
                    f"上一场景环境: {previous_style.get('environment', '')}\n"
                    f"上一场景摄像机运动: {previous_style.get('camera_movement', '')}\n"
                    f"\n【关键约束】\n"
                    f"当前场景的第一个关键帧必须与上一个场景的最后一个关键帧完全相同！\n"
                    f"这意味着当前场景的起始画面必须无缝衔接上一个场景的结束画面。\n"
                    f"请确保第一个关键帧的视觉元素、构图、色彩、光线等都与上一场景的最后一帧保持完全一致。\n"
                    f"后续关键帧可以逐渐过渡到当前场景的主要内容，但必须保持视觉风格的连贯性。\n"
                    f"\n【场景连贯性要求】\n"
                    f"1. 第一个关键帧必须完美衔接上一场景的最后一帧（这是强制要求）\n"
                    f"2. 保持视觉风格的一致性（色彩、光线、画质）\n"
                    f"3. 保持人物外观的一致性（服装、发型、表情特征）\n"
                    f"4. 保持环境元素的一致性（背景、道具、氛围）\n"
                    f"5. 确保场景过渡自然流畅，没有突兀的跳跃"
                )            
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
{cleaned_audio_text}
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
{cleaned_audio_text}
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
