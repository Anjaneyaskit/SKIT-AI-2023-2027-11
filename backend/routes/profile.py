"""
User Profile Management Routes for NutriScan
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.schemas import validate_profile

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('', methods=['GET'])
@jwt_required
def get_profile():
    user = g.current_user
    return jsonify({
        'success': True,
        'message': 'User profile retrieved successfully.',
        'data': {
            'profile': user.get('profile', {})
        }
    }), 200


@profile_bp.route('', methods=['PUT'])
@jwt_required
def update_profile():
    data = request.get_json(silent=True) or {}
    is_valid, err_msg, cleaned_profile = validate_profile(data)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg, 'data': None}), 400

    cleaned_profile['updated_at'] = datetime.now(timezone.utc).isoformat()

    db = get_db()
    user_id = g.current_user['id']

    try:
        filter_q = {'_id': ObjectId(user_id)}
    except Exception:
        filter_q = {'_id': user_id}

    db.users.update_one(filter_q, {'$set': {'profile': cleaned_profile}})

    return jsonify({
        'success': True,
        'message': 'Profile updated successfully.',
        'data': {
            'profile': cleaned_profile
        }
    }), 200
