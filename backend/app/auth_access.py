"""鉴权：Supabase JWT 或旧版 Flask session。"""
import jwt
from flask import current_app, g, jsonify, request, session


def supabase_jwt_enabled(app=None):
    app = app or current_app
    return bool(app.config.get("SUPABASE_JWT_SECRET"))


def decode_supabase_jwt(token: str):
    secret = current_app.config.get("SUPABASE_JWT_SECRET")
    if not secret or not token:
        return None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.InvalidAudienceError:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.PyJWTError:
            return None
    except jwt.PyJWTError:
        return None


def apply_principal():
    """填充 g.supabase_uid / g.user_email / g.is_admin / g.legacy_user_id"""
    g.supabase_uid = None
    g.user_email = None
    g.is_admin = False
    g.legacy_user_id = None

    if supabase_jwt_enabled():
        token = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
        elif request.method == "GET":
            token = (request.args.get("access_token") or "").strip() or None
        if token:
            payload = decode_supabase_jwt(token)
            if payload:
                g.supabase_uid = payload.get("sub")
                g.user_email = payload.get("email")
                meta = payload.get("app_metadata") or {}
                g.is_admin = meta.get("role") == "admin"
        return

    uid = session.get("user_id")
    if uid is not None:
        g.legacy_user_id = uid


def require_authenticated_response():
    """未登录则返回 (response, status)，否则 None"""
    if request.method == "OPTIONS":
        return None
    apply_principal()
    if supabase_jwt_enabled():
        if g.supabase_uid:
            return None
        return (
            jsonify({"success": False, "error": "请先登录", "code": "UNAUTHORIZED"}),
            401,
        )
    if g.legacy_user_id:
        return None
    return (
        jsonify({"success": False, "error": "请先登录", "code": "UNAUTHORIZED"}),
        401,
    )


def can_access_recreation(rec) -> bool:
    if not rec:
        return False
    uid = getattr(g, "supabase_uid", None)
    if uid:
        owner = getattr(rec, "owner_supabase_uid", None)
        if not owner:
            return True
        return owner == uid or getattr(g, "is_admin", False)
    return getattr(g, "legacy_user_id", None) is not None


def forbidden_recreation_response():
    return (
        jsonify({"success": False, "error": "无权访问该项目", "code": "FORBIDDEN"}),
        403,
    )
