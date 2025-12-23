

#AI视频生成系统 - 视频生成脚本



import sys
import os
import asyncio
import argparse
from typing import Dict, Any

# 添加backend目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 导入配置和Orchestrator
from config import config
from app.agents.orchestrator import VideoCreationOrchestrator


def parse_arguments() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='AI视频生成脚本')
    
    parser.add_argument('--keywords', nargs='+', required=True,
                      help='视频关键词列表，如："AI 科技 创新"')
    
    parser.add_argument('--style', type=str, default='commentary',
                      choices=['commentary', 'entertainment', 'educational'],
                      help='视频风格')
    
    parser.add_argument('--duration', type=int, default=60,
                      help='视频时长（秒）')
    
    parser.add_argument('--output-filename', type=str, default='output_video.mp4',
                      help='输出视频文件名')
    
    parser.add_argument('--comfyui-url', type=str,
                      default=config.COMFYUI_URL if hasattr(config, 'COMFYUI_URL') else 'http://127.0.0.1:8188',
                      help='ComfyUI访问地址')
    
    parser.add_argument('--output-dir', type=str, default='output/videos',
                      help='视频输出目录')
    
    return parser.parse_args()


async def generate_video(args: argparse.Namespace) -> Dict[str, Any]:
    """生成视频的主要函数"""
    print("=" * 60)
    print("AI视频生成系统 - 开始生成视频")
    print("=" * 60)
    
    try:
        # 初始化Orchestrator
        orchestrator = VideoCreationOrchestrator({
            'comfyui_url': args.comfyui_url,
            'output_dir': args.output_dir
        })
        
        # 准备视频生成参数
        video_params = {
            'keywords': args.keywords,
            'style': args.style,
            'duration': args.duration,
            'output_filename': args.output_filename
        }
        
        print(f"\n[参数配置]")
        print(f"关键词: {', '.join(args.keywords)}")
        print(f"视频风格: {args.style}")
        print(f"视频时长: {args.duration}秒")
        print(f"输出文件名: {args.output_filename}")
        print(f"ComfyUI地址: {args.comfyui_url}")
        print(f"输出目录: {args.output_dir}")
        
        print("\n" + "=" * 60)
        print("开始执行视频生成流程...")
        print("=" * 60)
        
        # 调用Orchestrator生成视频
        result = await orchestrator.create_video(video_params)
        
        print("\n" + "=" * 60)
        print("视频生成流程结束")
        print("=" * 60)
        
        if result['success']:
            print(f"\n✅ 视频生成成功!")
            print(f"📁 输出路径: {result['final_video']}")
            print(f"📊 生成阶段: {', '.join(result['stages'].keys())}")
        else:
            print(f"\n❌ 视频生成失败!")
            print(f"💥 错误信息: {result.get('error', '未知错误')}")
            print(f"📍 失败阶段: {result.get('failed_stage', '未知阶段')}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 视频生成过程中发生异常!")
        print(f"💥 异常信息: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'exception': traceback.format_exc()
        }


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 运行异步视频生成函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(generate_video(args))
    loop.close()
    
    # 根据结果设置退出码
    if result['success']:
        print("\n🎉 视频生成成功，程序正常退出!")
        sys.exit(0)
    else:
        print("\n💥 视频生成失败，程序异常退出!")
        sys.exit(1)


if __name__ == '__main__':
    main()
