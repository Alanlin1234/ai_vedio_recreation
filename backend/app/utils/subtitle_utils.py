#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕编码处理工具模块
用于处理视频字幕的编码问题，确保中文字幕显示正常
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def ensure_utf8_encoding(text: str) -> str:
    """
    确保文本是UTF-8编码
    
    Args:
        text: 需要检查编码的文本
        
    Returns:
        确保为UTF-8编码的文本
    """
    if not isinstance(text, str):
        return str(text)
    
    try:
        # 尝试编码和解码，确保文本是有效的UTF-8
        return text.encode('utf-8').decode('utf-8')
    except UnicodeError as e:
        logger.error(f"文本编码错误: {str(e)}")
        # 使用错误处理模式
        return text.encode('utf-8', errors='replace').decode('utf-8')

def clean_subtitle_text(text: str) -> str:
    """
    清理字幕文本，去除可能导致编码问题的字符
    
    Args:
        text: 原始字幕文本
        
    Returns:
        清理后的字幕文本
    """
    if not isinstance(text, str):
        return str(text)
    
    # 确保UTF-8编码
    text = ensure_utf8_encoding(text)
    
    # 去除控制字符（除了换行符和制表符）
    cleaned_text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # 去除多余的空白字符
    cleaned_text = ' '.join(cleaned_text.split())
    
    logger.info(f"字幕文本清理完成，原始长度: {len(text)}, 清理后长度: {len(cleaned_text)}")
    
    return cleaned_text

def validate_subtitle_encoding(subtitle_content: str) -> Dict[str, Any]:
    """
    验证字幕编码并返回编码信息
    
    Args:
        subtitle_content: 字幕内容
        
    Returns:
        包含编码验证结果的字典
    """
    result = {
        'valid': True,
        'encoding': 'utf-8',
        'length': len(subtitle_content),
        'has_chinese': any('\u4e00' <= char <= '\u9fff' for char in subtitle_content),
        'error': None
    }
    
    try:
        # 尝试UTF-8解码
        subtitle_content.encode('utf-8').decode('utf-8')
        result['valid'] = True
    except UnicodeError as e:
        result['valid'] = False
        result['error'] = str(e)
        logger.error(f"字幕编码验证失败: {str(e)}")
    
    return result

def prepare_subtitle_prompt(audio_text: str) -> str:
    """
    准备字幕生成提示词，确保编码正确
    
    Args:
        audio_text: 音频转录文本
        
    Returns:
        格式化的字幕提示词
    """
    # 清理音频文本
    cleaned_text = clean_subtitle_text(audio_text)
    
    # 构建字幕提示词
    subtitle_prompt = f"""
[Subtitle Generation]
Based on the following audio content, generate accurate Chinese subtitles:

Audio content:
{cleaned_text}

Requirements:
1. Subtitles must be in Simplified Chinese
2. Use UTF-8 encoding
3. Subtitles should match the audio content exactly
4. Split long sentences into appropriate lines
5. Ensure proper timing and synchronization

[字幕生成]
根据以下音频内容，生成准确的中文字幕：

音频内容：
{cleaned_text}

要求：
1. 字幕必须使用简体中文
2. 使用UTF-8编码
3. 字幕应与音频内容完全匹配
4. 将长句子分成适当的行
5. 确保正确的时间和同步
"""
    
    return subtitle_prompt

def fix_subtitle_encoding_in_video(video_path: str) -> Optional[str]:
    """
    修复视频文件中的字幕编码问题
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        修复后的视频路径，如果修复失败则返回None
    """
    if not os.path.exists(video_path):
        logger.error(f"视频文件不存在: {video_path}")
        return None
    
    try:
        # 这里可以添加使用FFmpeg修复字幕编码的逻辑
        # 例如：提取字幕、修复编码、重新嵌入
        logger.info(f"检查视频文件字幕编码: {video_path}")
        
        # 暂时返回原路径，实际实现需要添加FFmpeg处理逻辑
        return video_path
        
    except Exception as e:
        logger.error(f"修复视频字幕编码失败: {str(e)}")
        return None

if __name__ == "__main__":
    # 测试字幕编码处理功能
    test_text = "这是一段测试文本，包含中文字符和可能的编码问题。This is a test text with Chinese characters."
    
    print("原始文本:")
    print(test_text)
    print()
    
    print("编码检查:")
    validated = validate_subtitle_encoding(test_text)
    print(validated)
    print()
    
    print("清理后文本:")
    cleaned = clean_subtitle_text(test_text)
    print(cleaned)
    print()
    
    print("字幕提示词:")
    prompt = prepare_subtitle_prompt(test_text)
    print(prompt[:200] + "...")