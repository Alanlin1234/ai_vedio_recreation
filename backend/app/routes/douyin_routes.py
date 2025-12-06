from flask import Blueprint, request, jsonify
from app.services.douyin_service import DouyinService
# 删除这行：from service.data_service import DataService
from app.services.author_service import AuthorService

douyin_bp = Blueprint('douyin', __name__)

@douyin_bp.route('/fetch_author_by_sec_uid', methods=['POST'])
def fetch_author_by_sec_uid():
    """根据sec_uid获取并保存作者信息"""
    data = request.get_json()
    if not data or 'sec_uid' not in data:
        return jsonify({'error': '缺少sec_uid参数'}), 400
    
    try:
        sec_uid = data['sec_uid']
        # 调用DouyinService获取作者信息
        author_info = DouyinService.fetch_author_info(sec_uid)
        
        # 保存到数据库
        AuthorService.create_author(author_info)
        
        return jsonify({
            'success': True, 
            'message': '作者信息获取并保存成功',
            'author_info': author_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@douyin_bp.route('/crawl_user_today_videos', methods=['POST'])
def download_today_videos():
    data = request.get_json()
    sec_uid = data.get('sec_uid')
    
    if not sec_uid:
        return jsonify({'error': 'sec_uid参数缺失'}), 400
    
    try:
        # 爬取当天视频
        video_count = DouyinService.crawl_user_today_videos(sec_uid)
        return jsonify({
            'success': True,
            'video_count': video_count,  # 改为 video_count
            'message': f'成功下载了 {video_count} 个当天发布的视频'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500