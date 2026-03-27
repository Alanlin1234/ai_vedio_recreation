"""
高效视频分析：先通过多模态模型理解视频，再调用 EnhancedVideoAnalyzer 提炼亮点与教育意义。
供 frontend_pipeline `/analyze-video` 使用。
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
        '请详细观看并概括该视频：1）主要情节与叙事；2）人物与场景；'
        '3）画面风格与节奏；4）可能的亮点片段。用中文分段输出，便于后续改编。'
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
            educational = inner.get('educational_meaning')
            if isinstance(highlights, dict):
                highlights = highlights.get('summary') or str(highlights)
            if isinstance(educational, dict):
                educational = str(educational)
            story = inner.get('story_content') or raw_content
            return {
                'success': True,
                'content': story,
                'highlights': highlights or '暂无亮点描述',
                'educational_meaning': educational or '暂无教育意义描述',
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
            'keyframes_count': 0,
            'time_cost': elapsed,
            'transcription': '',
            'debug_prompts': debug_prompts,
        }
