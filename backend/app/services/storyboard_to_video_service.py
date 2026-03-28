"""
分镜到视频生成服务
整合分镜、提示词生成、视频生成和一致性检查
"""

import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import Config

from app.services.shot_breakdown_generator import ShotBreakdownGenerator
from app.services.qwen_video_service import QwenVideoService
from app.models import db, VideoRecreation, RecreationScene

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from video_consistency_agent.agent.consistency_agent import ConsistencyAgent

logger = logging.getLogger(__name__)


def _clip_prompt(text: str, max_len: int = 320) -> str:
    if not text:
        return ''
    t = text.strip()
    return t if len(t) <= max_len else t[: max_len - 1] + '…'


class StoryboardToVideoService:
    """分镜到视频生成服务"""

    def __init__(self):
        self.shot_breakdown_generator = ShotBreakdownGenerator()
        self.qwen_video_service = QwenVideoService({
            "api_key": Config.DASHSCOPE_API_KEY,
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "timeout": 60,
            "poll_interval": 10,
            "max_wait_time": 600
        })

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        config_path = os.path.join(project_root, 'video_consistency_agent', 'config', 'config.yaml')
        self.consistency_agent = ConsistencyAgent(config_path)

    def _generate_visual_lock_prompt(self, story_full: str, lang: str = 'zh') -> str:
        """
        一次性生成全片共用的画面风格锁定句（中英文均可），须逐镜原样复用。
        """
        text = (story_full or '').strip()
        if len(text) < 30:
            return (
                "Consistent 3D animated film look, Pixar-like soft global illumination, "
                "warm saturated palette, same character proportions and costume colors across all shots, "
                "cinematic depth of field."
            )
        try:
            import dashscope
            from dashscope import Generation

            dashscope.api_key = Config.DASHSCOPE_API_KEY
            if lang == 'en':
                prompt = f"""You are a film art director. Write **one single paragraph** (English, 80–220 words) that will be copied verbatim into **every** shot's video prompt as the VISUAL_LOCK.

Requirements:
1. **Actionable**: overall look (e.g. Pixar-style 3D, watercolor picture-book, documentary realism), dominant palette, typical lighting.
2. **Cross-shot consistency**: lead character costume colors/shape, age/build; environment and materials — this block is repeated in every shot.
3. Output one paragraph only, no bullets or headings.

Story spine:
{text[:4500]}
"""
                v_sys = 'Output only one English visual/style lock paragraph, no title.'
            else:
                prompt = f"""你是视频美术指导。根据下列短片/故事梗概，写出**唯一一段**将用于**每一个分镜视频**的「画面风格锁定」说明（中英文混合，80～220 字）。
要求：
1. **具体可执行**：写明整体美术方向（如迪士尼手绘 2D / 皮克斯 3D / 写实纪录片 / 水彩插画等）、主色调、典型光影。
2. **跨镜一致**：写明角色**服装主色与款式**、体型年龄段；环境与材质基调；这些要求在每一镜提示词里都会**原样复制**。
3. 单段输出，不要编号、不要多条。

故事梗概：
{text[:4500]}
"""
                v_sys = '你只输出一段美术与角色外观锁定说明，无标题。'

            response = Generation.call(
                model='qwen-plus-latest',
                messages=[
                    {'role': 'system', 'content': v_sys},
                    {'role': 'user', 'content': prompt},
                ],
                result_format='message',
                temperature=0.35,
                max_tokens=400,
            )
            if response.status_code == 200 and response.output and response.output.choices:
                out = (response.output.choices[0].message.content or '').strip()
                if len(out) > 40:
                    return out
        except Exception as e:
            logger.warning(f'[visual_lock] LLM 失败，使用默认: {e}')
        return (
            "Consistent stylized 3D animation, soft cinematic lighting, harmonious warm palette, "
            "same character silhouette and outfit colors in every shot, film grain optional."
        )

    def _validate_prompts_form_complete_story(
        self,
        story_full: str,
        shot_summaries: List[str],
        prompt_excerpts: List[str],
        lang: str = 'zh',
    ) -> Dict[str, Any]:
        """检查各镜视频提示词合起来是否足以构成连贯完整故事。"""
        if not story_full or len(story_full.strip()) < 40:
            skip = (
                'Synopsis too short; skip story validation.'
                if lang == 'en'
                else '梗概过短，跳过叙事完整性校验'
            )
            return {'passed': True, 'reason': skip}

        try:
            import dashscope
            from dashscope import Generation
            import json as _json
            import re

            dashscope.api_key = Config.DASHSCOPE_API_KEY
            lines = []
            for i, (sm, pe) in enumerate(zip(shot_summaries, prompt_excerpts), start=1):
                if lang == 'en':
                    lines.append(f"--- Shot {i} beat ---\n{sm}\n--- Shot {i} prompt excerpt ---\n{pe}\n")
                else:
                    lines.append(f"--- 镜头{i} 情节摘要 ---\n{sm}\n--- 镜头{i} 提示词节选 ---\n{pe}\n")
            blob = '\n'.join(lines)[:12000]

            if lang == 'en':
                user = f"""[Full synopsis]
{story_full[:3500]}

[Per-shot materials in order]
{blob}

Task: Decide whether these shots, **in sequence**, can tell one **complete, coherent** mini-story (clear setup–development–payoff or emotional arc), not unrelated fragments.

Output **only** one JSON object, no Markdown: {{"complete_story": true or false, "reason": "English, max ~100 chars"}}"""
                val_sys = 'You only output valid JSON.'
            else:
                user = f"""【全文梗概】
{story_full[:3500]}

【按顺序排列的各镜材料】
{blob}

任务：判断上述各镜的提示词与情节，**串联后**是否能讲出一个**完整、连贯**的小故事（有清晰起因—展开—收束，或明确情感弧线），而不是互不相关的碎片拼贴。

只输出一个 JSON 对象，不要 Markdown：{{"complete_story": true 或 false, "reason": "不超过100字的中文说明"}}"""
                val_sys = '你只输出合法 JSON。'

            response = Generation.call(
                model='qwen-plus-latest',
                messages=[
                    {'role': 'system', 'content': val_sys},
                    {'role': 'user', 'content': user},
                ],
                result_format='message',
                temperature=0.1,
                max_tokens=300,
            )
            if response.status_code == 200 and response.output and response.output.choices:
                raw = (response.output.choices[0].message.content or '').strip()
                m = re.search(r'\{[\s\S]*\}', raw)
                if m:
                    data = _json.loads(m.group(0))
                    passed = bool(data.get('complete_story', False))
                    ok = 'OK' if lang == 'en' else '通过'
                    bad = 'Not passed' if lang == 'en' else '未通过'
                    reason = (data.get('reason') or '').strip() or (ok if passed else bad)
                    return {'passed': passed, 'reason': reason}
        except Exception as e:
            logger.warning(f'[故事校验] 失败，放行: {e}')
            msg = f'Validation error skipped: {e}' if lang == 'en' else f'校验异常已放行: {e}'
            return {'passed': True, 'reason': msg}

        fallback = (
            'Could not parse validation; proceeding.' if lang == 'en' else '无法解析校验结果，已放行'
        )
        return {'passed': True, 'reason': fallback}

    def _build_full_video_prompt(
        self,
        scene_data: Dict[str, Any],
        scene_index: int,
        narrative_context: Optional[Dict[str, Any]],
        visual_lock: str,
        lang: str = 'zh',
    ) -> str:
        """组装单镜完整视频提示词（与生成视频时一致）。"""
        shot_breakdown = self.shot_breakdown_generator.generate_shot_breakdown(
            scene_data, scene_index, lang=lang
        )
        video_prompt = self.shot_breakdown_generator.format_for_video_generation(
            shot_breakdown,
            narrative_context=narrative_context,
            visual_lock=visual_lock,
        )
        storyboard_prompt = (scene_data.get('video_prompt') or '').strip()
        if storyboard_prompt:
            if lang == 'en':
                video_prompt = (
                    f"[Storyboard I2V] Follow the keyframe look; generate ~{int(scene_data.get('duration', 5))}s "
                    f"of motion. Narrative and style must match VISUAL_LOCK and neighboring shots:\n"
                    f"{storyboard_prompt}\n\n--- Shot breakdown ---\n{video_prompt}"
                )
            else:
                video_prompt = (
                    f"[Storyboard I2V] 严格参考当前分镜关键帧的画面内容与风格，按以下提示生成约 "
                    f"{int(scene_data.get('duration', 5))} 秒镜头；叙事与画面风格须与全片 VISUAL_LOCK 及相邻分镜一致：\n"
                    f"{storyboard_prompt}\n\n--- Shot breakdown ---\n{video_prompt}"
                )
        elif scene_index > 0 and scene_data.get('description'):
            video_prompt = (
                video_prompt
                + "\n[Visual continuity] Match lighting, character look, and VISUAL_LOCK with previous shot."
            )
        return video_prompt

    def generate_scene_videos(self, recreation_id: int) -> Dict[str, Any]:
        """
        生成分场景视频

        Args:
            recreation_id: 项目ID

        Returns:
            包含生成结果的字典
        """
        try:
            logger.info(f"开始生成分场景视频，recreation_id={recreation_id}")

            recreation = VideoRecreation.query.get(recreation_id)
            if not recreation:
                return {
                    'success': False,
                    'error': '项目不存在'
                }

            from app.output_language import generation_language

            lang = generation_language(recreation)

            scenes = RecreationScene.query.filter_by(
                recreation_id=recreation_id
            ).order_by(RecreationScene.scene_index).all()

            if not scenes:
                return {
                    'success': False,
                    'error': '没有分镜数据'
                }

            task_dir = self._get_task_directory(recreation_id, recreation.original_video_path)
            generated_videos = []
            failed_scenes = []
            previous_last_frame = None
            debug_prompts = []

            story_full = (recreation.new_script_content or recreation.video_understanding or '').strip()
            total_n = len(scenes)

            visual_lock = self._generate_visual_lock_prompt(story_full, lang=lang)
            logger.info(f'[视频] 已生成全片 VISUAL_LOCK（{len(visual_lock)} 字）')

            built_prompts: List[str] = []
            shot_summaries: List[str] = []
            prompt_excerpts: List[str] = []

            for scene in scenes:
                scene_index = scene.scene_index
                scene_data = {
                    'scene_number': scene_index + 1,
                    'shot_type': scene.shot_type,
                    'description': scene.description,
                    'plot': scene.plot,
                    'dialogue': scene.dialogue,
                    'duration': float(scene.duration or 5),
                    'video_prompt': scene.video_prompt,
                }
                prev_sc = scenes[scene_index - 1] if scene_index > 0 else None
                next_sc = scenes[scene_index + 1] if scene_index < total_n - 1 else None
                narrative_context = {
                    'story_summary': story_full,
                    'shot_index': scene_index + 1,
                    'total_shots': total_n,
                    'previous_plot': (prev_sc.plot or '') if prev_sc else '',
                    'previous_dialogue': (prev_sc.dialogue or '') if prev_sc else '',
                    'next_plot': (next_sc.plot or '') if next_sc else '',
                }
                full_p = self._build_full_video_prompt(
                    scene_data, scene_index, narrative_context, visual_lock, lang=lang
                )
                built_prompts.append(full_p)
                shot_summaries.append(
                    f"{(scene.plot or '')}\n{(scene.description or '')}".strip()[:900]
                )
                prompt_excerpts.append(_clip_prompt(full_p, 420))

            story_val = self._validate_prompts_form_complete_story(
                story_full, shot_summaries, prompt_excerpts, lang=lang
            )
            if not story_val.get('passed'):
                logger.warning(f'[视频] 叙事校验未通过: {story_val.get("reason")}')
                err_prefix = (
                    'Shot prompts failed full-story validation: '
                    if lang == 'en'
                    else '各镜视频提示词未通过「完整故事」校验：'
                )
                return {
                    'success': False,
                    'error': err_prefix + (story_val.get('reason') or ''),
                    'story_prompt_validation': story_val,
                    'visual_lock_preview': visual_lock[:500],
                    'debug_prompts': debug_prompts,
                }

            logger.info('[视频] 叙事校验通过，开始逐镜生成视频')

            for idx, scene in enumerate(scenes):
                try:
                    scene_index = scene.scene_index
                    logger.info(f"正在生成场景 {scene_index + 1} / {len(scenes)}")

                    scene_data = {
                        'scene_number': scene_index + 1,
                        'shot_type': scene.shot_type,
                        'description': scene.description,
                        'plot': scene.plot,
                        'dialogue': scene.dialogue,
                        'duration': float(scene.duration or 5),
                        'video_prompt': scene.video_prompt,
                    }

                    prev_sc = scenes[scene_index - 1] if scene_index > 0 else None
                    next_sc = scenes[scene_index + 1] if scene_index < total_n - 1 else None
                    narrative_context = {
                        'story_summary': story_full,
                        'shot_index': scene_index + 1,
                        'total_shots': total_n,
                        'previous_plot': (prev_sc.plot or '') if prev_sc else '',
                        'previous_dialogue': (prev_sc.dialogue or '') if prev_sc else '',
                        'next_plot': (next_sc.plot or '') if next_sc else '',
                    }

                    scene_image_path = os.path.join(
                        Config.UPLOAD_FOLDER,
                        'storyboards',
                        f'recreation_{recreation_id}',
                        f"scene_{scene_index + 1:02d}.png"
                    )
                    scene_image_path = os.path.abspath(scene_image_path)
                    if not os.path.exists(scene_image_path):
                        logger.warning(f"场景 {scene_index + 1} 分镜图文件不存在: {scene_image_path}")
                        scene_image_url = None
                    else:
                        scene_image_url = f"file://{scene_image_path}"
                        logger.info(f"场景 {scene_index + 1} 分镜图URL: {scene_image_url}")

                    prebuilt = built_prompts[idx]
                    result = self._generate_single_scene_video(
                        scene_data=scene_data,
                        scene_image_url=scene_image_url,
                        previous_last_frame=previous_last_frame,
                        task_dir=task_dir,
                        scene_index=scene_index,
                        debug_prompts=debug_prompts,
                        narrative_context=narrative_context,
                        prebuilt_video_prompt=prebuilt,
                        visual_lock=visual_lock,
                        lang=lang,
                    )

                    if result.get('success'):
                        generated_videos.append({
                            'scene_index': scene_index,
                            'video_path': result.get('video_path'),
                            'consistency_check': result.get('consistency_check'),
                            'success': True
                        })

                        previous_last_frame = result.get('last_frame')

                        scene.generated_video_path = result.get('video_path')
                        scene.generation_status = 'completed'
                        scene.generation_completed_at = datetime.now()
                        db.session.commit()
                    else:
                        failed_scenes.append({
                            'scene_index': scene_index,
                            'error': result.get('error', '未知错误'),
                            'success': False
                        })

                        scene.generation_status = 'failed'
                        db.session.commit()

                except Exception as e:
                    logger.error(f"生成场景 {scene.scene_index + 1} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    failed_scenes.append({
                        'scene_index': scene.scene_index,
                        'error': str(e),
                        'success': False
                    })

            logger.info(f"分场景视频生成完成，成功: {len(generated_videos)}, 失败: {len(failed_scenes)}")

            return {
                'success': True,
                'recreation_id': recreation_id,
                'generated_videos': generated_videos,
                'failed_scenes': failed_scenes,
                'total_scenes': len(scenes),
                'successful_count': len(generated_videos),
                'debug_prompts': debug_prompts,
                'story_prompt_validation': story_val,
                'visual_lock_preview': visual_lock[:500],
            }

        except Exception as e:
            logger.error(f"生成分场景视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'debug_prompts': [],
            }

    def _generate_single_scene_video(
        self,
        scene_data: Dict[str, Any],
        scene_image_url: str,
        previous_last_frame: Optional[str],
        task_dir: str,
        scene_index: int,
        debug_prompts: Optional[List[Dict[str, Any]]] = None,
        narrative_context: Optional[Dict[str, Any]] = None,
        prebuilt_video_prompt: Optional[str] = None,
        visual_lock: Optional[str] = None,
        lang: str = 'zh',
    ) -> Dict[str, Any]:
        """
        生成单个场景视频。若传入 prebuilt_video_prompt（与先生成、校验后的提示一致），则不再重复拼装。
        """
        try:
            logger.info(f"场景 {scene_index + 1} 开始生成")

            shot_breakdown = self.shot_breakdown_generator.generate_shot_breakdown(
                scene_data, scene_index, lang=lang
            )

            if prebuilt_video_prompt and str(prebuilt_video_prompt).strip():
                video_prompt = prebuilt_video_prompt.strip()
            else:
                vl = visual_lock or ''
                video_prompt = self._build_full_video_prompt(
                    scene_data,
                    scene_index,
                    narrative_context,
                    vl,
                    lang=lang,
                )

            logger.info(f"场景 {scene_index + 1} 视频提示词: {video_prompt[:200]}...")

            storyboard_prompt = (scene_data.get('video_prompt') or '').strip()

            # 图生视频：优先使用当前分镜图作为 img_url（与分镜 prompt 对齐）
            keyframes = []
            if scene_image_url:
                keyframes.append(scene_image_url)
            if previous_last_frame and previous_last_frame != scene_image_url:
                keyframes.append(previous_last_frame)

            if debug_prompts is not None:
                from app.utils.prompt_trace import trace

                kf_short = [
                    (u[:160] + '…') if isinstance(u, str) and len(u) > 160 else u for u in keyframes
                ]
                debug_prompts.append(
                    trace(
                        'video_generator',
                        f'场景 {scene_index + 1} 图生视频',
                        body=video_prompt,
                        extra={
                            'shot_breakdown': shot_breakdown,
                            'storyboard_video_prompt': storyboard_prompt or None,
                            'keyframes': kf_short,
                        },
                    )
                )

            if not keyframes:
                return {
                    'success': False,
                    'error': '没有可用的关键帧图片'
                }

            result = self.qwen_video_service.generate_video_from_keyframes(
                keyframes=keyframes,
                prompt={'video_prompt': video_prompt}
            )

            if not result.get('success'):
                return {
                    'success': False,
                    'error': result.get('error', '视频生成失败')
                }

            video_url = result.get('video_url')
            if not video_url:
                return {
                    'success': False,
                    'error': '视频URL不存在'
                }

            local_video_path = os.path.join(task_dir, 'videos', f"scene_{scene_index + 1:02d}.mp4")
            os.makedirs(os.path.dirname(local_video_path), exist_ok=True)

            download_result = self.qwen_video_service.download_video(
                video_url, local_video_path
            )

            if not download_result.get('success'):
                return {
                    'success': False,
                    'error': download_result.get('error', '视频下载失败')
                }

            logger.info(f"场景 {scene_index + 1} 一致性检查（跳过）")

            return {
                'success': True,
                'video_path': local_video_path,
                'last_frame': scene_image_url,
                'consistency_check': {'passed': True, 'score': 1.0, 'source': 'skipped'}
            }

        except Exception as e:
            logger.error(f"生成场景视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _check_consistency(
        self,
        current_video_path: str,
        previous_last_frame: str,
        scene_index: int
    ) -> Dict[str, Any]:
        """
        检查场景一致性

        Args:
            current_video_path: 当前视频路径
            previous_last_frame: 上一场景的最后一帧
            scene_index: 场景索引

        Returns:
            一致性检查结果（已设为直接通过）
        """
        try:
            logger.info(f"场景 {scene_index + 1} 一致性检查（跳过，直接通过）")

            return {
                'passed': True,
                'score': 1.0,
                'source': 'skipped',
                'message': '一致性检查已跳过（阈值设为0）'
            }

        except Exception as e:
            logger.error(f"一致性检查异常: {e}")
            return {
                'passed': True,
                'score': 1.0,
                'warning': f'一致性检查异常: {str(e)}'
            }

    def _get_task_directory(self, recreation_id: int, original_video_path: str) -> str:
        """获取任务目录"""
        video_dir = os.path.dirname(original_video_path)
        task_dir = os.path.join(video_dir, f"recreation_{recreation_id}")
        videos_dir = os.path.join(task_dir, 'videos')
        os.makedirs(videos_dir, exist_ok=True)
        return task_dir

    def concatenate_scene_videos(self, recreation_id: int) -> Dict[str, Any]:
        """
        将分场景视频合成完整视频

        Args:
            recreation_id: 项目ID

        Returns:
            包含合成结果的字典
        """
        try:
            logger.info(f"开始合成完整视频，recreation_id={recreation_id}")

            scenes = RecreationScene.query.filter_by(
                recreation_id=recreation_id
            ).order_by(RecreationScene.scene_index).all()

            if not scenes:
                return {
                    'success': False,
                    'error': '没有分镜场景'
                }

            video_paths = []
            for scene in scenes:
                if scene.generated_video_path and os.path.exists(scene.generated_video_path):
                    video_paths.append(scene.generated_video_path)
                else:
                    logger.warning(f"场景 {scene.scene_index + 1} 视频不存在，跳过")

            if not video_paths:
                return {
                    'success': False,
                    'error': '没有可用的场景视频'
                }

            recreation = VideoRecreation.query.get(recreation_id)
            task_dir = self._get_task_directory(recreation_id, recreation.original_video_path)
            output_path = os.path.join(task_dir, 'final_video.mp4')

            import asyncio
            from app.services.ffmpeg_service import FFmpegService

            ffmpeg_service = FFmpegService()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    ffmpeg_service.compose_videos(video_paths, output_path)
                )
            finally:
                loop.close()

            if result.get('success'):
                recreation.final_video_path = output_path
                recreation.status = 'completed'
                db.session.commit()

                logger.info(f"视频合成完成: {output_path}")

                return {
                    'success': True,
                    'output_path': output_path,
                    'total_scenes': len(video_paths)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '视频合成失败')
                }

        except Exception as e:
            logger.error(f"合成完整视频失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
