from flask import Blueprint, request, jsonify
from app.services.video_service import VideoService

video_bp = Blueprint('video', __name__)

# @video_bp.route('/videos', methods=['POST'])
# def add_video():
#     data = request.get_json()
#     try:
#         video_id = VideoService.create_video(data)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# def get_video(video_id):
#     try:
#         video = VideoService.get_video_by_id(video_id)
#         if not video:
#             return jsonify({'error': '视频不存在'}), 404
#         return jsonify(video)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@video_bp.route('/videos/<video_id>', methods=['PUT'])
def update_video(video_id):
    data = request.get_json()
    try:
        VideoService.update_video(video_id, data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/videos/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    try:
        VideoService.delete_video(video_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/videos', methods=['GET'])
def get_videos():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        author_uid = request.args.get('author_uid')
        
        result = VideoService.get_videos_paginated(page, per_page, author_uid)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@video_bp.route('/authors/<author_uid>/videos', methods=['GET'])
def get_author_videos(author_uid):
    try:
        limit = request.args.get('limit', 10, type=int)
        videos = VideoService.get_videos_by_author(author_uid, limit)
        return jsonify({'videos': videos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
