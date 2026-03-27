"""
二创准入审核：结合用户「片子说明」与解析结果，从内容、画风/视听、叙事与二创潜力等维度打分。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from config import Config

logger = logging.getLogger(__name__)

PASS_SCORE = float(getattr(Config, 'RECREATION_REVIEW_PASS_SCORE', 60))


def _weights() -> Tuple[float, float, float, float]:
    """内容、画风/视听、二创叙事潜力、与用户说明契合度"""
    return (0.25, 0.25, 0.25, 0.25)


def _parse_json_block(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _clamp_score(v: Any) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, x))


def review_for_secondary_creation(
    *,
    video_understanding: str,
    highlights: str,
    educational: str,
    creator_notes: str,
) -> Dict[str, Any]:
    """
    返回:
      overall_score, passed, scores{...}, summary, detail (完整结构)
    """
    vu = (video_understanding or '').strip()
    cn = (creator_notes or '').strip()
    hi = (highlights or '').strip() if highlights else ''
    ed = (educational or '').strip() if educational else ''

    if len(vu) < 20:
        return _fail_result('视频理解内容过短，请先完成解析或检查解析是否成功', overall=0.0)

    bad_markers = ['解析失败', '无法识别', '无内容', 'N/A']
    if any(m in vu[:500] for m in bad_markers) and len(vu) < 80:
        return _fail_result('视频理解质量不足，暂无法完成二创审核', overall=15.0)

    llm = _try_llm_review(vu, hi, ed, cn)
    if llm:
        return llm

    return _heuristic_review(vu, hi, ed, cn)


def _fail_result(message: str, overall: float = 0.0) -> Dict[str, Any]:
    scores = {
        'content': overall,
        'visual_style': overall,
        'story_recreation': overall,
        'creator_notes_alignment': overall,
    }
    return {
        'success': True,
        'passed': False,
        'overall_score': round(overall, 1),
        'scores': scores,
        'summary': message,
        'message': message,
        'detail': {'source': 'rule', 'reason': message},
    }


def _try_llm_review(vu: str, hi: str, ed: str, cn: str) -> Optional[Dict[str, Any]]:
    try:
        import dashscope
        from dashscope import Generation

        api_key = getattr(Config, 'DASHSCOPE_API_KEY', None) or getattr(Config, 'LLM_API_KEY', '')
        if not api_key:
            return None

        dashscope.api_key = api_key

        prompt = f"""你是影视二创项目的「审核专员」。用户会上传原始视频并希望做「二创」（改编/重构/续写风格的新视频）。
请根据：①系统对视频的文本理解；②亮点；③教育/主题意义；④用户自己对这部片子的说明（创作意图、想做的二创方向等），从四个维度分别打 0–100 分，并判断是否适合进入二创流程。

【视频内容理解】
{vu[:6000]}

【亮点摘要】
{hi[:2000] if hi else '（无）'}

【主题/教育意义】
{ed[:2000] if ed else '（无）'}

【用户片子说明 / 二创意图】
{cn[:2000] if cn else '（用户未填写）'}

评分维度说明：
- content：内容是否清晰、有信息量、适合作为二创素材（叙事是否可拆解）。
- visual_style：从文字描述中推断的画面风格、节奏、视听潜力（能否支撑统一画风/镜头语言）。
- story_recreation：故事延展与二创潜力（是否有改编空间、是否过于空洞或违规风险高）。
- creator_notes_alignment：用户说明与素材是否契合；若用户未填写，给 45–55 的中性分并简要说明。

只输出一个 JSON 对象，不要 Markdown，不要其它文字：
{{
  "content": <0-100整数>,
  "visual_style": <0-100整数>,
  "story_recreation": <0-100整数>,
  "creator_notes_alignment": <0-100整数>,
  "summary": "<一句中文结论>",
  "suggestions": "<一句改进建议，可空字符串>"
}}"""

        from app.utils.prompt_trace import trace

        dbg = [
            trace(
                'reviewer',
                '二创准入审核',
                system='你只输出合法 JSON，键名与要求完全一致。',
                user=prompt,
                model='qwen-plus-latest',
            )
        ]

        response = Generation.call(
            model='qwen-plus-latest',
            messages=[
                {
                    'role': 'system',
                    'content': '你只输出合法 JSON，键名与要求完全一致。',
                },
                {'role': 'user', 'content': prompt},
            ],
            result_format='message',
            temperature=0.3,
            max_tokens=800,
        )

        if response.status_code != 200 or not response.output or not response.output.choices:
            return None

        raw = response.output.choices[0].message.content
        data = _parse_json_block(raw)
        if not data:
            logger.warning('审核 LLM 返回无法解析 JSON: %s', raw[:300])
            return None

        w = _weights()
        keys = ['content', 'visual_style', 'story_recreation', 'creator_notes_alignment']
        scores = {k: _clamp_score(data.get(k)) for k in keys}
        overall = sum(scores[k] * w[i] for i, k in enumerate(keys))

        summary = (data.get('summary') or '').strip() or '审核完成'
        suggestions = (data.get('suggestions') or '').strip()
        passed = overall >= PASS_SCORE

        message = summary
        if not passed:
            message = f'得分 {overall:.1f}，未达二创准入线（{PASS_SCORE:.0f}）。{summary}'
        else:
            message = f'得分 {overall:.1f}，适合进入二创。{summary}'

        return {
            'success': True,
            'passed': passed,
            'overall_score': round(overall, 1),
            'scores': scores,
            'summary': summary,
            'suggestions': suggestions,
            'message': message,
            'detail': {'source': 'llm', 'raw_scores': data},
            'debug_prompts': dbg,
        }
    except Exception as e:
        logger.exception('LLM 审核失败，回退启发式: %s', e)
        return None


def _heuristic_review(vu: str, hi: str, ed: str, cn: str) -> Dict[str, Any]:
    """无可用大模型时的保守打分。"""
    L = len(vu)
    base_content = min(100.0, 35.0 + min(40.0, L / 80.0))
    base_visual = min(100.0, 40.0 + (10.0 if any(x in vu for x in ['镜头', '画面', '风格', '色调', '光影']) else 0))
    base_story = min(100.0, 38.0 + min(30.0, (len(hi) + len(ed)) / 40.0))
    align = 50.0
    if cn:
        align = min(100.0, 45.0 + min(40.0, len(cn) / 15.0))
    else:
        align = 48.0

    w = _weights()
    keys = ['content', 'visual_style', 'story_recreation', 'creator_notes_alignment']
    scores = {
        'content': round(base_content, 1),
        'visual_style': round(base_visual, 1),
        'story_recreation': round(base_story, 1),
        'creator_notes_alignment': round(align, 1),
    }
    overall = sum(scores[k] * w[i] for i, k in enumerate(keys))
    passed = overall >= PASS_SCORE
    summary = '启发式审核：未调用大模型，结果仅供参考。'
    message = (
        f'得分 {overall:.1f}，{"适合进入二创" if passed else f"未达准入线（{PASS_SCORE:.0f}）"}。{summary}'
    )
    from app.utils.prompt_trace import trace

    return {
        'success': True,
        'passed': passed,
        'overall_score': round(overall, 1),
        'scores': scores,
        'summary': summary,
        'suggestions': '建议配置 DASHSCOPE_API_KEY 以获得更准确的审核。',
        'message': message,
        'detail': {'source': 'heuristic'},
        'debug_prompts': [
            trace(
                'reviewer',
                '启发式审核（未调用大模型）',
                body='基于文本长度与关键词的保守打分，仅作占位。',
            )
        ],
    }
