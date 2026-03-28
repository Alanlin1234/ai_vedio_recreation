"""按 recreation_id 取项目并校验当前用户是否有权访问。"""
from flask import jsonify

from app.auth_access import can_access_recreation, forbidden_recreation_response
from app.models import VideoRecreation


def recreation_for_request(recreation_id):
    recreation = VideoRecreation.query.get(recreation_id)
    if not recreation:
        return None, (jsonify({"success": False, "error": "项目不存在"}), 404)
    if not can_access_recreation(recreation):
        return None, forbidden_recreation_response()
    return recreation, None
