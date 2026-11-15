"""
Health Check Route for NutriScan
"""

from flask import Blueprint, jsonify
from backend.db import get_db

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    db = get_db()
    db_status = "connected (mock)" if db.is_mock else "connected (live mongodb)"
    return jsonify({
        'success': True,
        'message': 'NutriScan API is operating normally.',
        'data': {
            'status': 'healthy',
            'version': '1.0.0',
            'database': db_status
        }
    }), 200
