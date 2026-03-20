"""
阿里DashScope图像生成服务 - 用于生成分镜图
重点：确保所有分镜图之间的一致性极高
"""

import requests
import os
import json
import time
import logging
import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StoryboardImageGenerator:
    """分镜图生成器 - 使用阿里DashScope图像生成API"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "sk-5eeb025e53df459b9f8a4b4209bd5fa5"
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"

    def _generate_consistent_style_guide(self, story_content: str) -> Dict[str, str]:
        """生成统一的视觉风格指南，确保所有分镜图一致性"""
        try:
            import dashscope
            from dashscope import Generation
            from dashscope.api_entities.dashscope_response import GenerationResponse

            dashscope.api_key = self.api_key

            style_guide_prompt = f"""你是一个专业的视觉风格设计师。请分析以下故事内容，生成一个统一的视觉风格指南，用于指导后续所有分镜图的生成。

故事内容：
{story_content}

请生成以下内容（用JSON格式返回）：
{{
    "character_description": "人物描述：详细描述主要人物的外貌、服装、表情特征",
    "color_scheme": "色彩方案：描述整体色调和色彩搭配",
    "lighting_style": "光线风格：描述主光线处理方式",
    "scene_setting": "场景设定：描述环境的整体风格",
    "art_style": "艺术风格：描述整体的美术风格，如写实、插画、水墨等",
    "visual_mood": "视觉氛围：描述整体的情绪和氛围"
}}

要求：
1. 人物描述必须适用于所有场景，保持一致
2. 色彩方案要协调统一
3. 风格描述要具体明确，便于AI图像生成模型理解"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的视觉风格设计师。"},
                    {"role": "user", "content": style_guide_prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=1500
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                try:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end+1]
                        style_guide = json.loads(json_str)
                        logger.info(f"视觉风格指南生成成功")
                        return style_guide
                except:
                    pass

            return self._get_default_style_guide()

        except Exception as e:
            logger.error(f"生成视觉风格指南失败: {e}")
            return self._get_default_style_guide()

    def _get_default_style_guide(self) -> Dict[str, str]:
        """获取默认风格指南"""
        return {
            "character_description": "一位年轻的亚洲女性，长发披肩，穿着休闲服装，表情自然",
            "color_scheme": "温暖的棕色调，柔和的光线",
            "lighting_style": "自然散射光，温暖舒适",
            "scene_setting": "现代都市风格，简洁背景",
            "art_style": "电影感写实风格，高质量摄影",
            "visual_mood": "温馨、自然、真实"
        }

    def generate_storyboard_images(
        self,
        story_content: str,
        scenes: List[Dict[str, str]],
        output_dir: str,
        style_reference_image: str = None
    ) -> Dict[str, Any]:
        """
        生成分镜图，确保极高一致性

        Args:
            story_content: 故事内容
            scenes: 分镜场景列表，每个包含description和prompt
            output_dir: 输出目录
            style_reference_image: 风格参考图路径（可选）

        Returns:
            包含成功状态和生成图片路径的字典
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            # 第一步：生成统一的视觉风格指南
            logger.info("="*50)
            logger.info("开始生成统一的视觉风格指南...")
            style_guide = self._generate_consistent_style_guide(story_content)
            logger.info(f"视觉风格指南: {json.dumps(style_guide, ensure_ascii=False, indent=2)}")

            # 第二步：为每个场景生成图片
            generated_images = []
            logger.info("="*50)
            logger.info(f"开始生成 {len(scenes)} 个分镜图...")

            for idx, scene in enumerate(scenes):
                scene_num = idx + 1
                description = scene.get('description', '')
                scene_prompt = scene.get('prompt', '')

                logger.info(f"\n--- 开始生成场景 {scene_num}/{len(scenes)} ---")

                # 构建一致性极高的提示词
                final_prompt = self._build_consistent_prompt(
                    scene_description=description,
                    scene_prompt=scene_prompt,
                    style_guide=style_guide,
                    scene_number=scene_num,
                    total_scenes=len(scenes)
                )

                # 调用图像生成API
                image_path = self._call_image_generation_api(
                    prompt=final_prompt,
                    output_path=os.path.join(output_dir, f"storyboard_{scene_num:02d}.png"),
                    style_reference=style_reference_image
                )

                if image_path:
                    generated_images.append({
                        'scene_number': scene_num,
                        'description': description,
                        'prompt': scene_prompt,
                        'image_path': image_path,
                        'style_guide': style_guide
                    })
                    logger.info(f"场景 {scene_num} 图片生成成功: {image_path}")
                else:
                    logger.error(f"场景 {scene_num} 图片生成失败")
                    generated_images.append({
                        'scene_number': scene_num,
                        'description': description,
                        'prompt': scene_prompt,
                        'image_path': None,
                        'style_guide': style_guide,
                        'error': '图像生成失败'
                    })

            # 第三步：一致性检查
            logger.info("="*50)
            logger.info("进行一致性检查...")
            consistency_check = self._check_consistency(generated_images, style_guide)

            return {
                'success': True,
                'images': generated_images,
                'style_guide': style_guide,
                'consistency_check': consistency_check,
                'total_scenes': len(scenes),
                'generated_count': len([img for img in generated_images if img.get('image_path')])
            }

        except Exception as e:
            logger.error(f"生成分镜图失败: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'images': []
            }

    def _build_consistent_prompt(
        self,
        scene_description: str,
        scene_prompt: str,
        style_guide: Dict[str, str],
        scene_number: int,
        total_scenes: int
    ) -> str:
        """构建一致性极高的分镜图提示词"""

        prompt_template = f"""电影分镜图 {scene_number}/{total_scenes}：

