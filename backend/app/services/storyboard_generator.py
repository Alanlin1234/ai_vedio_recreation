"""
分镜图生成集成服务
整合分镜脚本生成和图像生成，确保极高的一致性
"""

import os
import sys
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

# 每个分镜对应成片时长（秒），与视频生成、剪辑节奏一致
SHOT_DURATION_SECONDS = 5
# 分镜数量：偏精简，按故事节拍划分（硬上限防止出现十几镜）
MIN_SCENES = 3
MAX_SCENES = 6

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

logger = logging.getLogger(__name__)


class StoryboardGenerator:
    """分镜图生成器 - 同时生成文字脚本和图片"""

    def __init__(self):
        self.dashscope_api_key = Config.DASHSCOPE_API_KEY

    def _non_human_primary_cast(
        self,
        story_content: str,
        scenes: List[Dict],
        style_guide: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        是否为动物/拟人动物为主角。此类若用「首帧参考图」做图生图，模型极易把后续镜画成真人，
        因此检测到后改为**每镜独立文生图**（仅画风文字约束跨镜一致）。
        """
        blob = (story_content or '')[:12000]
        if style_guide:
            blob += ' ' + (style_guide.get('character_description') or '')
        for s in scenes[: min(8, len(scenes))]:
            blob += ' ' + (s.get('visual_subject') or '') + ' ' + (s.get('description') or '')
        low = blob.lower()
        en = (
            'kitten',
            'kitty',
            'puppy',
            'bunny',
            'rabbit',
            'anthropomorphic',
            'furry',
            'whisker',
            'paws',
            'meow',
            'bark',
        )
        if any(x in low for x in en):
            return True
        zh = (
            '小猫',
            '猫咪',
            '狗子',
            '小狗',
            '兔子',
            '兔爷爷',
            '兔',
            '拟人',
            '动物主角',
            '童话',
            '毛绒',
            '虎斑',
            '喵',
            '汪',
            '爪',
            '兽耳',
            '猫科',
        )
        return any(z in blob for z in zh)

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

任务：在**尽量少**的前提下，估算需要多少个「分镜镜头」——宁少勿滥，**按故事实际转折点**划分，禁止为凑数拆镜。
硬性规则：
- 每个镜头对应约 {SHOT_DURATION_SECONDS} 秒成片，一个镜头只承载**一个**清晰节拍（一段连续动作或一两句关键对白）。
- **短剧本（约千字内）优先 3～4 个镜头**；中等长度 4～6；**不得超过 {MAX_SCENES}**。
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

        # 启发式：偏保守，长文也不强行加镜
        n = max(MIN_SCENES, min(MAX_SCENES, len(text) // 900 + 2))
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
            else:
                scene_count = max(MIN_SCENES, min(MAX_SCENES, int(scene_count)))

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

            # 硬性截断，防止模型多返回镜数或历史逻辑异常
            if len(scenes) > scene_count:
                logger.warning(f'[分镜] 解析得到 {len(scenes)} 镜，按上限截断为 {scene_count}')
                scenes = scenes[:scene_count]
            for i, s in enumerate(scenes):
                s['scene_number'] = i + 1

            logger.info(f"分镜脚本生成成功，共{len(scenes)}个场景")

            for s in scenes:
                s['duration'] = float(SHOT_DURATION_SECONDS)

            # 第二步：生成视觉风格指南
            style_guide = self._generate_style_guide(story_content, debug_prompts)
            # 动物/童话主角：覆盖风格指南里可能误导为真人的描述，避免配图跑偏
            if self._non_human_primary_cast(story_content, scenes, style_guide):
                v0 = (scenes[0].get('visual_subject') or '').strip()
                style_guide['character_description'] = (
                    f"全片为动物或拟人动物故事，禁止人类、真人、真人儿童。"
                    f"主角外观必须与剧本一致：{v0 or '见各分镜 visual_subject'}。"
                )
            logger.info(f"视觉风格指南: {json.dumps(style_guide, ensure_ascii=False)}")

            # 第三步：生成图片（如果需要）
            if generate_images and output_dir:
                scenes_with_images = self._generate_storyboard_images(
                    scenes=scenes,
                    style_guide=style_guide,
                    output_dir=output_dir,
                    debug_prompts=debug_prompts,
                    story_content=story_content,
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

            prompt = f"""根据以下故事内容，生成**正好 {scene_count} 个**分镜场景。每个分镜对应约 {SHOT_DURATION_SECONDS} 秒成片，**必须写满这 {SHOT_DURATION_SECONDS} 秒内**发生的事（情节推进、动作、镜头、语言）。

故事内容：
{story_content[:8000]}

硬性要求：
1. 分镜数量必须正好 {scene_count} 个，**严格按时间顺序**串联成**同一部短片的连续镜头**，覆盖起承转合，**禁止**跳过关键因果、**禁止**场景乱跳（若换场须写清过渡逻辑）。
2. **物种与人物一致**：先通读剧本，确定出现的角色是**人类 / 动物 / 拟人动物**等。`visual_subject`、`description`、`plot` 必须**同一套角色**，禁止 plot 写「兔爷爷」而 description 写年轻女性；禁止跨镜无故换人换物种。
3. **visual_subject**：每一镜单独一行，写清**本镜画面中必须出现的主体**（物种、年龄感、服装或毛色特征），与剧本一致。
4. **plot（情节节拍）**：用 **至少 3 句、建议 4～6 句中文**，按时间顺序写满本 {SHOT_DURATION_SECONDS} 秒内：开场画面 → 中间动作与冲突 → 镜头结束时的结果；**第 2 镜起**须承接上一镜；禁止一句话敷衍。
5. **action_in_shot**：本 {SHOT_DURATION_SECONDS} 秒内**可见的具体动作**（走位、手势、物体运动），须与 `description` 可画内容一致。
6. **camera_movement**：本 {SHOT_DURATION_SECONDS} 秒内**镜头怎么动**（固定/推/拉/摇/移/跟拍/升降等）及与上一镜的衔接；可与 `shot_type` 呼应。
7. **description（画面）**：写清构图、主体位置、环境、光影；须能直接用于作画，且与 `visual_subject`、物种设定一致。
8. **dialogue（台词）**：**必填**。每镜至少一句：角色对白、内心独白或「旁白：…」；动物童话可写拟人台词。**禁止**空字符串、「无」「暂无」「暂无台词」；若本镜纯动作，写「小满：（内心）……」或「（环境音：风声）」二选一。
9. **shot_type**：具体景别（如大远景俯角、中景侧拍、特写），相邻镜头尽量避免完全重复同一景别+同构图。
10. `prompt`（图生视频）：英文或中英混合，含动作与镜头变化，可加 "Story beat:" / "Camera:" 便于视频模型理解衔接。
11. 每个场景 `duration` 必须为 {SHOT_DURATION_SECONDS}。

JSON格式（直接返回 JSON 数组，不要其他文字；键名必须齐全）：
[{{"scene_number":1,"shot_type":"景别","visual_subject":"本镜画面必须出现的主体","description":"画面","action_in_shot":"本5秒内动作","camera_movement":"本5秒内镜头运动","plot":"情节节拍","dialogue":"台词或旁白","prompt":"图生视频提示词","duration":{SHOT_DURATION_SECONDS}}}]"""

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                debug_prompts.append(
                    trace(
                        'storyboard',
                        '分镜脚本（JSON）',
                        system='你是电影分镜师。物种与画面一致；镜间承接；每镜约5秒含动作与镜头；台词必填。',
                        user=prompt,
                        model='qwen-plus-latest',
                    )
                )

            response = Generation.call(
                model="qwen-plus-latest",
                messages=[
                    {
                        "role": "system",
                        "content": "你是电影分镜师。分镜须物种与画面一致、连成完整故事、镜间有因果承接；每镜写满约5秒内的动作与镜头；台词必填；视频提示词须体现叙事衔接。"
                    },
                    {"role": "user", "content": prompt}
                ],
                result_format='message',
                temperature=0.55,
                max_tokens=8000,
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

            prompt = f"""分析以下故事内容，生成一个统一的视觉风格指南（用于系列分镜画风一致）。

故事内容：
{story_content}

重要：**character_description 必须与故事中出现的角色物种一致**——若故事是童话/拟人动物，须写「拟人化兔子/狐狸」等具体物种与服饰特征；**禁止**在剧本未写人类时默认成「年轻女性/真人」。若多角色，用简短列表概括共同画风下的外观差异。

请用JSON格式返回，包含：
{{
    "character_description": "跨镜一致的角色外观：物种、年龄感、服装或毛色、标志性道具（须与原文一致，不得臆造人类替代动物）",
    "color_scheme": "色彩方案 - 描述整体色调和色彩搭配",
    "lighting_style": "光线风格 - 描述主光线处理方式",
    "scene_setting": "场景设定 - 描述环境的整体风格",
    "art_style": "艺术风格 - 如电影感、绘本插画、3D动画等",
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
                    {
                        "role": "system",
                        "content": "你是视觉风格设计师。物种与剧本一致，禁止用默认真人替代故事中的动物或拟人角色。",
                    },
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

    def _generate_ref_storyboard_image_task(
        self,
        scene: Dict[str, Any],
        first_frame_ref_path: str,
        output_dir: str,
        style_guide: Dict[str, str],
    ) -> Dict[str, Any]:
        """单张「首帧参考」分镜图（供线程池并行调用）。不在此写 debug_prompts。"""
        scene_num = int(scene['scene_number'])
        prompt = self._build_image_prompt(scene, style_guide, use_compact_style=True)
        ref_instructions = """【qwen-image-edit 任务说明】
参考图为**第 1 个分镜**成图：请在其基础上做「编辑式生成」——**保留**同一主角物种、毛色/服装与整体画风；**按下方文字**改变景别、机位、动作、背景与情节瞬间。

【必须】
1. 画面内容严格符合下方【本镜情节】【画面描述】【景别】与「本镜主体」，表现本镜独有动作与构图。
2. 与参考图相比须有明显差异（不同镜头、不同动作），禁止仅裁剪或微调。
3. 物种与角色身份须与参考图一致（同一故事主角），除非下方文字明确要求新角色登场。
4. 画面中不得出现任何文字、字幕、标牌、水印、Logo。

请根据以下要求编辑生成新画面：
"""
        full_prompt = ref_instructions + "\n\n" + prompt
        image_url = self._call_qwen_image_edit_with_ref(
            full_prompt, first_frame_ref_path, scene_index=scene_num, raw_prompt=True
        )
        if not image_url:
            logger.warning(f'[分镜图] 场景{scene_num} qwen-image-edit 失败，回退 qwen-image-2.0 参考图')
            image_url = self._call_qwen_image_v2_with_ref(
                full_prompt, first_frame_ref_path, scene_index=scene_num, raw_prompt=True
            )
        image_path = None
        if image_url:
            image_path = self._save_image_url_to_file(image_url, output_dir, scene_num)
        return {
            'scene_number': scene_num,
            'image_prompt_base': prompt,
            'image_prompt_full': full_prompt,
            'image_path': image_path,
            'image_generation_success': image_path is not None,
        }

    def _generate_storyboard_images(
        self,
        scenes: List[Dict],
        style_guide: Dict[str, str],
        output_dir: str,
        debug_prompts: Optional[List[Dict[str, Any]]] = None,
        story_content: str = '',
    ) -> List[Dict]:
        """生成分镜图图片 - 使用 qwen-image-2.0；动物主角时全程文生图，人类主角时首帧+参考图。"""
        try:
            import dashscope
            from dashscope import MultiModalConversation

            dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
            dashscope.api_key = self.dashscope_api_key

            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"[图片生成] 输出目录: {output_dir}")

            first_frame_ref_path: Optional[str] = None

            for scene in scenes:
                scene_num = int(scene['scene_number'])
                if scene_num != 1:
                    continue
                logger.info(f"[图片生成] 场景 {scene_num} 开始（文生首帧）...")

                prompt = self._build_image_prompt(
                    scene, style_guide, use_compact_style=False
                )
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
                            first_frame_ref_path = image_path
                            logger.info(f"[图片生成] 场景 {scene_num} 成功: {image_path}")
                        else:
                            logger.error(f"[图片生成] 场景 {scene_num} 保存失败")
                    else:
                        scene['image'] = None
                        scene['image_generation_success'] = False
                        logger.error(f"[图片生成] 场景 {scene_num} API失败")

            # 第 2 镜起：以第 1 张为参考，并行生成（同步提交、多线程调用 API）
            remaining = [s for s in scenes if int(s.get('scene_number', 0)) > 1]
            if first_frame_ref_path and remaining:
                max_workers = min(6, len(remaining))
                logger.info(
                    f"[图片生成] 首帧已就绪，{len(remaining)} 张并行（qwen-image-edit，参考首帧；失败则回退 qwen-image-2.0）"
                )
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_map = {
                        executor.submit(
                            self._generate_ref_storyboard_image_task,
                            sc,
                            first_frame_ref_path,
                            output_dir,
                            style_guide,
                        ): sc
                        for sc in remaining
                    }
                    for fut in as_completed(future_map):
                        sc = future_map[fut]
                        sn = int(sc.get('scene_number', 0))
                        try:
                            res = fut.result()
                        except Exception as e:
                            logger.exception(f"[图片生成] 场景 {sn} 并行任务异常: {e}")
                            for s in scenes:
                                if int(s.get('scene_number', 0)) == sn:
                                    s['image'] = None
                                    s['image_generation_success'] = False
                            continue
                        for s in scenes:
                            if int(s.get('scene_number', 0)) != res['scene_number']:
                                continue
                            s['image_prompt_base'] = res.get('image_prompt_base')
                            s['image_prompt_full'] = res.get('image_prompt_full')
                            s['image'] = res.get('image_path')
                            s['image_generation_success'] = bool(res.get('image_generation_success'))
                            logger.info(
                                f"[图片生成] 场景 {res['scene_number']} 并行结果: "
                                f"{'OK' if res.get('image_path') else '失败'}"
                            )
                            if debug_prompts is not None:
                                from app.utils.prompt_trace import trace

                                debug_prompts.append(
                                    trace(
                                        'storyboard',
                                        f"分镜图 场景{res['scene_number']}（qwen-image-edit·并行）",
                                        user=res.get('image_prompt_full') or '',
                                        model='qwen-image-edit',
                                        extra={
                                            'mode': 'image_edit',
                                            'reference_first_frame': True,
                                            'parallel': True,
                                        },
                                    )
                                )
                            break
            elif remaining and not first_frame_ref_path:
                for sc in remaining:
                    sn = int(sc.get('scene_number', 0))
                    logger.error(f"[图片生成] 场景 {sn} 无首帧参考图，跳过")
                    for s in scenes:
                        if int(s.get('scene_number', 0)) == sn:
                            s['image'] = None
                            s['image_generation_success'] = False

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

    def _call_qwen_image_edit_with_ref(
        self,
        prompt: str,
        reference_image_path: str,
        scene_index: int = 0,
        raw_prompt: bool = True,
    ) -> Optional[str]:
        """第 2 镜起：qwen-image-edit，以首张分镜图为参考，按本镜情节编辑生成。"""
        try:
            import dashscope
            from dashscope import MultiModalConversation

            dashscope.api_key = self.dashscope_api_key
            ref_url = f"file://{os.path.abspath(reference_image_path)}"

            if raw_prompt:
                full_prompt = prompt
            else:
                full_prompt = (
                    f"【基于参考图编辑生成第 {scene_index} 镜】保留画风与主角外观，按下列描述改变构图与动作。\n\n"
                    + prompt
                )
            clean_prompt = self._clean_prompt(full_prompt)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": ref_url},
                        {"text": clean_prompt},
                    ],
                }
            ]

            response = MultiModalConversation.call(
                api_key=dashscope.api_key,
                model="qwen-image-edit",
                messages=messages,
                result_format="message",
                stream=False,
                watermark=False,
                prompt_extend=True,
                negative_prompt="",
                size="1328*1328",
            )

            if response.status_code != 200:
                logger.error(
                    f"qwen-image-edit 失败: {response.status_code} - {getattr(response, 'message', response)}"
                )
                return None

            if not response.output or not response.output.choices:
                return None
            content = response.output.choices[0].message.content
            if not isinstance(content, list):
                return None
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("image"):
                    return item["image"]
                imgs = item.get("images")
                if isinstance(imgs, list) and imgs:
                    return imgs[0]
            return None

        except Exception as e:
            logger.error(f"qwen-image-edit 异常: {e}")
            return None

    def _call_qwen_image_v2_with_ref(
        self,
        prompt: str,
        reference_image_path: str,
        scene_index: int = 0,
        raw_prompt: bool = False,
    ) -> Optional[str]:
        """调用 qwen-image-2.0：参考**首张分镜图**，锁画风；画面内容以当前 prompt 为准。

        raw_prompt=True 时表示 prompt 已为完整指令（含参考说明），不再前置拼接默认说明。
        """
        try:
            import dashscope
            from dashscope import MultiModalConversation

            ref_url = f"file://{os.path.abspath(reference_image_path)}"

            if raw_prompt:
                full_prompt = prompt
            else:
                instructions = f"""【参考图】为第 1 镜成图，用于统一画风与色调；若本镜情节要求不同角色/物种，以本镜文字为准，不得以首帧替代。
【当前任务】生成第 {scene_index} 镜画面，必须严格按下方情节与画面描述构图，与第 1 镜在景别、动作、背景上明显不同。
禁止：与参考图同构图、仅微调；禁止画面内出现任何文字、字幕、标牌、水印、Logo。

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
        return clean[:2000]

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

    def _build_image_prompt(
        self,
        scene: Dict,
        style_guide: Dict[str, str],
        use_compact_style: bool = False,
        force_animal_no_human: bool = False,
    ) -> str:
        """构建分镜图提示词：先写当前镜叙事与画面，再补风格；禁止出文字。"""
        scene_description = scene.get('description', '')
        scene_plot = scene.get('plot', '')
        scene_dialogue = scene.get('dialogue', '')
        shot_type = scene.get('shot_type', '')
        visual_subject = (scene.get('visual_subject') or '').strip()
        action_in_shot = (scene.get('action_in_shot') or '').strip()
        camera_mv = (scene.get('camera_movement') or '').strip()

        character = style_guide.get('character_description', '')
        color = style_guide.get('color_scheme', '')
        lighting = style_guide.get('lighting_style', '')
        art_style = style_guide.get('art_style', '')
        scene_setting = style_guide.get('scene_setting', '')

        prompt_parts: List[str] = [
            "【纯画面约束】画面中不得出现任何文字、字幕、对话框、标牌、水印、Logo、书法或印刷字；仅视觉呈现。",
        ]
        if force_animal_no_human:
            prompt_parts.append(
                "【物种锁定】禁止出现人类、真人、写实人脸、儿童或成人；仅允许本故事中的动物或拟人动物（直立可穿衣但须保留明显动物头耳尾等特征），与「本镜主体」一致。"
            )
        prompt_parts.append(
            "【图文一致】画面中的物种、人数、服装须与下方「本镜主体」和情节一致，禁止用真人替代剧本中的动物/拟人角色，反之亦然。"
        )

        if visual_subject:
            prompt_parts.append(f"【本镜主体（优先）】{visual_subject[:400]}")
        if scene_plot:
            prompt_parts.append(f"【本镜情节（必须画出来）】{scene_plot}")
        if action_in_shot:
            prompt_parts.append(f"【本镜动作】{action_in_shot[:400]}")
        if camera_mv:
            prompt_parts.append(f"【镜头】{camera_mv[:300]}")
        if scene_description:
            prompt_parts.append(f"【画面描述】{scene_description}")
        if shot_type:
            prompt_parts.append(f"【景别】{shot_type}")
        if scene_dialogue:
            prompt_parts.append(f"【表演/情绪参考（勿在图中写字）】{scene_dialogue}")

        if character:
            prompt_parts.append(
                f"【系列画风与跨镜参考（若与「本镜主体」冲突，以本镜主体与情节为准）】"
                f"{character[:240]}{'…' if len(character) > 240 else ''}"
            )
        if use_compact_style:
            if art_style:
                prompt_parts.append(f"【画风】{art_style[:120]}")
            if scene_setting:
                prompt_parts.append(f"【环境基调】{scene_setting[:120]}")
        else:
            if scene_setting:
                prompt_parts.append(f"【环境设定】{scene_setting}")
            if art_style:
                prompt_parts.append(f"【艺术风格】{art_style}")
            if color:
                prompt_parts.append(f"【色调】{color}")
            if lighting:
                prompt_parts.append(f"【光线】{lighting}")

        prompt = "\n".join(prompt_parts)

        return prompt[:1800]

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

    def _normalize_scene_dict(self, scene: Dict, idx: int, dialogue: str) -> Dict:
        """统一分镜字典字段，便于配图与前端展示。"""
        visual = (scene.get('visual_subject') or '').strip()
        action = (scene.get('action_in_shot') or '').strip()
        camera = (scene.get('camera_movement') or '').strip()
        plot_body = (scene.get('plot') or '').strip()
        plot_lines = []
        if camera:
            plot_lines.append(f'【镜头运动】{camera}')
        if action:
            plot_lines.append(f'【人物/动作】{action}')
        if plot_body:
            plot_lines.append(plot_body)
        plot_merged = '\n'.join(plot_lines) if plot_lines else plot_body

        desc = (scene.get('description') or '').strip()
        if visual and visual not in desc[:80]:
            desc = f'{visual}。{desc}' if desc else visual

        return {
            'scene_number': scene.get('scene_number', idx + 1),
            'shot_type': scene.get('shot_type', ''),
            'visual_subject': visual,
            'description': desc or f'场景{idx + 1}',
            'action_in_shot': action,
            'camera_movement': camera,
            'plot': plot_merged,
            'plot_body': plot_body,
            'dialogue': dialogue,
            'prompt': scene.get('prompt', ''),
            'duration': float(scene.get('duration', SHOT_DURATION_SECONDS) or SHOT_DURATION_SECONDS),
        }

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
                        d = scene.get('dialogue') or scene.get('台词') or scene.get('lines') or ''
                        ds = str(d).strip()
                        if not ds or ds in ('无', '暂无', '暂无台词', 'N/A', 'n/a'):
                            d = '（本镜以动作为主；环境音）'
                        scenes.append(
                            self._normalize_scene_dict(scene, idx, d)
                        )
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
                        d = scene.get('dialogue') or scene.get('台词') or scene.get('lines') or ''
                        ds = str(d).strip()
                        if not ds or ds in ('无', '暂无', '暂无台词', 'N/A', 'n/a'):
                            d = '（本镜以动作为主；环境音）'
                        scenes.append(
                            self._normalize_scene_dict(scene, idx, d)
                        )
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
                    'visual_subject': '',
                    'description': f'基于故事内容生成的实际画面描述，描述第{i+1}个场景',
                    'action_in_shot': '',
                    'camera_movement': '',
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
                    'visual_subject': '',
                    'description': f'场景{i+1}的画面描述',
                    'action_in_shot': '',
                    'camera_movement': '',
                    'plot': f'情节{i+1}描述',
                    'dialogue': f'台词{i+1}',
                    'prompt': story_content[:200],
                    'duration': float(SHOT_DURATION_SECONDS),
                })
            return scenes

    def _get_default_style_guide(self) -> Dict[str, str]:
        """获取默认风格指南（避免臆造「年轻女性」等，以免与童话/动物剧本冲突）"""
        return {
            "character_description": "以剧本中明确写出的角色为准；若未指定物种则中性卡通人物造型，不默认真人写真",
            "color_scheme": "柔和、统一的配色，与场景情绪一致",
            "lighting_style": "自然散射光或柔和的戏剧光",
            "scene_setting": "与故事场景一致的环境",
            "art_style": "统一的手绘插画或电影感画面，全片一致",
            "visual_mood": "与故事基调一致",
        }
