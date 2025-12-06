from . import db
from datetime import datetime
import json

class VideoRecreation(db.Model):
    """视频二创主表"""
    __tablename__ = 'video_recreations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    original_video_id = db.Column(db.String(255), nullable=False, comment='原视频ID')
    recreation_name = db.Column(db.String(255), comment='二创项目名称')
    status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed'), default='pending', comment='处理状态')
    
    # 视频理解结果
    video_understanding = db.Column(db.Text, comment='视频内容理解结果')
    understanding_model = db.Column(db.String(100), comment='理解模型名称')
    understanding_time_cost = db.Column(db.Float, comment='理解耗时(秒)')
    
    # 音频转录结果
    audio_file_path = db.Column(db.String(500), comment='音频文件路径')
    transcription_text = db.Column(db.Text, comment='转录文本内容')
    transcription_service = db.Column(db.String(100), comment='转录服务')
    
    # 新文案
    new_script_content = db.Column(db.Text, comment='新文案内容')
    script_generation_model = db.Column(db.String(100), comment='文案生成模型')
    
    # TTS音频
    tts_audio_path = db.Column(db.String(500), comment='TTS音频文件路径')
    tts_service = db.Column(db.String(100), comment='TTS服务')
    tts_voice_model = db.Column(db.String(100), comment='语音模型')
    tts_audio_duration = db.Column(db.Float, comment='TTS音频时长(秒)')
    
    # 最终输出视频
    final_video_path = db.Column(db.String(500), comment='最终合成视频文件路径')
    final_video_with_audio_path = db.Column(db.String(500), comment='音画同步后的最终视频路径')
    composition_status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed'), default='pending', comment='视频合成状态')
    total_duration = db.Column(db.Float, comment='最终视频总时长(秒)')
    final_file_size = db.Column(db.BigInteger, comment='最终视频文件大小(字节)')
    video_resolution = db.Column(db.String(20), comment='最终视频分辨率')
    video_fps = db.Column(db.Integer, comment='最终视频帧率')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    
    # 关联场景
    scenes = db.relationship('RecreationScene', backref='recreation', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('RecreationLog', backref='recreation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'original_video_id': self.original_video_id,
            'recreation_name': self.recreation_name,
            'status': self.status,
            'video_understanding': self.video_understanding,
            'understanding_model': self.understanding_model,
            'understanding_time_cost': self.understanding_time_cost,
            'audio_file_path': self.audio_file_path,
            'transcription_text': self.transcription_text,
            'transcription_service': self.transcription_service,
            'new_script_content': self.new_script_content,
            'script_generation_model': self.script_generation_model,
            'tts_audio_path': self.tts_audio_path,
            'tts_service': self.tts_service,
            'tts_voice_model': self.tts_voice_model,
            'tts_audio_duration': self.tts_audio_duration,
            'final_video_path': self.final_video_path,
            'final_video_with_audio_path': self.final_video_with_audio_path,
            'composition_status': self.composition_status,
            'total_duration': self.total_duration,
            'final_file_size': self.final_file_size,
            'video_resolution': self.video_resolution,
            'video_fps': self.video_fps,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self):
        return f'<VideoRecreation {self.id}>'


class RecreationScene(db.Model):
    """二创场景表"""
    __tablename__ = 'recreation_scenes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recreation_id = db.Column(db.Integer, db.ForeignKey('video_recreations.id'), nullable=False, comment='关联video_recreations表')
    scene_index = db.Column(db.Integer, nullable=False, comment='场景序号')
    start_time = db.Column(db.Float, nullable=False, comment='开始时间(秒)')
    end_time = db.Column(db.Float, nullable=False, comment='结束时间(秒)')
    duration = db.Column(db.Float, nullable=False, comment='场景时长(秒)')
    description = db.Column(db.Text, comment='场景描述')
    
    # 文生视频提示词
    video_prompt = db.Column(db.Text, comment='视频生成提示词')
    technical_params = db.Column(db.JSON, comment='技术参数(分辨率、帧率等)')
    style_elements = db.Column(db.JSON, comment='风格元素')
    prompt_generation_model = db.Column(db.String(100), comment='提示词生成模型')
    
    # 生成的视频文件
    generated_video_path = db.Column(db.String(500), comment='单个场景生成的视频文件路径')
    generation_status = db.Column(db.Enum('pending', 'processing', 'completed', 'failed'), default='pending')
    generation_task_id = db.Column(db.String(255), comment='外部服务任务ID')
    generation_service = db.Column(db.String(100), comment='视频生成服务')
    video_file_size = db.Column(db.BigInteger, comment='场景视频文件大小')
    video_resolution = db.Column(db.String(20), comment='场景视频分辨率')
    video_fps = db.Column(db.Integer, comment='场景视频帧率')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    generation_completed_at = db.Column(db.DateTime, comment='生成完成时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'recreation_id': self.recreation_id,
            'scene_index': self.scene_index,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'description': self.description,
            'video_prompt': self.video_prompt,
            'technical_params': self.technical_params,
            'style_elements': self.style_elements,
            'prompt_generation_model': self.prompt_generation_model,
            'generated_video_path': self.generated_video_path,
            'generation_status': self.generation_status,
            'generation_task_id': self.generation_task_id,
            'generation_service': self.generation_service,
            'video_file_size': self.video_file_size,
            'video_resolution': self.video_resolution,
            'video_fps': self.video_fps,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'generation_completed_at': self.generation_completed_at.isoformat() if self.generation_completed_at else None
        }
    
    def __repr__(self):
        return f'<RecreationScene {self.id}>'


class RecreationLog(db.Model):
    """处理日志表"""
    __tablename__ = 'recreation_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recreation_id = db.Column(db.Integer, db.ForeignKey('video_recreations.id'), nullable=False, comment='关联video_recreations表')
    scene_id = db.Column(db.Integer, db.ForeignKey('recreation_scenes.id'), nullable=True, comment='关联recreation_scenes表(可选)')
    log_level = db.Column(db.Enum('info', 'warning', 'error'), default='info')
    step_name = db.Column(db.String(100), nullable=False, comment='处理步骤名称')
    message = db.Column(db.Text, comment='日志消息')
    error_details = db.Column(db.Text, comment='错误详情')
    processing_time = db.Column(db.Float, comment='处理耗时(秒)')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'recreation_id': self.recreation_id,
            'scene_id': self.scene_id,
            'log_level': self.log_level,
            'step_name': self.step_name,
            'message': self.message,
            'error_details': self.error_details,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<RecreationLog {self.id}>'