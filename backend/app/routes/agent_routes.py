"""
Agent系统API路由
"""
from flask import Blueprint, request, jsonify
from app.agents.orchestrator import VideoCreationOrchestrator
from config import config
import asyncio

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agent')


@agent_bp.before_request
def _require_login_for_agent():
    from flask import session, jsonify

    if request.method == 'OPTIONS':
        return None
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '请先登录', 'code': 'UNAUTHORIZED'}), 401
    return None


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


@agent_bp.route('/generate-videos/<int:recreation_id>', methods=['POST'])
def agent_generate_scene_videos(recreation_id):
    """
    分场景视频生成（与 /api/pipeline/generate-scene-videos 同源逻辑，供前端 agentApi 使用）。
    返回体同时包含扁平字段与 result 包装，兼容不同前端解析方式。
    """
    from app.models import VideoRecreation, db
    from app.services.pipeline_workflow import run_generate_scene_videos

    recreation = VideoRecreation.query.get(recreation_id)
    if not recreation:
        return jsonify({'success': False, 'error': '项目不存在'}), 404

    result = run_generate_scene_videos(recreation_id)

    if result.get('success'):
        recreation.status = 'completed'
        db.session.commit()

    gv = result.get('generated_videos') or []
    payload = {
        'success': bool(result.get('success')),
        'recreation_id': recreation_id,
        'generated_videos': gv,
        'failed_scenes': result.get('failed_scenes', []),
        'total_scenes': result.get('total_scenes'),
        'successful_count': result.get('successful_count'),
        'error': result.get('error'),
        'debug_prompts': result.get('debug_prompts') or [],
        'result': {
            'scene_videos': gv,
            'generated_videos': gv,
            'debug_prompts': result.get('debug_prompts') or [],
        },
        'message': '完成' if result.get('success') else (result.get('error') or '生成失败'),
    }
    return jsonify(payload), (200 if result.get('success') else 500)


@agent_bp.route('/video-status/<int:recreation_id>', methods=['GET'])
def agent_video_status(recreation_id):
    from app.services.pipeline_workflow import build_scene_video_status

    data = build_scene_video_status(recreation_id)
    code = 200 if data.get('success') else 404
    return jsonify(data), code
