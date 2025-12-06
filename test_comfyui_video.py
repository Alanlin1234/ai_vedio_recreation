#!/usr/bin/env python3
"""
测试ComfyUI视频生成功能
直接测试视频生成流程，验证ComfyUI能否正常生成视频
"""

import os
import sys
import asyncio
import logging
import requests
from datetime import datetime

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/test_comfyui_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("TestComfyUIVideo")

async def test_comfyui_video_generation():
    """
    测试ComfyUI视频生成功能
    直接调用VideoCreationOrchestrator生成视频
    """
    logger.info("=== 测试ComfyUI视频生成 ===")
    
    try:
        # 1. 检查ComfyUI服务状态
        logger.info("1. 检查ComfyUI服务状态...")
        try:
            comfyui_response = requests.get("http://127.0.0.1:8188/system_stats", timeout=5)
            if comfyui_response.status_code == 200:
                logger.info("✅ ComfyUI服务正常运行")
            else:
                logger.warning("⚠️ ComfyUI服务返回非200状态码: %d", comfyui_response.status_code)
        except requests.exceptions.ConnectionError:
            logger.error("❌ ComfyUI服务未运行，请先启动ComfyUI")
            logger.info("请访问 https://github.com/comfyanonymous/ComfyUI 了解如何启动ComfyUI")
            return False
        except Exception as e:
            logger.error("❌ 检查ComfyUI服务时出错: %s", e)
            return False
        
        # 2. 导入必要的模块
        logger.info("2. 导入必要的模块...")
        from app.agents.orchestrator import VideoCreationOrchestrator
        from config import config
        
        # 3. 初始化视频生成编排器
        logger.info("3. 初始化视频生成编排器...")
        orchestrator = VideoCreationOrchestrator({
            'comfyui_url': config.COMFYUI_URL,
            'output_dir': 'output/test_videos',
            'timeout': 600  # 增加超时时间，视频生成可能需要较长时间
        })
        
        # 4. 准备测试数据（简化版，跳过热点采集）
        logger.info("4. 准备测试数据...")
        
        # 创建一个简化的测试热点数据
        mock_hotspot = {
            'title': '测试风景视频',
            'description': '一段关于美丽风景的测试视频',
            'category': '风景',
            'view_count': 1000000,
            'comment_count': 5000,
            'share_count': 1000
        }
        
        # 5. 执行视频生成（使用模拟数据）
        logger.info("5. 开始视频生成...")
        logger.info("   风格: cinematic")
        logger.info("   时长: 10秒")
        logger.info("   分辨率: 1920x1080")
        logger.info("   帧率: 30fps")
        
        # 调用视频生成API
        result = await orchestrator.create_video({
            'mock_hotspot': mock_hotspot,  # 使用模拟热点数据，跳过真实的热点采集
            'style': 'cinematic',
            'duration': 10,  # 缩短测试时长
            'batch_size': 1,
            'retry_failed': True,
            'comfyui_workflow': {
                'width': 1920,
                'height': 1080,
                'steps': 30,
                'cfg_scale': 5.0,
                'fps': 30,
                'workflow_type': 'wan21'  # 使用wan21视频生成工作流
            }
        })
        
        # 6. 处理生成结果
        logger.info("6. 处理生成结果...")
        if result['success']:
            logger.info("🎉 视频生成成功！")
            logger.info(f"📁 视频文件: {result.get('final_video')}")
            logger.info(f"🔢 生成阶段数: {len(result.get('stages', {}))}")
            
            # 打印各阶段结果
            for stage, data in result.get('stages', {}).items():
                logger.info(f"   - {stage}: 完成")
            
            # 验证视频文件存在
            final_video_path = result.get('final_video')
            if final_video_path and os.path.exists(final_video_path):
                logger.info("✅ 视频文件已成功生成")
                logger.info(f"   文件大小: {os.path.getsize(final_video_path) / (1024 * 1024):.2f} MB")
                return True
            else:
                logger.error("❌ 视频文件不存在或路径错误")
                return False
        else:
            logger.error("❌ 视频生成失败")
            logger.error(f"   失败阶段: {result.get('failed_stage')}")
            logger.error(f"   错误信息: {result.get('error')}")
            return False
            
    except Exception as e:
        logger.error("❌ 测试过程中发生异常: %s", e)
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        logger.info("=== 测试结束 ===")

if __name__ == "__main__":
    logger.info("启动ComfyUI视频生成测试...")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"当前目录: {os.getcwd()}")
    
    # 检查output目录
    if not os.path.exists('output/test_videos'):
        os.makedirs('output/test_videos', exist_ok=True)
        logger.info("创建测试输出目录: output/test_videos")
    
    # 运行测试
    success = asyncio.run(test_comfyui_video_generation())
    
    if success:
        logger.info("✅ 测试通过")
        sys.exit(0)
    else:
        logger.info("❌ 测试失败")
        sys.exit(1)
