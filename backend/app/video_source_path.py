"""原始视频：本地路径或从 Storage 下载缓存。"""
import os

from flask import current_app

from app.models import db
from app.supabase_storage import download_object, storage_configured


def ensure_local_original_video(rec):
    """返回可读本地文件路径，失败返回 None。"""
    if not rec:
        return None
    path = rec.original_video_path
    if path and os.path.isfile(path):
        return path
    key = getattr(rec, "original_video_storage_key", None)
    if not key or not storage_configured():
        return None
    upload_root = current_app.config["UPLOAD_FOLDER"]
    owner = getattr(rec, "owner_supabase_uid", None) or "legacy"
    cache_dir = os.path.join(upload_root, "user_videos", str(owner), str(rec.id))
    os.makedirs(cache_dir, exist_ok=True)
    ext = os.path.splitext(key)[1] or ".mp4"
    dest = os.path.join(cache_dir, f"source{ext}")
    bucket = current_app.config["SUPABASE_STORAGE_BUCKET"]
    if download_object(bucket, key, dest):
        rec.original_video_path = dest
        db.session.commit()
        return dest
    return None
