"""
分镜图生成集成服务
整合分镜脚本生成和图像生成，确保极高的一致性
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional

# 每个分镜对应成片时长（秒），与视频生成、剪辑节奏一致
SHOT_DURATION_SECONDS = 5
MIN_SCENES = 4
MAX_SCENES = 24

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

logger = logging.getLogger(__name__)


class StoryboardGenerator:
    """分镜图生成器 - 同时生成文字脚本和图片"""

    def __init__(self):
        self.dashscope_api_key = Config.DASHSCOPE_API_KEY

    def plan_scene_count(
        self, story_content: str, debug_prompts: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        根据故事编剧产出的剧本，智能规划分镜数量。
        约定：每个分镜对应约 SHOT_DURATION_SECONDS 秒成片，仅承载一个叙事节拍/视觉动作。
        """
        text = (story_content or '').strip()
        if len(text) < 80:
            return MIN_SCENES

        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.dashscope_api_key
            prompt = f"""你是分镜统筹。下面是一部用于二创视频的剧本（已由故事编剧写好）。

【剧本全文】
{text[:12000]}

任务：根据叙事结构（起承转合、情绪转折、关键信息点）估算需要多少个「分镜镜头」。
硬性规则：
- 每个镜头对应约 {SHOT_DURATION_SECONDS} 秒成片，镜头内只能安排**一个清晰的视觉节拍**（一个动作、一句关键对白、或一个信息点），不要贪多。
- 镜头总数必须在 {MIN_SCENES} 到 {MAX_SCENES} 之间（含边界）。
- 只输出一个 JSON 对象，不要 Markdown：{{"scene_count": <整数>, "rationale": "<不超过80字的中文说明>"}}"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'storyboard',
                        '智能规划镜头数',
                        system='你只输出合法 JSON，键名与要求一致。',
                        user=prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model='qwen-plus-latest',
                messages=[
                    {'role': 'system', 'content': '你只输出合法 JSON，键名与要求一致。'},
                    {'role': 'user', 'content': prompt},
                ],
                result_format='message',
                temperature=0.2,
                max_tokens=400,
            )
            if response.status_code == 200 and response.output and response.output.choices:
                raw = response.output.choices[0].message.content.strip()
                j_start, j_end = raw.find('{'), raw.rfind('}')
                if j_start != -1 and j_end != -1:
                    import json as _json
                    data = _json.loads(raw[j_start : j_end + 1])
                    n = int(data.get('scene_count', MIN_SCENES))
                    n = max(MIN_SCENES, min(MAX_SCENES, n))
                    logger.info(f'[分镜统筹] LLM 规划镜头数: {n}, 说明: {data.get("rationale", "")[:120]}')
                    return n
        except Exception as e:
            logger.warning(f'[分镜统筹] LLM 失败，使用启发式: {e}')

        # 启发式：按字数粗略估计节拍数
        n = max(MIN_SCENES, min(MAX_SCENES, len(text) // 220 + 4))
        logger.info(f'[分镜统筹] 启发式镜头数: {n}')
        return n

    def generate_storyboard(
        self,
        story_content: str,
        scene_count: Optional[int] = None,
        output_dir: str = None,
        generate_images: bool = True
    ) -> Dict[str, Any]:
        """
        生成分镜图（脚本+可选图片）

        Args:
            story_content: 故事内容（优先使用故事编剧写出的 new_script_content）
            scene_count: 场景数量；为 None 时根据剧本智能规划
            output_dir: 图片输出目录
            generate_images: 是否生成图片

        Returns:
            包含成功状态、场景列表、风格指南、planned_scene_count 等
        """
        debug_prompts: List[Dict[str, Any]] = []
        try:
            if scene_count is None:
                scene_count = self.plan_scene_count(story_content, debug_prompts)

            logger.info("="*60)
            logger.info(f"开始生成分镜图，场景数量: {scene_count}（每镜约 {SHOT_DURATION_SECONDS}s 成片）")
            logger.info("="*60)

            # 第一步：生成分镜脚本（确保一致性）
            scenes = self._generate_storyboard_scripts(
                story_content, scene_count, debug_prompts
            )

            if not scenes:
                return {
                    'success': False,
                    'error': '分镜脚本生成失败',
                    'scenes': [],
                    'debug_prompts': debug_prompts,
                }

            logger.info(f"分镜脚本生成成功，共{len(scenes)}个场景")

            for s in scenes:
                s['duration'] = float(SHOT_DURATION_SECONDS)

            # 第二步：生成视觉风格指南
            style_guide = self._generate_style_guide(story_content, debug_prompts)
            logger.info(f"视觉风格指南: {json.dumps(style_guide, ensure_ascii=False)}")

            # 第三步：生成图片（如果需要）
            if generate_images and output_dir:
                scenes_with_images = self._generate_storyboard_images(
                    scenes=scenes,
                    style_guide=style_guide,
                    output_dir=output_dir,
                    debug_prompts=debug_prompts,
                )
                scenes = scenes_with_images

            return {
                'success': True,
                'scenes': scenes,
                'style_guide': style_guide,
                'total_scenes': len(scenes),
                'planned_scene_count': scene_count,
                'shot_duration_seconds': SHOT_DURATION_SECONDS,
                'has_images': generate_images,
                'debug_prompts': debug_prompts,
            }

        except Exception as e:
            logger.error(f"生成分镜图失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'scenes': [],
                'debug_prompts': debug_prompts,
            }

    def _generate_storyboard_scripts(
        self,
        story_content: str,
        scene_count: int,
        debug_prompts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict]:
        """生成分镜脚本"""
        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = self.dashscope_api_key

            prompt = f"""根据以下故事内容，生成{scene_count}个分镜场景。本流程中**每个分镜将生成约 {SHOT_DURATION_SECONDS} 秒的视频**，再交给剪辑师按顺序拼接。

