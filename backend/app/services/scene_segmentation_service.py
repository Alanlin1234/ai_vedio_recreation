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
    """
    场景分割服务类
    支持基于视觉特征的传统分割和基于大模型的智能分割
    """
    
    def __init__(self, min_scene_duration: float = 2.0, similarity_threshold: float = 0.8):
        """
        初始化场景分割服务
        
        Args:
            min_scene_duration: 最小场景时长（秒）
            similarity_threshold: 相似度阈值，用于判断场景变化
        """
        self.min_scene_duration = min_scene_duration
        self.similarity_threshold = similarity_threshold
        
        # 设置DashScope API密钥
        dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    
    def segment_video_scenes(self, video_path: str, method: str = "intelligent") -> List[Dict[str, Any]]:
        """
        对视频进行场景分割
        
        Args:
            video_path: 视频文件路径
            method: 分割方法，"intelligent"（智能分割）或 "traditional"（传统分割）
        
        Returns:
            场景分割结果列表
        """
        try:
            if method == "intelligent":
                return self.traditional_scene_segmentation(video_path)  # 如果没有内容参数，回退到传统方法
            else:
                return self.traditional_scene_segmentation(video_path)
        except Exception as e:
            print(f"场景分割失败，回退到传统分割: {e}")
            return self.traditional_scene_segmentation(video_path)
    
    def intelligent_scene_segmentation(self, video_path: str, video_understanding: str = "", audio_text: str = "") -> Dict[str, Any]:
        """
        基于大模型的智能场景分割（不传视频给模型，只基于文本内容）
        
        Args:
            video_path: 视频文件路径（用于获取视频时长等基本信息）
            video_understanding: 视频理解内容
            audio_text: 音频转录文本
        
        Returns:
            智能分割的场景结果字典
        """
        try:
            # 获取视频基本信息
            video_info = self._get_video_info(video_path)
            
            # 构建智能分割的提示词
            prompt = self._build_intelligent_segmentation_prompt_with_content(
                video_understanding, audio_text, video_info['duration']
            )
            
            print("正在调用qwen-plus模型进行智能场景分割...")
            
            # 使用 dashscope 库调用 qwen-plus 模型
            response = dashscope.Generation.call(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一个专业的视频内容分析师，擅长根据视频理解内容和音频文本进行智能场景分割，并生成高质量的英文文生视频提示词。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=4000
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                scenes = self._parse_intelligent_segmentation_result(result_text)
                
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
            return {
                'success': False,
                'error': str(e),
                'method': 'intelligent_failed'
            }
    
    def generate_video_prompt_for_scene(self, scene: Dict[str, Any], video_understanding: str, 
                                       audio_text: str, scene_index: int) -> Dict[str, Any]:
        """
        为单个场景生成视频提示词
        
        Args:
            scene: 场景信息
            video_understanding: 视频理解内容
            audio_text: 音频转录文本
            scene_index: 场景索引
        
        Returns:
            视频提示词结果
        """
        try:
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

请生成一个详细的英文文生视频提示词，包含：
1. 人物描述（外观、服装、表情、动作）
2. 环境场景（背景、道具、氛围）
3. 视觉风格（色彩、光线、画面质感）
4. 摄像机运动（角度、运动方式、景别）
5. 技术参数（画质、特效等）

要求：
- 提示词要具体详细，便于AI视频生成
- 保持与整体视频风格的一致性
- 长度控制在100-200个英文单词
- 使用专业的视频制作术语

请直接返回英文提示词，不需要其他解释。
"""
            
            # 使用 dashscope 库调用 qwen-plus 模型
            response = dashscope.Generation.call(
                model="qwen-plus",
                messages=[
                    {"role": "system", "content": "你是一个专业的视频制作专家，擅长生成高质量的英文文生视频提示词。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.8,
                max_tokens=500
            )
            
            if response.status_code == 200 and response.output and response.output.choices:
                video_prompt = response.output.choices[0].message.content.strip()
                
                return {
                    'success': True,
                    'video_prompt': video_prompt,
                    'duration': scene['duration'],
                    'technical_params': {
                        'aspect_ratio': '16:9',
                        'fps': 24,
                        'quality': 'high',
                        'style': 'cinematic'
                    }
                }
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
    
    def _parse_intelligent_segmentation_result(self, result_text: str) -> List[Dict[str, Any]]:
        """
        解析智能分割结果
        """
        try:
            # 尝试提取JSON部分
            import re
            json_match = re.search(r'```json\s*({.*?})\s*```', result_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有找到代码块，尝试直接解析
                json_str = result_text.strip()
            
            # 解析JSON
            result_data = json.loads(json_str)
            scenes = result_data.get('scenes', [])
            
            # 验证和标准化场景数据
            standardized_scenes = []
            for i, scene in enumerate(scenes):
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
            
            return standardized_scenes
            
        except Exception as e:
            print(f"解析智能分割结果失败: {e}")
            print(f"原始结果: {result_text}")
            return []
    
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
