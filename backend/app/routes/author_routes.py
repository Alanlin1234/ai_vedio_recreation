from flask import Blueprint, request, jsonify
from app.services.author_service import AuthorService

author_bp = Blueprint('author', __name__)

# @author_bp.route('/authors', methods=['POST'])
# def add_author():
#     data = request.get_json()
#     try:
#         author_id = AuthorService.create_author(data)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# def get_author(uid):
#     try:
#         author = AuthorService.get_author_by_uid(uid)
#         if not author:
#             return jsonify({'error': '作者不存在'}), 404
#         return jsonify(author)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# def update_author(uid):
#     data = request.get_json()
#     try:
#         AuthorService.update_author(uid, data)
#         return jsonify({'success': True})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@author_bp.route('/authors/<uid>', methods=['DELETE'])
def delete_author(uid):
    try:
        AuthorService.delete_author(uid)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@author_bp.route('/authors', methods=['GET'])
def get_authors():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        result = AuthorService.get_authors_paginated(page, per_page)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
