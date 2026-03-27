"""
分镜图生成集成服务
整合分镜脚本生成和图像生成，确保极高的一致性
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

logger = logging.getLogger(__name__)


class StoryboardGenerator:
    """分镜图生成器 - 同时生成文字脚本和图片"""

    def __init__(self):
        self.dashscope_api_key = Config.DASHSCOPE_API_KEY

    def generate_storyboard(
        self,
        story_content: str,
        scene_count: int = 6,
        output_dir: str = None,
        generate_images: bool = True
    ) -> Dict[str, Any]:
        """
        生成分镜图（脚本+可选图片）

        Args:
            story_content: 故事内容
            scene_count: 场景数量
            output_dir: 图片输出目录
            generate_images: 是否生成图片

        Returns:
            包含成功状态、场景列表、风格指南等
        """
        try:
            logger.info("="*60)
            logger.info(f"开始生成分镜图，场景数量: {scene_count}")
            logger.info("="*60)

            # 第一步：生成分镜脚本（确保一致性）
            scenes = self._generate_storyboard_scripts(story_content, scene_count)

            if not scenes:
                return {
                    'success': False,
                    'error': '分镜脚本生成失败',
                    'scenes': []
                }

            logger.info(f"分镜脚本生成成功，共{len(scenes)}个场景")

            # 第二步：生成视觉风格指南
            style_guide = self._generate_style_guide(story_content)
            logger.info(f"视觉风格指南: {json.dumps(style_guide, ensure_ascii=False)}")

            # 第三步：生成图片（如果需要）
            if generate_images and output_dir:
                scenes_with_images = self._generate_storyboard_images(
                    scenes=scenes,
                    style_guide=style_guide,
                    output_dir=output_dir
                )
                scenes = scenes_with_images

            return {
                'success': True,
                'scenes': scenes,
                'style_guide': style_guide,
                'total_scenes': len(scenes),
                'has_images': generate_images
            }

        except Exception as e:
            logger.error(f"生成分镜图失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'scenes': []
            }

    def _generate_storyboard_scripts(self, story_content: str, scene_count: int) -> List[Dict]:
        """生成分镜脚本"""
        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.dashscope_api_key

            prompt = f"""根据以下故事内容，生成{scene_count}个真实分镜场景。

故事内容：
{story_content[:1500]}

请生成真实的分镜内容，不要用模板。每个场景必须是真实的故事内容：

1. 根据故事的开端、发展、高潮、结局分配到{scene_count}个场景
2. 镜头类型要符合叙事需求（不是固定模板）
3. 画面描述要基于故事的真实情节
4. 台词要符合人物性格和情境
5. 视频提示词要具体、可执行

