"""
高效视频分析：先通过多模态模型理解视频，再调用 EnhancedVideoAnalyzer 提炼亮点与教育意义。
供 frontend_pipeline `/analyze-video` 使用。
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 教育意义摘要略放宽，避免一句话被截断在关键处（仍偏短，适合列表展示）
_BRIEF_MAX = 220
_POINT_MAX = 140
_POINTS_CAP = 3


def _flatten_educational_for_api(educational_raw: Any) -> tuple[str, List[str]]:
    """将教育意义转为简短摘要 + 分点列表，避免整段 JSON 字符串展示。"""
    points: List[str] = []

    def _clip(s: str, n: int = _POINT_MAX) -> str:
        s = (s or '').strip()
        if not s:
            return ''
        return s[: n - 1] + '…' if len(s) > n else s

    def _add_point(prefix: str, text: str) -> None:
        if text and len(points) < _POINTS_CAP:
            points.append(f'{prefix}{text}')

    if educational_raw is None:
        return ('暂无教育意义描述', points)
    if isinstance(educational_raw, str):
        s = educational_raw.strip()
        if not s:
            return ('暂无教育意义描述', points)
        return (s[:_BRIEF_MAX] + ('…' if len(s) > _BRIEF_MAX else ''), points)
    if not isinstance(educational_raw, dict):
        return (str(educational_raw)[:_BRIEF_MAX], points)

    inner = educational_raw.get('educational')
    if not isinstance(inner, dict):
        inner = educational_raw

    summary_line = (educational_raw.get('summary') or '').strip()
    brief = (inner.get('overall_educational_value') or summary_line or '').strip()

    me = inner.get('moral_education') or {}
    if isinstance(me, dict):
        d = _clip(me.get('description') or '')
        if d:
            _add_point('品德：', d)
        elif isinstance(me.get('values'), list) and me['values']:
            _add_point('品德：', '、'.join(str(x) for x in me['values'][:4]))

    kt = inner.get('knowledge_transfer') or {}
    if isinstance(kt, dict):
        d = _clip(kt.get('description') or '')
        if d:
            _add_point('知识：', d)
        elif isinstance(kt.get('learning_points'), list) and kt['learning_points']:
            _add_point('学习要点：', '、'.join(str(x) for x in kt['learning_points'][:3]))

    vs = inner.get('value_shaping') or {}
    if isinstance(vs, dict):
        d = _clip(vs.get('description') or vs.get('positive_model') or '')
        if d:
            _add_point('价值观：', d)

    lw = inner.get('life_wisdom') or {}
    if isinstance(lw, dict):
        d = _clip(lw.get('description') or '')
        if d:
            _add_point('生活智慧：', d)

    age = inner.get('age_appropriateness') or {}
    if isinstance(age, dict):
        sa = (age.get('suitable_ages') or '').strip()
        if sa:
            _add_point('适龄：', _clip(sa, 80))

    bd = inner.get('behavior_demonstration') or {}
    if isinstance(bd, dict) and len(points) < _POINTS_CAP:
        les = (bd.get('lessons') or '').strip()
        if les:
            _add_point('行为启示：', _clip(les, 100))

    if not brief:
        brief = summary_line or '暂无教育意义描述'
    if len(brief) > _BRIEF_MAX:
        brief = brief[: _BRIEF_MAX - 1] + '…'

    # 若维度未凑够要点，用综合句拆成 2～3 条（用户侧只关心最核心几条）
    if len(points) < 2 and brief and brief != '暂无教育意义描述':
        extra = _split_core_sentences(brief, max_n=max(0, _POINTS_CAP - len(points)))
        for line in extra:
            if len(points) >= _POINTS_CAP:
                break
            if line and line not in points:
                points.append(line)

    return (brief[:_BRIEF_MAX], points[:_POINTS_CAP])


def _split_core_sentences(text: str, max_n: int = 3) -> List[str]:
    """把一段综合表述按句号拆成若干短句，作补充要点。"""
    if not text or max_n <= 0:
        return []
    chunks = re.split(r'(?<=[。！？])\s*', text.strip())
    out: List[str] = []
    for c in chunks:
        c = c.strip()
        if len(c) < 12:
            continue
        if len(c) > _POINT_MAX:
            c = c[: _POINT_MAX - 1] + '…'
        out.append(c)
        if len(out) >= max_n:
            break
    return out


def _extract_quoted_field_from_repr_blob(s: str, field: str) -> str:
    """从误存的 str(dict) 文本里尽量抽出某字段的字符串值（单/双引号）。"""
    if not s or field not in s:
        return ''
    # 'field': '...' 或 "field": "..."
    pat_single = rf"['\"]{re.escape(field)}['\"]\s*:\s*'((?:[^'\\]|\\.)*)'"
    m = re.search(pat_single, s, re.DOTALL)
    if m:
        return m.group(1).replace("\\'", "'").replace('\\"', '"')
    pat_double = rf"['\"]{re.escape(field)}['\"]\s*:\s*\"((?:[^\"\\]|\\.)*)\""
    m = re.search(pat_double, s, re.DOTALL)
    if m:
        return m.group(1).replace('\\"', '"')
    return ''


def _extract_educational_from_repr_blob(s: str) -> tuple[str, List[str]]:
    """
    literal_eval 失败时（超长引号、转义异常等）：从 repr 文本中抽 summary / overall，
    再拆成 2～3 条核心要点。
    """
    blob = s.strip()
    overall = _extract_quoted_field_from_repr_blob(blob, 'overall_educational_value').strip()
    summary = _extract_quoted_field_from_repr_blob(blob, 'summary').strip()
    text = overall or summary
    if not text:
        m = re.search(r"'description'\s*:\s*'((?:[^'\\]|\\.){15,800})'", blob, re.DOTALL)
        if m:
            text = m.group(1).replace("\\'", "'")
    if not text:
        return ('暂无教育意义描述', [])
    text = text.replace('\\n', ' ')
    brief = text[:_BRIEF_MAX] + ('…' if len(text) > _BRIEF_MAX else '')
    points = _split_core_sentences(text, max_n=_POINTS_CAP)
    if len(points) < 2:
        parts = [p.strip() for p in re.split(r'[；;]\s*', text) if len(p.strip()) >= 12]
        for p in parts:
            if len(points) >= _POINTS_CAP:
                break
            if p not in points:
                pp = p[:_POINT_MAX] + ('…' if len(p) > _POINT_MAX else '')
                points.append(pp)
    if not points and text:
        points = [text[:_POINT_MAX] + ('…' if len(text) > _POINT_MAX else '')]
    return (brief, points[:_POINTS_CAP])


def normalize_educational_for_api_response(
    value: Any,
    educational_points: Optional[List[str]] = None,
) -> tuple[str, List[str]]:
    """
    接口出口统一处理：保证 educational_meaning 为短纯文本，educational_points 为列表。
    兼容 dict、以及历史上误用 str(dict) 存入的整段 repr 字符串。
    """
    pts: List[str] = list(educational_points) if educational_points else []
    if isinstance(value, dict):
        b, p = _flatten_educational_for_api(value)
        return (b, p if p else pts)

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ('暂无教育意义描述', pts)
        # 历史问题：整段 Python dict 被 str() 后展示成「JSON」
        if s.startswith('{') and ("'educational'" in s or '"educational"' in s) and len(s) < 80000:
            parsed_dict: Optional[Dict[str, Any]] = None
            try:
                import ast

                parsed = ast.literal_eval(s)
                if isinstance(parsed, dict):
                    parsed_dict = parsed
            except (ValueError, SyntaxError, MemoryError):
                pass
            if parsed_dict is None:
                try:
                    import json

                    parsed = json.loads(s)
                    if isinstance(parsed, dict):
                        parsed_dict = parsed
                except (json.JSONDecodeError, ValueError):
                    pass
            if parsed_dict is not None:
                return _flatten_educational_for_api(parsed_dict)
            bb, pp = _extract_educational_from_repr_blob(s)
            if bb != '暂无教育意义描述' or pp:
                return (bb, pp[:_POINTS_CAP] if pp else pts)
        if len(s) > _BRIEF_MAX:
            s = s[: _BRIEF_MAX - 1] + '…'
        return (s, pts)

    b, p = _flatten_educational_for_api(value)
    return (b, p if p else pts)


def _dashscope_key() -> str:
    try:
        from config import Config

        return getattr(Config, 'DASHSCOPE_API_KEY', '') or os.environ.get('DASHSCOPE_API_KEY', '')
    except Exception:
        return os.environ.get('DASHSCOPE_API_KEY', '')


def _understand_video_with_qwen_vl(
    video_path: str, debug_prompts: Optional[List[Dict[str, Any]]] = None
) -> str:
    """使用 DashScope 多模态模型理解本地视频，返回中文长文本描述。"""
    import dashscope

    from app.utils.prompt_trace import trace

    api_key = _dashscope_key()
    if not api_key:
        raise RuntimeError('未配置 DASHSCOPE_API_KEY')

    dashscope.api_key = api_key
    abs_path = os.path.abspath(video_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(abs_path)

    from dashscope import MultiModalConversation

    user_text = (
        '请详细观看并概括该视频：1）主要情节（谁、做了什么、结果）；2）人物与场景；'
        '3）画面风格与节奏；4）你觉得好看的片段。用中文分段输出，语言通俗、少堆砌形容词，便于后续改编。'
    )
    if debug_prompts is not None:
        debug_prompts.append(
            trace(
                'education_expert',
                '多模态视频理解',
                user=user_text,
                model='qwen-vl-plus',
                extra={'video_file': os.path.basename(abs_path)},
            )
        )

    video_uri = f'file://{abs_path}'
    messages = [
        {
            'role': 'user',
            'content': [
                {'video': video_uri},
                {'text': user_text},
            ],
        }
    ]

    rsp = MultiModalConversation.call(
        model='qwen-vl-plus',
        messages=messages,
        result_format='message',
    )
    if rsp.status_code != 200:
        raise RuntimeError(getattr(rsp, 'message', None) or f'API错误 {rsp.status_code}')

    text_parts = []
    if rsp.output and rsp.output.choices:
        msg = rsp.output.choices[0].message
        content = getattr(msg, 'content', None) or []
        if isinstance(content, str):
            text_parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('text'):
                    text_parts.append(block['text'])
    out = '\n'.join(text_parts).strip()
    if not out:
        raise RuntimeError('模型未返回文本内容')
    return out


class EfficientVideoAnalyzerWithHighlights:
    """
    与 pipeline 约定：`analyze_video_complete(video_path=...)` 返回 dict，
    含 success、content、highlights、educational_meaning、keyframes_count、time_cost、transcription。
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or _dashscope_key()

    async def analyze_video_complete(self, video_path: str) -> Dict[str, Any]:
        t0 = time.time()
        debug_prompts: List[Dict[str, Any]] = []
        try:
            raw_content = _understand_video_with_qwen_vl(video_path, debug_prompts)
        except Exception as e:
            logger.exception('视频多模态理解失败: %s', e)
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'highlights': '',
                'educational_meaning': '',
                'educational_points': [],
                'keyframes_count': 0,
                'time_cost': round(time.time() - t0, 2),
                'transcription': '',
                'debug_prompts': debug_prompts,
            }

        try:
            from app.services.enhanced_video_analyzer import EnhancedVideoAnalyzer

            inner = EnhancedVideoAnalyzer(api_key=self.api_key).analyze_video_complete(
                video_path,
                {'content': raw_content},
                debug_prompts=debug_prompts,
            )
        except Exception as e:
            logger.exception('EnhancedVideoAnalyzer 失败，仅使用原始理解文本: %s', e)
            inner = {'success': True}

        elapsed = round(time.time() - t0, 2)

        if inner.get('success'):
            highlights = inner.get('highlights')
            educational_raw = inner.get('educational_meaning')
            if isinstance(highlights, dict):
                highlights = highlights.get('summary') or str(highlights)
            educational_brief, educational_points = _flatten_educational_for_api(educational_raw)
            story = inner.get('story_content') or raw_content
            return {
                'success': True,
                'content': story,
                'highlights': highlights or '暂无亮点描述',
                'educational_meaning': educational_brief or '暂无教育意义描述',
                'educational_points': educational_points,
                'keyframes_count': 0,
                'time_cost': elapsed,
                'transcription': inner.get('structured_summary', '') or '',
                'debug_prompts': debug_prompts,
            }

        return {
            'success': True,
            'content': raw_content,
            'highlights': '暂无亮点描述',
            'educational_meaning': '暂无教育意义描述',
            'educational_points': [],
            'keyframes_count': 0,
            'time_cost': elapsed,
            'transcription': '',
            'debug_prompts': debug_prompts,
        }
