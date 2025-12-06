from flask import Blueprint, request, jsonify
from app.services.video_recreation_service import VideoRecreationService
from app.services.video_service import VideoService
from app.models import db, VideoRecreation, RecreationScene, RecreationLog
from datetime import datetime
import os
import traceback

video_recreation_bp = Blueprint('video_recreation', __name__)

@video_recreation_bp.route('/videos/<video_id>/recreate', methods=['POST'])
def recreate_video(video_id):
    """
    视频二创接口
    
    Args:
        video_id: 视频ID
        
    Returns:
        二创结果
    """
    try:
        # 获取视频信息
        video = VideoService.get_video_by_id(video_id)
        if not video:
            return jsonify({'error': '视频不存在'}), 404
        
        video_path = video.get('local_file_path')
        if not video_path or not os.path.exists(video_path):
            return jsonify({'error': '视频文件不存在或路径无效'}), 400
        
        # 检查是否已经在处理中
        existing_recreation = VideoRecreation.query.filter_by(
            original_video_id=video_id,
            status='processing'
        ).first()
        
        if existing_recreation:
            return jsonify({
                'error': '该视频正在二创处理中，请稍后再试',
                'recreation_id': existing_recreation.id
            }), 409
        
        # 创建二创记录
        recreation = VideoRecreation(
            original_video_id=video_id,
            status='processing',
            created_at=datetime.now()
        )
        db.session.add(recreation)
        db.session.commit()
        
        # 记录开始日志
        log = RecreationLog(
            recreation_id=recreation.id,
            step_name='start',
            log_level='info',
            message='开始视频二创处理',
            created_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        # 初始化二创服务
        print(f"[二创进度] 初始化二创服务，任务ID: {recreation.id}")
        recreation_service = VideoRecreationService()
        
        try:
            # 调用完整的视频二创处理流程
            result = recreation_service.process_video_for_recreation(video_path, recreation.id)
            
            if result.get('success'):
                print(f"[二创进度] 视频二创处理完成")
                recreation.status = 'completed'
                recreation.completed_at = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': '视频二创处理完成',
                    'recreation_id': recreation.id,
                    'result': result
                })
            else:
                print(f"[二创进度] 视频二创处理失败: {result.get('error', '未知错误')}")
                recreation.status = 'failed'
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'message': f"视频二创处理失败: {result.get('error', '未知错误')}",
                    'recreation_id': recreation.id
                }), 500
        
        except Exception as e:
            # 更新状态为失败
            recreation.status = 'failed'
            log_step(recreation.id, 'error', 'failed', f'处理失败: {str(e)}')
            db.session.commit()
            
            return jsonify({
                'success': False,
                'recreation_id': recreation.id,
                'error': str(e)
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@video_recreation_bp.route('/recreations/<int:recreation_id>', methods=['GET'])
def get_recreation_status(recreation_id):
    """
    获取二创状态
    
    Args:
        recreation_id: 二创ID
        
    Returns:
        二创状态信息
    """
    try:
        recreation = VideoRecreation.query.get(recreation_id)
        if not recreation:
            return jsonify({'error': '二创记录不存在'}), 404
        
        # 获取场景信息
        scenes = RecreationScene.query.filter_by(recreation_id=recreation_id).order_by(RecreationScene.scene_index).all()
        
        # 获取日志信息
        logs = RecreationLog.query.filter_by(recreation_id=recreation_id).order_by(RecreationLog.created_at).all()
        
        return jsonify({
            'recreation': recreation.to_dict(),
            'scenes': [scene.to_dict() for scene in scenes],
            'logs': [log.to_dict() for log in logs]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_recreation_bp.route('/recreations', methods=['GET'])
def get_recreations():
    """
    获取二创列表
    
    Returns:
        二创列表
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        query = VideoRecreation.query
        
        if status:
            query = query.filter_by(status=status)
        
        recreations = query.order_by(VideoRecreation.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'recreations': [recreation.to_dict() for recreation in recreations.items],
            'total': recreations.total,
            'pages': recreations.pages,
            'current_page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def log_step(recreation_id: int, step: str, status: str, message: str):
    """
    记录处理步骤日志
    
    Args:
        recreation_id: 二创ID
        step: 步骤名称
        status: 状态
        message: 消息
    """
    try:
        log = RecreationLog(
            recreation_id=recreation_id,
            step_name=step,
            log_level='info' if status == 'success' or status == 'processing' else 'error',
            message=message,
            created_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        print(f"[{step}] {status}: {message}")
    except Exception as e:
        print(f"记录日志失败: {e}")