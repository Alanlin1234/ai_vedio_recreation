#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频处理流程测试脚本
通过调用 VideoProcessingPipeline 服务完成完整的视频处理流程
"""
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app import create_app
from app.services.video_processing_pipeline import VideoProcessingPipeline

app = create_app()


def log_callback(step_name: str, status: str, debug_info: str = ""):
    """日志回调函数"""
    if debug_info:
        print(f"[{step_name}] {status} | {debug_info}")
    else:
        print(f"[{step_name}] {status}")


async def main():
    if len(sys.argv) != 2:
        print(f"用法: python {sys.argv[0]} <视频文件路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"错误: 视频文件不存在 - {video_path}")
        sys.exit(1)
    
    config = {
        'slice_count': 5,
        'slice_duration': 5,
        'use_original_keyframes': True,
        'quality_config': {
            'min_resolution': (1280, 720),
            'min_fps': 24,
            'min_bitrate': 1000000
        }
    }
    
    pipeline = VideoProcessingPipeline(config)
    pipeline.set_log_callback(log_callback)
    
    result = await pipeline.run_full_pipeline(video_path)
    
    if result.get('success'):
        print("\n" + "="*50)
        print("视频处理流程完成！")
        print(f"输出目录: {result.get('output_dir')}")
        print(f"生成视频数量: {len(result.get('generated_videos', []))}")
        print("="*50)
    else:
        print("\n视频处理流程完成，但部分步骤可能失败")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
