#!/usr/bin/env python3
"""
视频生成脚本
使用VideoCreationOrchestrator生成视频
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.agents.orchestrator import VideoCreationOrchestrator
from config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/video_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("VideoGenerator")

async def generate_video():
    """生成视频"""
    logger.info("=== 开始视频生成流程 ===")
    
    try:
        # 检查ComfyUI服务状态
        logger.info("检查ComfyUI服务状态...")
        import requests
        try:
            comfyui_response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
            if comfyui_response.status_code != 200:
                logger.warning("ComfyUI服务返回非200状态码: %d", comfyui_response.status_code)
        except requests.exceptions.ConnectionError:
            logger.error("❌ ComfyUI服务未运行，请先启动ComfyUI")
            logger.info("请访问 https://github.com/comfyanonymous/ComfyUI 了解如何启动ComfyUI")
            return False
        except Exception as e:
            logger.error("❌ 检查ComfyUI服务时出错: %s", e)
            return False
        
        # 创建编排器实例
        logger.info("创建视频生成编排器...")
        orchestrator = VideoCreationOrchestrator({
            'comfyui_url': config.COMFYUI_URL,
            'output_dir': 'output/videos',
            'timeout': 300
        })
        
        # 视频生成参数（优化后，降低内存使用）
        video_params = {
            'keywords': ['风景', '旅行', '自然'],
            'hotspot_count': 5,
            'style': 'cinematic',
            'duration': 10,  # 缩短视频时长，减少生成工作量
            'batch_size': 1,
            'retry_failed': True,
            'comfyui_workflow': {
            'width': 1280,  # 降低分辨率，减少内存使用
            'height': 720,   # 降低分辨率，减少内存使用
            'steps': 20,     # 减少采样步骤，降低内存使用
            'cfg_scale': 5.0,
            'fps': 30
        }
        }
        
        logger.info("视频生成参数: %s", video_params)
        logger.info("开始执行视频生成流程...")
        
        # 执行视频生成
        result = await orchestrator.create_video(video_params)
        
        if result['success']:
            logger.info("🎉 视频生成成功！")
            logger.info(f"📁 视频文件: {result.get('final_video')}")
            logger.info(f"🔢 生成阶段数: {len(result.get('stages', {}))}")
            
            # 打印各阶段结果
            for stage, data in result.get('stages', {}).items():
                logger.info(f"   - {stage}: 完成")
            
            return True
        else:
            logger.error("❌ 视频生成失败")
            logger.error(f"   失败阶段: {result.get('failed_stage')}")
            logger.error(f"   错误信息: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error("❌ 视频生成过程中发生异常: %s", e)
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        logger.info("=== 视频生成流程结束 ===")

if __name__ == "__main__":
    logger.info("启动视频生成脚本...")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"当前目录: {os.getcwd()}")
    
    # 检查output目录
    if not os.path.exists('output/videos'):
        os.makedirs('output/videos', exist_ok=True)
        logger.info("创建输出目录: output/videos")
    
    # 运行视频生成
    success = asyncio.run(generate_video())
    
    if success:
        logger.info("视频生成脚本执行成功")
        sys.exit(0)
    else:
        logger.error("视频生成脚本执行失败")
        sys.exit(1)
