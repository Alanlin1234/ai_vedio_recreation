"""登录 / 会话"""
from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash

from app.models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    if not username or not password:
        return jsonify({'success': False, 'error': '请输入用户名和密码'}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session.permanent = True

    return jsonify(
        {
            'success': True,
            'user': user.to_public(),
        }
    )


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/me', methods=['GET'])
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'success': True, 'authenticated': False, 'user': None})

    user = User.query.get(uid)
    if not user:
        session.clear()
        return jsonify({'success': True, 'authenticated': False, 'user': None})

    return jsonify(
        {
            'success': True,
            'authenticated': True,
            'user': user.to_public(),
        }
    )
