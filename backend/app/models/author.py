from . import db
from datetime import datetime

class DouyinAuthor(db.Model):
    """抖音作者模型"""
    __tablename__ = 'douyin_authors'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nickname = db.Column(db.String(255), nullable=False, comment='昵称')
    followers_count = db.Column(db.BigInteger, default=0, comment='粉丝数')
    following_count = db.Column(db.BigInteger, default=0, comment='关注数')
    total_favorited = db.Column(db.BigInteger, default=0, comment='获赞总数')
    signature = db.Column(db.Text, comment='个人简介')
    sec_uid = db.Column(db.String(255), unique=True, nullable=False, comment='加密用户ID')
    uid = db.Column(db.String(255), unique=True, nullable=False, comment='用户ID')
    unique_id = db.Column(db.String(255), comment='用户唯一标识')
    cover_url = db.Column(db.Text, comment='封面图片URL')
    avatar_larger_url = db.Column(db.Text, comment='头像大图URL')
    share_url = db.Column(db.Text, comment='分享链接')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关系映射
    videos = db.relationship('DouyinVideo', backref='author_info', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nickname': self.nickname,
            'followers_count': self.followers_count,
            'following_count': self.following_count,
            'total_favorited': self.total_favorited,
            'signature': self.signature,
            'sec_uid': self.sec_uid,
            'uid': self.uid,
            'unique_id': self.unique_id,
            'cover_url': self.cover_url,
            'avatar_larger_url': self.avatar_larger_url,
            'share_url': self.share_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<DouyinAuthor {self.nickname}>'
