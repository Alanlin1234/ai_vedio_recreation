from app.models import DouyinAuthor, db
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_
from typing import Dict, List, Optional

class AuthorService:
    """作者业务逻辑服务"""
    
    @staticmethod
    def create_author(author_data: Dict) -> int:
        """创建作者"""
        try:
            # 检查是否已存在
            existing_author = DouyinAuthor.query.filter(
                or_(DouyinAuthor.uid == author_data['uid'], 
                    DouyinAuthor.sec_uid == author_data['sec_uid'])
            ).first()
            
            if existing_author:
                # 如果存在则更新
                return AuthorService.update_author(author_data['uid'], author_data)
            
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
    def get_author_by_uid(uid: str) -> Optional[Dict]:
        """根据UID获取作者"""
        try:
            author = DouyinAuthor.query.filter_by(uid=uid).first()
            return author.to_dict() if author else None
        except SQLAlchemyError as e:
            raise Exception(f"获取作者失败: {str(e)}")
    
    @staticmethod
    def update_author(uid: str, author_data: Dict) -> int:
        """更新作者信息"""
        try:
            author = DouyinAuthor.query.filter_by(id=uid).first()
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
    def get_authors_paginated(page: int = 1, per_page: int = 10) -> Dict:
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
    
    @staticmethod
    def delete_author(uid: str) -> bool:
        """删除作者"""
        try:
            author = DouyinAuthor.query.filter_by(id=uid).first()
            if not author:
                raise Exception("作者不存在")
            
            db.session.delete(author)
            db.session.commit()
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"删除作者失败: {str(e)}")
