from app.models import DouyinVideo, DouyinAuthor, db
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc
from typing import Dict, List, Optional
from datetime import datetime

class VideoService:
    """视频完整逻辑服务"""
    
    @staticmethod
    def create_video(video_data: Dict) -> int:
        """创建视频"""
        try:
            # 检查是否已存在
            existing_video = DouyinVideo.query.filter_by(
                video_id=video_data['video_id']
            ).first()
            
            if existing_video:
                # 如果存在则更新
                return VideoService.update_video(video_data['video_id'], video_data)
            
            # 处理标题长度限制
            title = video_data.get('title', '')
            if len(title) > 255:
                title = title[:252] + '...'  # 截断并添加省略
            
            # 处理其他可能过长的字段
            author_nickname = video_data.get('author_nickname', '')
            if len(author_nickname) > 100:
                author_nickname = author_nickname[:97] + '...'
                
            author_unique_id = video_data.get('author_unique_id', '')
            if len(author_unique_id) > 100:
                author_unique_id = author_unique_id[:100]
                
            author_uid = video_data.get('author_uid', '')
            if len(author_uid) > 100:
                author_uid = author_uid[:100]
            
            video = DouyinVideo(
                title=title,
                description=video_data.get('description', ''),
                create_time=video_data.get('create_time'),
                duration=video_data.get('duration', 0),
                video_id=video_data['video_id'],
                video_uri=video_data.get('video_uri', ''),
                play_count=video_data.get('play_count', 0),
                digg_count=video_data.get('digg_count', 0),
                comment_count=video_data.get('comment_count', 0),
                share_count=video_data.get('share_count', 0),
                collect_count=video_data.get('collect_count', 0),
                dynamic_cover_url=video_data.get('dynamic_cover_url', ''),
                author_nickname=author_nickname,
                author_unique_id=author_unique_id,
                author_uid=author_uid,
                author_signature=video_data.get('author_signature', ''),
                author_follower_count=video_data.get('author_follower_count', 0),
                author_following_count=video_data.get('author_following_count', 0),
                author_total_favorited=video_data.get('author_total_favorited', 0),
                video_quality_high=video_data.get('video_quality_high', ''),
                video_quality_medium=video_data.get('video_quality_medium', ''),
                video_quality_low=video_data.get('video_quality_low', ''),
                local_file_path=video_data.get('local_file_path', '')
            )
            
            # 处理标签
            if 'tags' in video_data:
                video.set_tags(video_data['tags'])
            
            db.session.add(video)
            db.session.commit()
            return video.id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"创建视频失败: {str(e)}")
    
    @staticmethod
    def get_video_by_id(video_id: str) -> Optional[Dict]:
        """根据视频ID获取视频"""
        try:
            video = DouyinVideo.query.filter_by(id=video_id).first()
            return video.to_dict() if video else None
        except SQLAlchemyError as e:
            raise Exception(f"获取视频失败: {str(e)}")
    
    @staticmethod
    def update_video(video_id: str, video_data: Dict) -> int:
        """更新视频信息"""
        try:
            video = DouyinVideo.query.filter_by(id=video_id).first()
            if not video:
                raise Exception("视频不存在")
            
            # 更新字段
            for key, value in video_data.items():
                if hasattr(video, key) and key not in ['id', 'created_at']:
                    if key == 'tags':
                        video.set_tags(value)
                    else:
                        setattr(video, key, value)
            
            db.session.commit()
            return video.id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"更新视频失败: {str(e)}")
    
    @staticmethod
    def get_videos_paginated(page: int = 1, per_page: int = 10, author_uid: str = None) -> Dict:
        """分页获取视频列表"""
        try:
            query = DouyinVideo.query
            
            # 如果指定了作者UID
            if author_uid:
                query = query.filter_by(author_uid=author_uid)
            
            # 按创建时间倒序排列
            query = query.order_by(desc(DouyinVideo.created_at))
            
            pagination = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            return {
                'videos': [video.to_dict() for video in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        except SQLAlchemyError as e:
            raise Exception(f"获取视频列表失败: {str(e)}")
    
    @staticmethod
    def delete_video(video_id: str) -> bool:
        """删除视频"""
        try:
            video = DouyinVideo.query.filter_by(id=video_id).first()
            if not video:
                raise Exception("视频不存在")
            
            db.session.delete(video)
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"删除视频失败: {str(e)}")
    
    @staticmethod
    def get_videos_by_author(author_uid: str, limit: int = 10) -> List[Dict]:
        """获取指定作者的视频列表"""
        try:
            videos = DouyinVideo.query.filter_by(author_uid=author_uid)\
                                    .order_by(desc(DouyinVideo.created_at))\
                                    .limit(limit).all()
            return [video.to_dict() for video in videos]
        except SQLAlchemyError as e:
            raise Exception(f"获取作者视频失败: {str(e)}")
