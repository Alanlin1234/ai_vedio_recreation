#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内容生成服务
提供文本到语音等内容生成功能
"""

from .text_to_speech_service import TextToSpeechService

# ContentGenerationService 是 TextToSpeechService 的别名
# 为了保持向后兼容性
ContentGenerationService = TextToSpeechService

__all__ = ['ContentGenerationService']