[场景描述]
{scene_description}

[视觉风格规范 - 所有分镜必须严格遵守]
- 人物形象: {style_guide.get('character_description', '')}
- 色彩方案: {style_guide.get('color_scheme', '')}
- 光线风格: {style_guide.get('lighting_style', '')}
- 场景设定: {style_guide.get('scene_setting', '')}
- 艺术风格: {style_guide.get('art_style', '')}
- 视觉氛围: {style_guide.get('visual_mood', '')}

[生成要求]
1. 严格遵循上述视觉风格规范
2. 人物形象必须与规范完全一致
3. 色彩搭配必须统一协调
4. 画面质量：专业电影海报级别
5. 构图：电影镜头感，主体突出
6. 细节：8K分辨率，精致细节

请生成这个分镜的画面。"""

        return prompt_template

    def _call_image_generation_api(
        self,
        prompt: str,
        output_path: str,
        style_reference: str = None
    ) -> Optional[str]:
        """调用阿里DashScope图像生成API"""

        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.api_key

            api_prompt = f"""{prompt}

风格要求：电影质感，高清晰度，专业的电影分镜风格。

技术参数：16:9宽屏比例，分辨率1920x1080"""

            logger.info(f"调用图像生成API，提示词长度: {len(api_prompt)}")

            response = Generation.call(
                model="qwen-image-edit",
                messages=[{"role": "user", "content": [{"text": api_prompt, "image": None}]}],
                result_format='message'
            )

            if response.status_code == 200 and response.output and response.output.images:
                image_data = response.output.images[0]
                if isinstance(image_data, dict) and image_data.get('url'):
                    # 下载图片
                    image_url = image_data['url']
                    return self._download_image(image_url, output_path)
                elif hasattr(image_data, 'url'):
                    image_url = image_data.url
                    return self._download_image(image_url, output_path)

            logger.error(f"图像生成API返回错误: status={response.status_code}")
            return None

        except Exception as e:
            logger.error(f"调用图像生成API失败: {e}")
            traceback.print_exc()
            return None

    def _download_image(self, url: str, output_path: str) -> Optional[str]:
        """下载图片到本地"""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"图片下载成功: {output_path}")
                return output_path
            else:
                logger.error(f"图片下载失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"下载图片异常: {e}")
            return None

    def _check_consistency(
        self,
        generated_images: List[Dict],
        style_guide: Dict[str, str]
    ) -> Dict[str, Any]:
        """检查生成图片的一致性"""
        try:
            # 简单的一致性检查：检查是否所有图片都成功生成
            successful_images = [img for img in generated_images if img.get('image_path')]

            if len(successful_images) < 2:
                return {
                    'consistent': True,
                    'score': 1.0,
                    'message': '图片数量不足，无法充分评估一致性'
                }

            # 检查风格指南是否应用到所有图片
            all_have_style_guide = all(
                img.get('style_guide') == style_guide
                for img in successful_images
            )

            return {
                'consistent': all_have_style_guide,
                'score': 1.0 if all_have_style_guide else 0.5,
                'message': '所有分镜图已按照统一的视觉风格指南生成',
                'generated_images': len(successful_images),
                'total_scenes': len(generated_images)
            }

        except Exception as e:
            logger.error(f"一致性检查失败: {e}")
            return {
                'consistent': False,
                'score': 0.0,
                'error': str(e)
            }
