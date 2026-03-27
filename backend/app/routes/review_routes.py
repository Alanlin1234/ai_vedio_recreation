"""
二创准入审核：POST /api/reviewer/<recreation_id>
结合用户「片子说明」与解析结果，多维度打分后判断是否适合进入二创流程。
"""

import json
import logging

from flask import Blueprint, jsonify, request

from app.models import VideoRecreation, db
from app.services.recreation_review_service import PASS_SCORE, review_for_secondary_creation

logger = logging.getLogger(__name__)

review_bp = Blueprint('review', __name__)


@review_bp.before_request
def _require_login_for_review():
    from flask import session, jsonify

    if request.method == 'OPTIONS':
        return None
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': '请先登录', 'code': 'UNAUTHORIZED'}), 401
    return None


@review_bp.route('/reviewer/<int:recreation_id>', methods=['POST'])
def review_recreation(recreation_id):
    """
    请求体可选 JSON: { "creator_notes": "用户对片子/二创方向的说明" }
    返回: passed, score, scores, summary, message, pass_threshold
    """
    try:
        rec = VideoRecreation.query.get(recreation_id)
        if not rec:
            return jsonify({'success': False, 'passed': False, 'message': '项目不存在'}), 404

        body = request.get_json(silent=True) or {}
        creator_notes = (body.get('creator_notes') or '').strip()
        if creator_notes:
            rec.creator_notes = creator_notes[:12000]
        elif rec.creator_notes:
            creator_notes = (rec.creator_notes or '').strip()

        highlights = (rec.analysis_highlights or '').strip()
        educational = (rec.analysis_educational or '').strip()

        result = review_for_secondary_creation(
            video_understanding=rec.video_understanding or '',
            highlights=highlights,
            educational=educational,
            creator_notes=creator_notes,
        )

        rec.review_score = result.get('overall_score')
        try:
            rec.review_detail_json = json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            rec.review_detail_json = None
        db.session.commit()

        return jsonify(
            {
                'success': True,
                'passed': result.get('passed', False),
                'score': result.get('overall_score'),
                'scores': result.get('scores'),
                'summary': result.get('summary'),
                'suggestions': result.get('suggestions'),
                'message': result.get('message'),
                'pass_threshold': PASS_SCORE,
                'detail': result.get('detail'),
                'debug_prompts': result.get('debug_prompts') or [],
            }
        )
    except Exception as e:
        logger.exception('reviewer: %s', e)
        db.session.rollback()
        return jsonify({'success': False, 'passed': False, 'message': str(e)}), 500