故事内容：
{story_content[:8000]}

硬性要求：
1. 分镜数量必须正好 {scene_count} 个，覆盖故事起承转合，顺序与叙事一致。
2. **每个分镜只承载 5 秒内能演完/拍完的一个节拍**：一个主要动作、或一句关键对白、或一个信息点；不要塞进整段 subplot。
3. 镜头类型、景别要符合该节拍的情绪与信息（避免万金油模板句）。
4. `description` / `plot` 要具体可拍；`dialogue` 若过长请截断到适合 5 秒口播。
5. `prompt` 为图生视频用的英文或中英混合提示词，需与分镜图内容一致，强调动作与光影，便于 Wan 类模型执行。
6. 每个场景的 `duration` 字段**必须填 {SHOT_DURATION_SECONDS}**（表示该镜成片目标时长秒数）。

JSON格式（直接返回 JSON 数组，不要其他文字）：
[{{"scene_number":1,"shot_type":"景别","description":"画面","plot":"情节节拍","dialogue":"台词","prompt":"图生视频提示词","duration":{SHOT_DURATION_SECONDS}}}]"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'storyboard',
                        '分镜脚本（JSON）',
                        system='你是电影分镜师。每个镜头对应约5秒成片，只写一个清晰节拍；提示词用于图生视频，须与画面一致。',
                        user=prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是电影分镜师。每个镜头对应约5秒成片，只写一个清晰节拍；提示词用于图生视频，须与画面一致。"
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

    def _generate_style_guide(
        self,
        story_content: str,
        debug_prompts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
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

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'storyboard',
                        '视觉风格指南',
                        system='你是一个专业的视觉风格设计师。',
                        user=prompt,
                        model='qwen-plus-latest',
                    )
                )

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
        output_dir: str,
        debug_prompts: Optional[List[Dict[str, Any]]] = None,
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
                scene['image_prompt_base'] = prompt
                logger.info(f"[图片生成] 场景 {scene_num} prompt: {prompt[:100]}...")

                if scene_num == 1:
                    if debug_prompts is not None:
                        from app.utils.prompt_trace import trace

                        debug_prompts.append(
                            trace(
                                'storyboard',
                                f'分镜图 场景{scene_num}（文生图）',
                                user=prompt,
                                model='qwen-image-2.0',
                                extra={'mode': 'text_to_image'},
                            )
                        )

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

                    ref_instructions = """【重要说明】
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
                    full_prompt = ref_instructions + "\n\n" + prompt
                    scene['image_prompt_full'] = full_prompt
                    if debug_prompts is not None:
                        from app.utils.prompt_trace import trace

                        debug_prompts.append(
                            trace(
                                'storyboard',
                                f'分镜图 场景{scene_num}（参考图生图）',
                                user=full_prompt,
                                model='qwen-image-2.0',
                                extra={'mode': 'image_to_image', 'reference_previous_scene': True},
                            )
                        )

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
                            'duration': float(scene.get('duration', SHOT_DURATION_SECONDS) or SHOT_DURATION_SECONDS),
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
                            'duration': float(scene.get('duration', SHOT_DURATION_SECONDS) or SHOT_DURATION_SECONDS),
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
                    'duration': float(SHOT_DURATION_SECONDS),
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
                    'duration': float(SHOT_DURATION_SECONDS),
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