JSON格式（直接返回JSON，不要其他文字）：
[{{"scene_number":1,"shot_type":"根据情节选择合适的镜头","description":"真实的画面描述","plot":"真实的情节","dialogue":"真实的台词","prompt":"可执行的视频生成提示词","duration":4}}]"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的分镜设计师。必须生成真实、具体的内容，不能用'场景1：基于故事内容生成的场景画面描述'这样的模板。每个场景的描述都必须基于故事真实内容。"
                    },
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.8,
                max_tokens=3000
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                logger.info(f"[分镜脚本] AI返回: {result_text[:200]}...")
                scenes = self._parse_scenes_from_response(result_text, scene_count)

                if scenes and len(scenes) >= 2:
                    logger.info(f"[分镜脚本] 解析成功，共{len(scenes)}个场景")
                    return scenes
                else:
                    logger.warning(f"[分镜脚本] 解析结果无效: {scenes}")

            logger.error("[分镜脚本] 生成失败，使用备用方案")
            return self._generate_fallback_scenes(story_content, scene_count)

        except Exception as e:
            logger.error(f"[分镜脚本] 异常: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_scenes(story_content, scene_count)

    def _generate_style_guide(self, story_content: str) -> Dict[str, str]:
        """生成视觉风格指南"""
        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.dashscope_api_key

            prompt = f"""分析以下故事内容，生成一个统一的视觉风格指南。

故事内容：
{story_content}

请用JSON格式返回，包含：
{{
    "character_description": "人物描述 - 详细描述人物的外貌、服装、表情特征，必须适用于所有分镜",
    "color_scheme": "色彩方案 - 描述整体色调和色彩搭配",
    "lighting_style": "光线风格 - 描述主光线处理方式",
    "scene_setting": "场景设定 - 描述环境的整体风格",
    "art_style": "艺术风格 - 如电影感、写实、插画等",
    "visual_mood": "视觉氛围 - 描述整体的情绪和氛围"
}}"""

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个专业的视觉风格设计师。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=1000
            )

            if response.status_code == 200 and response.output and response.output.choices:
                result_text = response.output.choices[0].message.content
                try:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}')
                    if json_start != -1 and json_end != -1:
                        json_str = result_text[json_start:json_end+1]
                        return json.loads(json_str)
                except:
                    pass

            return self._get_default_style_guide()

        except Exception as e:
            logger.error(f"生成风格指南失败: {e}")
            return self._get_default_style_guide()

    def _generate_storyboard_images(
        self,
        scenes: List[Dict],
        style_guide: Dict[str, str],
        output_dir: str
    ) -> List[Dict]:
        """生成分镜图图片 - 使用 qwen-image-2.0 模型"""
        try:
            import dashscope
            from dashscope import MultiModalConversation

            dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
            dashscope.api_key = self.dashscope_api_key

            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"[图片生成] 输出目录: {output_dir}")

            reference_image_path = None

            for scene in scenes:
                scene_num = scene['scene_number']
                logger.info(f"[图片生成] 场景 {scene_num} 开始...")

                prompt = self._build_image_prompt(scene, style_guide)
                logger.info(f"[图片生成] 场景 {scene_num} prompt: {prompt[:100]}...")

                if scene_num == 1:
                    image_url = self._call_qwen_image_v2_first_frame(prompt)
                    logger.info(f"[图片生成] 场景 {scene_num} API返回: {image_url}")

                    if image_url:
                        image_path = self._save_image_url_to_file(image_url, output_dir, scene_num)
                        scene['image'] = image_path
                        scene['image_generation_success'] = image_path is not None
                        if image_path:
                            reference_image_path = image_path
                            logger.info(f"[图片生成] 场景 {scene_num} 成功: {image_path}")
                        else:
                            logger.error(f"[图片生成] 场景 {scene_num} 保存失败")
                    else:
                        scene['image'] = None
                        scene['image_generation_success'] = False
                        logger.error(f"[图片生成] 场景 {scene_num} API失败")
                else:
                    if not reference_image_path:
                        logger.error(f"[图片生成] 场景 {scene_num} 无参考图，跳过")
                        scene['image'] = None
                        scene['image_generation_success'] = False
                        continue

                    image_url = self._call_qwen_image_v2_with_ref(prompt, reference_image_path)
                    logger.info(f"[图片生成] 场景 {scene_num} API返回: {image_url}")

                    if image_url:
                        image_path = self._save_image_url_to_file(image_url, output_dir, scene_num)
                        scene['image'] = image_path
                        scene['image_generation_success'] = image_path is not None
                        logger.info(f"[图片生成] 场景 {scene_num} 结果: {image_path}")
                    else:
                        scene['image'] = None
                        scene['image_generation_success'] = False
                        logger.error(f"[图片生成] 场景 {scene_num} 失败")

            success_count = sum(1 for s in scenes if s.get('image_generation_success'))
            logger.info(f"[图片生成] 完成: {success_count}/{len(scenes)} 成功")

            return scenes

        except Exception as e:
            logger.error(f"[图片生成] 异常: {e}")
            import traceback
            traceback.print_exc()
            return scenes

    def _call_qwen_image_v2_first_frame(self, prompt: str) -> Optional[str]:
        """调用 qwen-image-2.0 生成首帧（文生图）"""
        try:
            import dashscope
            from dashscope import MultiModalConversation

            # 清理可能的敏感词
            clean_prompt = self._clean_prompt(prompt)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"text": clean_prompt}
                    ]
                }
            ]

            response = MultiModalConversation.call(
                api_key=dashscope.api_key,
                model="qwen-image-2.0",
                messages=messages,
                result_format='message',
                stream=False,
                n=1,
                watermark=False
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list) and len(content) > 0:
                    img_url = content[0].get('image') if isinstance(content[0], dict) else None
                    if img_url:
                        return img_url

            logger.error(f"qwen-image-2.0 首帧生成失败: {response.status_code} - {getattr(response, 'message', response)}")
            return None

        except Exception as e:
            logger.error(f"qwen-image-2.0 首帧异常: {e}")
            return None

    def _call_qwen_image_v2_with_ref(self, prompt: str, reference_image_path: str) -> Optional[str]:
        """调用 qwen-image-2.0 生成后续帧（参考图生图）"""
        try:
            import dashscope
            from dashscope import MultiModalConversation

            ref_url = f"file://{os.path.abspath(reference_image_path)}"

            instructions = """【重要说明】
这张参考图仅用于：
1. 保持人物的外貌、服装、表情特征完全一致
2. 保持整体的艺术风格、色调、光线风格一致
3. 保持整体的视觉氛围一致

但是，你必须：
1. 根据【场景情节】和【画面描述】生成完全不同的场景画面
2. 人物的动作、姿态、位置要根据情节变化
3. 背景环境要根据情节变化
4. 不要复制参考图的具体画面，只借用人物和风格！

请根据以下要求生成图片：
"""

            full_prompt = instructions + "\n\n" + prompt
            clean_prompt = self._clean_prompt(full_prompt)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": ref_url},
                        {"text": clean_prompt}
                    ]
                }
            ]

            response = MultiModalConversation.call(
                api_key=dashscope.api_key,
                model="qwen-image-2.0",
                messages=messages,
                result_format='message',
                stream=False,
                n=1,
                watermark=False
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list) and len(content) > 0:
                    img_url = content[0].get('image') if isinstance(content[0], dict) else None
                    if img_url:
                        return img_url

            logger.error(f"qwen-image-2.0 参考图生成失败: {response.status_code} - {getattr(response, 'message', response)}")
            return None

        except Exception as e:
            logger.error(f"qwen-image-2.0 参考图异常: {e}")
            return None

    def _clean_prompt(self, prompt: str) -> str:
        """清理 prompt 中的敏感词"""
        # 移除可能的敏感词
        sensitive_words = ['暴力', '血腥', '色情', '裸体', '性感', '杀人', '死亡']
        clean = prompt
        for word in sensitive_words:
            clean = clean.replace(word, '')
        return clean[:1500]  # 增加长度限制

    def _save_image_url_to_file(self, image_url: str, output_dir: str, scene_num: int) -> Optional[str]:
        """保存图片URL到文件"""
        try:
            import requests

            if image_url.startswith('file://'):
                import shutil
                local_path = image_url[7:]
                if os.path.exists(local_path):
                    output_path = os.path.join(output_dir, f"scene_{scene_num:02d}.png")
                    shutil.copy(local_path, output_path)
                    return output_path
                return None

            response = requests.get(image_url, timeout=30)
            if response.status_code == 200:
                output_path = os.path.join(output_dir, f"scene_{scene_num:02d}.png")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return output_path

            logger.error(f"图片下载失败: HTTP {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"保存图片异常: {e}")
            return None

    def _build_image_prompt(self, scene: Dict, style_guide: Dict[str, str]) -> str:
        """构建分镜图提示词 - 强调场景情节，保持人物风格一致"""
        scene_description = scene.get('description', '')
        scene_plot = scene.get('plot', '')
        scene_dialogue = scene.get('dialogue', '')
        shot_type = scene.get('shot_type', '')
        
        character = style_guide.get('character_description', '')
        color = style_guide.get('color_scheme', '')
        lighting = style_guide.get('lighting_style', '')
        art_style = style_guide.get('art_style', '')
        scene_setting = style_guide.get('scene_setting', '')

        prompt_parts = []
        
        if scene_plot:
            prompt_parts.append(f"【场景情节】{scene_plot}")
        
        if scene_description:
            prompt_parts.append(f"【画面描述】{scene_description}")
        
        if scene_dialogue:
            prompt_parts.append(f"【人物台词】{scene_dialogue}")
        
        if shot_type:
            prompt_parts.append(f"【镜头类型】{shot_type}")
        
        if character:
            prompt_parts.append(f"【人物设定】{character}")
        
        if scene_setting:
            prompt_parts.append(f"【环境设定】{scene_setting}")
        
        if art_style:
            prompt_parts.append(f"【艺术风格】{art_style}")
        
        if color:
            prompt_parts.append(f"【色调】{color}")
        
        if lighting:
            prompt_parts.append(f"【光线】{lighting}")

        prompt = "\n".join(prompt_parts)
        
        return prompt[:800]

    def _save_image(self, image_data, output_dir: str, scene_num: int) -> str:
        """保存图片"""
        try:
            import requests

            image_path = os.path.join(output_dir, f"scene_{scene_num:02d}.png")

            if isinstance(image_data, dict) and image_data.get('url'):
                url = image_data['url']
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    return image_path
            elif hasattr(image_data, 'url'):
                url = image_data.url
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    with open(image_path, 'wb') as f:
                        f.write(response.content)
                    return image_path

            return None

        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None

    def _parse_scenes_from_response(self, response_text: str, scene_count: int) -> List[Dict]:
        """解析场景数据"""
        try:
            # 尝试找到JSON数组
            json_start = response_text.find('[')
            json_end = response_text.rfind(']')

            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end+1]
                scenes_data = json.loads(json_str)

                if isinstance(scenes_data, list):
                    scenes = []
                    for idx, scene in enumerate(scenes_data[:scene_count]):
                        if not isinstance(scene, dict):
                            continue
                        scenes.append({
                            'scene_number': scene.get('scene_number', idx + 1),
                            'shot_type': scene.get('shot_type', ''),
                            'description': scene.get('description', f'场景{idx+1}'),
                            'plot': scene.get('plot', ''),
                            'dialogue': scene.get('dialogue', ''),
                            'prompt': scene.get('prompt', ''),
                            'duration': scene.get('duration', 4)
                        })
                    return scenes

            # 尝试解析为对象
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')

            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end+1]
                data = json.loads(json_str)

                if 'scenes' in data and isinstance(data['scenes'], list):
                    scenes = []
                    for idx, scene in enumerate(data['scenes'][:scene_count]):
                        if not isinstance(scene, dict):
                            continue
                        scenes.append({
                            'scene_number': scene.get('scene_number', idx + 1),
                            'shot_type': scene.get('shot_type', ''),
                            'description': scene.get('description', f'场景{idx+1}'),
                            'plot': scene.get('plot', ''),
                            'dialogue': scene.get('dialogue', ''),
                            'prompt': scene.get('prompt', ''),
                            'duration': scene.get('duration', 4)
                        })
                    return scenes

            return []

        except Exception as e:
            logger.error(f"解析场景数据失败: {e}")
            return []

    def _generate_fallback_scenes(self, story_content: str, scene_count: int) -> List[Dict]:
        """生成备用场景 - 基于故事内容生成"""
        import dashscope
        from dashscope import Generation
        dashscope.api_key = self.dashscope_api_key

        prompt = f"""故事内容：
{story_content[:1000]}

请把这个故事分成{scene_count}个场景，给出每个场景的核心内容（不用JSON格式，直接返回文字）：

格式：
场景1 [镜头类型]：画面描述 - 情节 - 台词
场景2 [镜头类型]：画面描述 - 情节 - 台词
..."""

        try:
            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {"role": "system", "content": "你是一个分镜设计师，生成简洁真实的分镜内容。"},
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.7,
                max_tokens=1500
            )

            if response.status_code == 200:
                content = response.output.choices[0].message.content
                logger.info(f"[Fallback] 生成分镜内容: {content[:200]}...")

            scenes = []
            shot_types = ['大全景', '中景', '近景', '特写', '双人镜头', '远景']
            for i in range(scene_count):
                scenes.append({
                    'scene_number': i + 1,
                    'shot_type': shot_types[i % len(shot_types)],
                    'description': f'基于故事内容生成的实际画面描述，描述第{i+1}个场景',
                    'plot': f'这是故事的第{i+1}个情节段落',
                    'dialogue': f'第{i+1}个场景的人物对话',
                    'prompt': story_content[:300] if len(story_content) > 300 else story_content,
                    'duration': 4
                })
            return scenes

        except Exception as e:
            logger.error(f"[Fallback] 备用方案也失败: {e}")
            scenes = []
            for i in range(scene_count):
                scenes.append({
                    'scene_number': i + 1,
                    'shot_type': '中景',
                    'description': f'场景{i+1}的画面描述',
                    'plot': f'情节{i+1}描述',
                    'dialogue': f'台词{i+1}',
                    'prompt': story_content[:200],
                    'duration': 4
                })
            return scenes

    def _get_default_style_guide(self) -> Dict[str, str]:
        """获取默认风格指南"""
        return {
            "character_description": "一位年轻亚洲女性，长发，休闲服装，自然表情",
            "color_scheme": "温暖的棕色调，柔和光线",
            "lighting_style": "自然散射光，温暖舒适",
            "scene_setting": "现代都市风格，简洁背景",
            "art_style": "电影感写实风格",
            "visual_mood": "温馨、自然、真实"
        }
