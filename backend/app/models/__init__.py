from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .author import DouyinAuthor
from .video import DouyinVideo
from .video_recreation import VideoRecreation, RecreationScene, RecreationLog
__all__ = ['db', 'DouyinAuthor', 'DouyinVideo', 'VideoRecreation', 'RecreationScene', 'RecreationLog']