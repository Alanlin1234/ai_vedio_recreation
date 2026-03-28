"""数据库模型"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_public(self):
        return {'id': self.id, 'username': self.username}


class VideoRecreation(db.Model):
    __tablename__ = 'video_recreations'

    id = db.Column(db.Integer, primary_key=True)
    original_video_id = db.Column(db.String(128))
    original_video_path = db.Column(db.String(1024), nullable=True)
    original_video_storage_key = db.Column(db.String(1024), nullable=True)
    owner_supabase_uid = db.Column(db.String(36), nullable=True, index=True)
    recreation_name = db.Column(db.String(256))
    status = db.Column(db.String(64), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.now)

    video_understanding = db.Column(db.Text)
    understanding_model = db.Column(db.String(128))
    new_script_content = db.Column(db.Text)

    final_video_path = db.Column(db.String(1024))
    composition_status = db.Column(db.String(64))
    completed_at = db.Column(db.DateTime)
    total_duration = db.Column(db.Float)
    video_resolution = db.Column(db.String(64))
    video_fps = db.Column(db.Float)

    creator_notes = db.Column(db.Text)
    analysis_highlights = db.Column(db.Text)
    analysis_educational = db.Column(db.Text)
    review_score = db.Column(db.Float)
    review_detail_json = db.Column(db.Text)
    output_language = db.Column(db.String(8), default='zh')

    def to_dict(self):
        return {
            'id': self.id,
            'original_video_id': self.original_video_id,
            'original_video_path': self.original_video_path,
            'original_video_storage_key': self.original_video_storage_key,
            'owner_supabase_uid': self.owner_supabase_uid,
            'recreation_name': self.recreation_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'video_understanding': self.video_understanding,
            'understanding_model': self.understanding_model,
            'new_script_content': self.new_script_content,
            'final_video_path': self.final_video_path,
            'composition_status': self.composition_status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'total_duration': self.total_duration,
            'video_resolution': self.video_resolution,
            'video_fps': self.video_fps,
            'creator_notes': self.creator_notes,
            'analysis_highlights': self.analysis_highlights,
            'analysis_educational': self.analysis_educational,
            'review_score': self.review_score,
            'review_detail_json': self.review_detail_json,
            'output_language': self.output_language or 'zh',
        }


class RecreationScene(db.Model):
    __tablename__ = 'recreation_scenes'

    id = db.Column(db.Integer, primary_key=True)
    recreation_id = db.Column(db.Integer, db.ForeignKey('video_recreations.id'), nullable=False, index=True)
    scene_index = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Float, default=0)
    end_time = db.Column(db.Float, default=0)
    duration = db.Column(db.Float, default=5)
    shot_type = db.Column(db.String(128))
    description = db.Column(db.Text)
    plot = db.Column(db.Text)
    dialogue = db.Column(db.Text)
    video_prompt = db.Column(db.Text)
    generated_image_path = db.Column(db.String(1024))
    generated_video_path = db.Column(db.String(1024))
    generation_status = db.Column(db.String(64), default='pending')
    generation_completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'recreation_id': self.recreation_id,
            'scene_index': self.scene_index,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'shot_type': self.shot_type,
            'description': self.description,
            'plot': self.plot,
            'dialogue': self.dialogue,
            'video_prompt': self.video_prompt,
            'generated_image_path': self.generated_image_path,
            'generated_video_path': self.generated_video_path,
            'generation_status': self.generation_status,
            'generation_completed_at': self.generation_completed_at.isoformat()
            if self.generation_completed_at
            else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RecreationLog(db.Model):
    __tablename__ = 'recreation_logs'

    id = db.Column(db.Integer, primary_key=True)
    recreation_id = db.Column(db.Integer, db.ForeignKey('video_recreations.id'), index=True)
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


def ensure_video_recreation_schema():
    """为已有 SQLite 库增量添加 video_recreations 新列（避免仅删库才能迁移）。"""
    try:
        inspector = inspect(db.engine)
        if 'video_recreations' not in inspector.get_table_names():
            return
        cols = {c['name'] for c in inspector.get_columns('video_recreations')}
        stmts = []
        if 'creator_notes' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN creator_notes TEXT')
        if 'analysis_highlights' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN analysis_highlights TEXT')
        if 'analysis_educational' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN analysis_educational TEXT')
        if 'review_score' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN review_score REAL')
        if 'review_detail_json' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN review_detail_json TEXT')
        if 'owner_supabase_uid' not in cols:
            stmts.append('ALTER TABLE video_recreations ADD COLUMN owner_supabase_uid VARCHAR(36)')
        if 'original_video_storage_key' not in cols:
            stmts.append(
                'ALTER TABLE video_recreations ADD COLUMN original_video_storage_key VARCHAR(1024)'
            )
        if 'output_language' not in cols:
            stmts.append("ALTER TABLE video_recreations ADD COLUMN output_language VARCHAR(8)")
        for stmt in stmts:
            db.session.execute(text(stmt))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f'ensure_video_recreation_schema: {e}')


def ensure_default_user():
    """若无用户则创建默认管理员（可通过环境变量覆盖）。启用 Supabase JWT 时跳过。"""
    if os.environ.get("SUPABASE_JWT_SECRET", "").strip():
        return
    if User.query.count() > 0:
        return
    username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
    password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    print(f'已创建默认用户: {username}（请在生产环境修改密码）')
