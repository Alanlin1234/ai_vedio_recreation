from app.models import db, DouyinAuthor, DouyinVideo
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, and_, desc
from datetime import datetime
import json

class DBService:
    """使用SQLAlchemy ORM的数据库服务层"""
    
    # ==================== 作者相关操作 ====================
    
    @staticmethod
    def create_author(author_data):
        """创建作者"""
        try:
            # 检查是否已存在
            existing_author = DouyinAuthor.query.filter(
                or_(DouyinAuthor.uid == author_data['uid'], 
                    DouyinAuthor.sec_uid == author_data['sec_uid'])
            ).first()
            
            if existing_author:
                # 如果存在则更新
                return DBService.update_author(author_data['uid'], author_data)
            
            author = DouyinAuthor(
                nickname=author_data['nickname'],
                followers_count=author_data.get('followers_count', 0),
                following_count=author_data.get('following_count', 0),
                total_favorited=author_data.get('total_favorited', 0),
                signature=author_data.get('signature', ''),
                sec_uid=author_data['sec_uid'],
                uid=author_data['uid'],
                unique_id=author_data.get('unique_id', ''),
                cover_url=author_data.get('cover_url'),
                avatar_larger_url=author_data.get('avatar_larger_url'),
                share_url=author_data.get('share_url', '')
            )
            
            db.session.add(author)
            db.session.commit()
            return author.id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"创建作者失败: {str(e)}")
    
    @staticmethod
    def get_author_by_uid(uid):
        """根据UID获取作者"""
        try:
            author = DouyinAuthor.query.filter_by(uid=uid).first()
            return author.to_dict() if author else None
        except SQLAlchemyError as e:
            raise Exception(f"获取作者失败: {str(e)}")
    
    @staticmethod
    def update_author(uid, author_data):
        """更新作者信息"""
        try:
            author = DouyinAuthor.query.filter_by(uid=uid).first()
            if not author:
                raise Exception("作者不存在")
            
            # 更新字段
            for key, value in author_data.items():
                if hasattr(author, key) and key not in ['id', 'created_at']:
                    setattr(author, key, value)
            
            db.session.commit()
            return author.id
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"更新作者失败: {str(e)}")
    
    @staticmethod
    def get_authors_paginated(page=1, per_page=10):
        """分页获取作者列表"""
        try:
            pagination = DouyinAuthor.query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            return {
                'authors': [author.to_dict() for author in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'per_page': per_page,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        except SQLAlchemyError as e:
            raise Exception(f"获取作者列表失败: {str(e)}")
    
    # ==================== 视频相关操作 ====================
    
    @staticmethod
    def create_video(video_data):
        """创建视频"""
        try:
            # 检查是否已存在
            existing_video = DouyinVideo.query.filter_by(
                video_id=video_data['video_id']
            ).first()
            
            if existing_video:
                # 如果存在则更新
                return DBService.update_video(video_data['video_id'], video_data)
            
            video = DouyinVideo(
                title=video_data.get('title', ''),
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
                author_nickname=video_data.get('author_nickname', ''),
                author_unique_id=video_data.get('author_unique_id', ''),
                author_uid=video_data.get('author_uid', ''),
                author_signature=video_data.get('author_signature', ''),
                author_follower_count=video_data.get('author_follower_count', 0),
                author_following_count=video_data.get('author_following_count', 0),
                author_total_favorited=video_data.get('author_total_favorited', 0),
                video_quality_high=video_data.get('video_quality_high', ''),
                video_quality_medium=video_data.get('video_quality_medium', ''),
                video_quality_low=video_data.get('video_quality_low', '')
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
    def get_video_by_id(video_id):
        """根据视频ID获取视频"""
        try:
            video = DouyinVideo.query.filter_by(video_id=video_id).first()
            return video.to_dict() if video else None
        except SQLAlchemyError as e:
            raise Exception(f"获取视频失败: {str(e)}")
    
    @staticmethod
    def update_video(video_id, video_data):
        """更新视频信息"""
        try:
            video = DouyinVideo.query.filter_by(video_id=video_id).first()
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
    def delete_video(video_id):
        """删除视频"""
        try:
            video = DouyinVideo.query.filter_by(video_id=video_id).first()
            if not video:
                raise Exception("视频不存在")
            
            db.session.delete(video)
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"删除视频失败: {str(e)}")
    
    @staticmethod
    def get_videos_paginated(page=1, per_page=10):
        """分页获取视频列表"""
        try:
            pagination = DouyinVideo.query.order_by(desc(DouyinVideo.created_at)).paginate(
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