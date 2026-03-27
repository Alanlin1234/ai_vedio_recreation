"""
Agent系统API路由
"""
from flask import Blueprint, request, jsonify
from app.agents.orchestrator import VideoCreationOrchestrator
from config import config
import asyncio

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')

# 初始化编排器
orchestrator = VideoCreationOrchestrator({
    'comfyui_url': config.COMFYUI_URL if hasattr(config, 'COMFYUI_URL') else 'http://127.0.0.1:8188',
    'output_dir': 'output/videos'
})


@agent_bp.route('/create-video', methods=['POST'])
def create_video():
    """
    端到端创建视频
    
    请求体:
    {
        "keywords": ["热点关键词"],
        "style": "commentary",
        "duration": 60,
        "comfyui_workflow": {},
        "output_filename": "my_video.mp4"
    }
    """
    try:
        data = request.get_json()
        
        # 执行异步流程
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(orchestrator.create_video(data))
        loop.close()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '视频创建成功',
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': '视频创建失败',
                'error': result.get('error'),
                'failed_stage': result.get('failed_stage')
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@agent_bp.route('/status', methods=['GET'])
def get_status():
    """获取Agent系统状态"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        status = loop.run_until_complete(orchestrator.get_stage_status())
        loop.close()
        
        return jsonify({
            'success': True,
            'data': status
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@agent_bp.route('/test-comfyui', methods=['POST'])
def test_comfyui():
    """
    测试ComfyUI连接
    
    请求体:
    {
        "comfyui_url": "http://127.0.0.1:8188"
    }
    """
    try:
        data = request.get_json()
        comfyui_url = data.get('comfyui_url', 'http://127.0.0.1:8188')
        
        # TODO: 实现实际的ComfyUI连接测试
        
        return jsonify({
            'success': True,
            'message': 'ComfyUI连接正常',
            'url': comfyui_url
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'ComfyUI连接失败: {str(e)}'
        }), 500
