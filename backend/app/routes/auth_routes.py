"""登录 / 会话：未配置 SUPABASE_JWT_SECRET 时使用本地用户表 + session；已配置时 /me 校验 Bearer。"""
from flask import Blueprint, g, jsonify, request, session
from werkzeug.security import check_password_hash

from app.auth_access import apply_principal, supabase_jwt_enabled
from app.models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    if supabase_jwt_enabled():
        return (
            jsonify(
                {
                    "success": False,
                    "error": "已启用 Supabase 登录，请使用邮箱密码在前端登录",
                }
            ),
            400,
        )
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"success": False, "error": "请输入用户名和密码"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "error": "用户名或密码错误"}), 401

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    session.permanent = True

    return jsonify({"success": True, "user": user.to_public()})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/me", methods=["GET"])
def me():
    if supabase_jwt_enabled():
        apply_principal()
        if not g.supabase_uid:
            return jsonify({"success": True, "authenticated": False, "user": None})
        display = g.user_email or g.supabase_uid[:8]
        return jsonify(
            {
                "success": True,
                "authenticated": True,
                "user": {
                    "id": g.supabase_uid,
                    "email": g.user_email,
                    "username": display,
                    "role": "admin" if g.is_admin else "user",
                },
            }
        )

    uid = session.get("user_id")
    if not uid:
        return jsonify({"success": True, "authenticated": False, "user": None})

    user = User.query.get(uid)
    if not user:
        session.clear()
        return jsonify({"success": True, "authenticated": False, "user": None})

    return jsonify(
        {"success": True, "authenticated": True, "user": user.to_public()}
    )
