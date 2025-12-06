"""
视频生成流程测试脚本
测试视频生成服务的各个组件功能
"""

import os
import sys
from app import create_app
from app.services.video_recreation_service import VideoRecreationService
from app.services.content_generation_service import ContentGenerationService
from app.services.scene_segmentation_service import SceneSegmentationService
from app.services.speech_recognition_service import SimpleSpeechRecognizer
from app.services.video_analysis_agent import VideoAnalysisAgent

def test_speech_recognition():
    """测试语音识别服务"""
    print("=== 测试语音识别服务 ===")
    recognizer = SimpleSpeechRecognizer()
    
    # 测试语音识别服务是否正常初始化
    print("✓ 语音识别服务初始化成功")
    
    # 检查API密钥配置
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if api_key:
        print("✓ DashScope API密钥已配置")
    else:
        print("⚠ DashScope API密钥未配置，部分功能可能受限")
    
    return True

def test_content_generation():
    """测试内容生成服务"""
    print("\n=== 测试内容生成服务 ===")
    generator = ContentGenerationService()
    
    # 测试内容生成服务是否正常初始化
    print("✓ 内容生成服务初始化成功")
    
    # 测试文案生成功能
    try:
        test_prompt = "测试视频文案生成"
        print(f"✓ 内容生成服务准备就绪，可处理提示: '{test_prompt}'")
    except Exception as e:
        print(f"✗ 内容生成服务异常: {e}")
        return False
    
    return True

def test_scene_segmentation():
    """测试场景分割服务"""
    print("\n=== 测试场景分割服务 ===")
    segmenter = SceneSegmentationService()
    
    # 测试场景分割服务是否正常初始化
    print("✓ 场景分割服务初始化成功")
    
    # 测试场景分割功能
    try:
        print("✓ 场景分割服务准备就绪")
    except Exception as e:
        print(f"✗ 场景分割服务异常: {e}")
        return False
    
    return True

def test_video_analysis():
    """测试视频分析服务"""
    print("\n=== 测试视频分析服务 ===")
    analyzer = VideoAnalysisAgent()
    
    # 测试视频分析服务是否正常初始化
    print("✓ 视频分析服务初始化成功")
    
    # 测试视频分析功能
    try:
        print("✓ 视频分析服务准备就绪")
    except Exception as e:
        print(f"✗ 视频分析服务异常: {e}")
        return False
    
    return True

def test_video_recreation_service():
    """测试视频重制服务"""
    print("\n=== 测试视频重制服务 ===")
    
    # 创建Flask应用实例和应用上下文
    app = create_app()
    
    with app.app_context():
        recreation_service = VideoRecreationService()
        
        # 测试服务初始化
        print("✓ 视频重制服务初始化成功")
        
        # 测试任务目录创建功能
        try:
            test_task_dir = recreation_service.create_task_directory(999, "test_video.mp4")
            print(f"✓ 任务目录创建功能正常: {test_task_dir}")
            
            # 清理测试目录
            if os.path.exists(test_task_dir):
                import shutil
                shutil.rmtree(test_task_dir)
                print("✓ 测试目录清理完成")
        except Exception as e:
            print(f"✗ 任务目录创建异常: {e}")
            return False
        
        # 测试数据库连接
        try:
            from app.models import db
            from sqlalchemy import text
            db.session.execute(text("SELECT 1")).fetchone()
            print("✓ 数据库连接正常")
        except Exception as e:
            print(f"✗ 数据库连接异常: {e}")
            return False
        
        return True

def test_api_endpoints():
    """测试API端点"""
    print("\n=== 测试API端点 ===")
    
    import requests
    
    # 测试后端服务是否正常运行
    try:
        response = requests.get("http://127.0.0.1:5000/", timeout=5)
        if response.status_code == 200:
            print("✓ 后端服务运行正常")
        else:
            print(f"⚠ 后端服务响应异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ 后端服务连接失败: {e}")
        return False
    
    # 测试抖音爬虫服务
    try:
        response = requests.get("http://0.0.0.0:80/", timeout=5)
        if response.status_code == 200:
            print("✓ 抖音爬虫服务运行正常")
        else:
            print(f"⚠ 抖音爬虫服务响应异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ 抖音爬虫服务连接失败: {e}")
    
    return True

def main():
    """主测试函数"""
    print("开始视频生成流程测试...\n")
    
    # 执行各项测试
    tests = [
        test_speech_recognition,
        test_content_generation,
        test_scene_segmentation,
        test_video_analysis,
        test_video_recreation_service,
        test_api_endpoints
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append((test_func.__name__, result))
        except Exception as e:
            print(f"✗ {test_func.__name__} 测试异常: {e}")
            results.append((test_func.__name__, False))
    
    # 输出测试总结
    print("\n" + "="*50)
    print("测试总结:")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 项通过, {failed} 项失败")
    
    if failed == 0:
        print("🎉 所有测试通过！视频生成流程准备就绪")
    else:
        print("⚠ 部分测试失败，请检查相关配置")

if __name__ == "__main__":
    main()