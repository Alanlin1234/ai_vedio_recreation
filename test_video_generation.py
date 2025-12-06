import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.utils.comfyui_manager import get_comfyui_manager
from config import config

async def test_flux_keyframe_generation():
    """测试Flux关键帧生成"""
    print("=== 测试 Flux 关键帧生成 ===")
    
    try:
        # 获取ComfyUI管理器
        comfyui_manager = get_comfyui_manager({
            'comfyui_url': config.COMFYUI_URL
        })
        
        # 构建测试镜头信息
        test_shot = {
            'prompt': 'a beautiful landscape with mountains and a lake at sunset',
            'shot_id': 1,
            'scene_description': 'A serene mountain landscape with a calm lake reflecting the sunset colors',
            'style_keywords': ['cinematic', 'high quality', 'detailed', 'professional lighting']
        }
        
        # 构建Flux工作流
        flux_workflow = await comfyui_manager.build_workflow(test_shot, workflow_type='flux')
        print(f"✓ Flux工作流构建成功，包含 {len(flux_workflow.get('nodes', []))} 个节点")
        
        # 测试执行（可选，注释掉以避免实际执行）
        # result = await comfyui_manager.execute_workflow(flux_workflow)
        # print(f"✓ Flux工作流执行成功，生成图像URL: {result['image_url']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Flux关键帧生成测试失败: {e}")
        return False

async def test_wan21_video_generation():
    """测试Wan2.1视频生成"""
    print("\n=== 测试 Wan2.1 视频生成 ===")
    
    try:
        # 获取ComfyUI管理器
        comfyui_manager = get_comfyui_manager({
            'comfyui_url': config.COMFYUI_URL
        })
        
        # 构建测试视频信息
        test_video = {
            'prompt': 'a beautiful landscape with mountains and a lake at sunset, with gentle waves on the water',
            'shot_id': 1
        }
        
        # 构建Wan2.1工作流
        wan21_workflow = await comfyui_manager.build_workflow(test_video, workflow_type='wan21')
        print(f"✓ Wan2.1工作流构建成功，包含 {len(wan21_workflow.get('nodes', []))} 个节点")
        
        # 测试执行（可选，注释掉以避免实际执行）
        # result = await comfyui_manager.execute_workflow(wan21_workflow)
        # print(f"✓ Wan2.1工作流执行成功，生成视频URL: {result['image_url']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Wan2.1视频生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("开始测试视频生成功能...")
    
    # 测试Flux关键帧生成
    flux_result = await test_flux_keyframe_generation()
    
    # 测试Wan2.1视频生成
    wan21_result = await test_wan21_video_generation()
    
    print("\n=== 测试结果汇总 ===")
    print(f"Flux关键帧生成: {'✓ 成功' if flux_result else '✗ 失败'}")
    print(f"Wan2.1视频生成: {'✓ 成功' if wan21_result else '✗ 失败'}")
    
    if flux_result and wan21_result:
        print("\n🎉 所有测试通过！视频生成功能配置成功。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置。")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
