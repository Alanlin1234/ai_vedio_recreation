"""UI / 生成内容语言：请求头 X-Output-Language 与 video_recreations.output_language。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import VideoRecreation


def parse_output_language() -> str:
    """从当前请求读取语言，仅返回 zh 或 en。"""
    from flask import request

    raw = (request.headers.get('X-Output-Language') or 'zh').strip().lower()
    if raw.startswith('en'):
        return 'en'
    return 'zh'


def sync_recreation_output_language_before_analysis(recreation: 'VideoRecreation') -> None:
    """
    在尚未写入 video_understanding 时，用当前请求头覆盖 output_language；
    解析完成后不再改动（由调用方保证仅在 analyze 入口调用）。
    """
    if (recreation.video_understanding or '').strip():
        return
    recreation.output_language = parse_output_language()


def generation_language(recreation: 'VideoRecreation') -> str:
    """流水线生成步骤统一使用项目已锁定语言。"""
    lang = (recreation.output_language or 'zh').strip().lower()
    return 'en' if lang.startswith('en') else 'zh'
