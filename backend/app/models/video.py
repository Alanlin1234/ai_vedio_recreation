from . import db
from datetime import datetime
import json

class DouyinVideo(db.Model):
    """抖音视频模型"""
    __tablename__ = 'douyin_videos'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.Text, comment='视频标题')
    description = db.Column(db.Text, comment='视频描述')
    create_time = db.Column(db.DateTime, comment='视频创建时间')
    duration = db.Column(db.Integer, comment='视频时长(秒)')
    video_id = db.Column(db.String(255), unique=True, nullable=False, comment='视频ID')
    video_uri = db.Column(db.Text, comment='视频URI')
    play_count = db.Column(db.BigInteger, default=0, comment='播放数')
    digg_count = db.Column(db.BigInteger, default=0, comment='点赞数')
    comment_count = db.Column(db.BigInteger, default=0, comment='评论数')
    share_count = db.Column(db.BigInteger, default=0, comment='分享数')
    collect_count = db.Column(db.BigInteger, default=0, comment='收藏数')
    dynamic_cover_url = db.Column(db.Text, comment='动态封面URL')
    author_nickname = db.Column(db.String(255), comment='作者昵称')
    author_unique_id = db.Column(db.String(255), comment='作者唯一ID')
    author_uid = db.Column(db.String(255), db.ForeignKey('douyin_authors.uid'), comment='作者UID')
    author_signature = db.Column(db.Text, comment='作者签名')
    author_follower_count = db.Column(db.BigInteger, default=0, comment='作者粉丝数')
    author_following_count = db.Column(db.BigInteger, default=0, comment='作者关注数')
    author_total_favorited = db.Column(db.BigInteger, default=0, comment='作者获赞总数')
    video_quality_high = db.Column(db.Text, comment='高清视频URL')
    video_quality_medium = db.Column(db.Text, comment='中等质量视频URL')
    video_quality_low = db.Column(db.Text, comment='低质量视频URL')
    local_file_path = db.Column(db.Text, comment='本地存储路径')  # 添加这个字段
    tags = db.Column(db.Text, comment='标签(JSON格式)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    def get_tags(self):
        """获取标签列表"""
        if self.tags:
            try:
                return json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_tags(self, tags_list):
        """设置标签列表"""
        if tags_list:
            self.tags = json.dumps(tags_list, ensure_ascii=False)
        else:
            self.tags = None
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'duration': self.duration,
            'video_id': self.video_id,
            'video_uri': self.video_uri,
            'play_count': self.play_count,
            'digg_count': self.digg_count,
            'comment_count': self.comment_count,
            'share_count': self.share_count,
            'collect_count': self.collect_count,
            'dynamic_cover_url': self.dynamic_cover_url,
            'author_nickname': self.author_nickname,
            'author_unique_id': self.author_unique_id,
            'author_uid': self.author_uid,
            'author_signature': self.author_signature,
            'author_follower_count': self.author_follower_count,
            'author_following_count': self.author_following_count,
            'author_total_favorited': self.author_total_favorited,
            'video_quality_high': self.video_quality_high,
            'video_quality_medium': self.video_quality_medium,
            'video_quality_low': self.video_quality_low,
            'local_file_path': self.local_file_path,  # 添加这一行
            'tags': self.get_tags(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<DouyinVideo {self.video_id}>'