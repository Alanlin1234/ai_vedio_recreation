"""
测试追踪系统
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.agents.orchestrator import VideoCreationOrchestrator
from app.agents.tracking_manager import TrackingManager


async def test_tracking_system():
    """测试追踪系统功能"""
    
    # 配置
    config = {
        "tracking_file": "test_tracking.json",
        "log_level": "INFO",
        "database": {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "ai_agent_comfy"
        }
    }
    
    # 输入参数
    input_params = {
        "keywords": ["科技", "人工智能"],
        "hotspot_count": 5,
        "style": "cinematic",
        "duration": 60,
        "output_filename": "test_video.mp4"
    }
    
    print("=" * 60)
    print("测试追踪系统")
    print("=" * 60)
    
    try:
        # 创建编排器
        orchestrator = VideoCreationOrchestrator(config)
        
        # 运行视频创作流程
        print("\n开始视频创作流程...")
        result = await orchestrator.create_video(input_params)
        
        print("\n" + "=" * 60)
        print("流程执行结果:")
        print(f"成功: {result['success']}")
        if 'session_id' in result:
            print(f"会话ID: {result['session_id']}")
        if 'final_video' in result:
            print(f"视频路径: {result['final_video']}")
        
        # 检查追踪文件
        tracking_file = "test_tracking.json"
        if os.path.exists(tracking_file):
            print(f"\n追踪文件已创建: {tracking_file}")
            
            # 读取追踪数据
            with open(tracking_file, 'r', encoding='utf-8') as f:
                tracking_data = json.load(f)
            
            print(f"总会话数: {tracking_data.get('total_sessions', 0)}")
            
            # 显示会话摘要
            tracking_manager = TrackingManager(tracking_file)
            summaries = tracking_manager.get_all_sessions_summary()
            
            if summaries:
                print("\n会话摘要:")
                for summary in summaries:
                    print(f"\n会话ID: {summary['session_id']}")
                    print(f"状态: {summary['status']}")
                    print(f"总耗时: {summary['total_duration']:.2f}秒")
                    print(f"执行的Agent: {', '.join(summary['agents_executed'])}")
                    print(f"文件数量: {summary['file_count']}")
                    print(f"错误数量: {summary['error_count']}")
                    
                    # 显示token使用摘要
                    if summary['token_usage_summary']:
                        print("Token使用情况:")
                        for model, usage in summary['token_usage_summary'].items():
                            print(f"  {model}: {usage['total_tokens']} tokens")
        else:
            print("\n警告: 追踪文件未创建")
        
        print("\n" + "=" * 60)
        print("追踪系统测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


def test_tracking_manager_directly():
    """直接测试追踪管理器"""
    print("\n" + "=" * 60)
    print("直接测试追踪管理器")
    print("=" * 60)
    
    # 创建追踪管理器
    tracking_file = "direct_test_tracking.json"
    tracking_manager = TrackingManager(tracking_file)
    
    # 开始会话
    input_params = {
        "test_type": "direct_test",
        "description": "直接测试追踪管理器功能"
    }
    session_id = tracking_manager.start_session(input_params)
    print(f"开始会话: {session_id}")
    
    # 记录一些测试数据
    tracking_manager.record_token_usage("gpt-4", {
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "total_tokens": 300,
        "cost_estimate": 0.06
    })
    
    tracking_manager.record_time_tracking("test_stage", 5.5)
    
    tracking_manager.record_generated_content("script", {
        "title": "测试脚本",
        "content": "这是一个测试脚本内容",
        "length": 150
    })
    
    tracking_manager.record_file_location("video", "/path/to/test_video.mp4", {
        "size": "10MB",
        "duration": "60s"
    })
    
    # 记录Agent执行
    tracking_manager.record_agent_execution("test_agent", {
        "success": True,
        "input": {"test": "data"},
        "data": {"result": "success"},
        "execution_time": 2.5,
        "token_usage": {
            "test-model": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
        }
    })
    
    # 结束会话
    tracking_manager.end_session({"test_result": "success"})
    
    print(f"会话结束，数据已保存到: {tracking_file}")
    
    # 显示会话摘要
    summary = tracking_manager.get_session_summary(session_id)
    if summary:
        print("\n会话摘要:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    
    print("\n直接测试完成")


if __name__ == "__main__":
    # 运行直接测试
    test_tracking_manager_directly()
    
    # 运行完整系统测试
    asyncio.run(test_tracking_system())