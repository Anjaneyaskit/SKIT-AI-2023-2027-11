"""
Authentication Routes for NutriScan
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from backend.db import get_db
from backend.auth_utils import hash_password, verify_password, generate_jwt_token, jwt_required
from backend.schemas import validate_registration

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    is_valid, err_msg = validate_registration(data)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg, 'data': None}), 400

    name = data['name'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    db = get_db()
    existing_user = db.users.find_one({'email': email})
    if existing_user:
        return jsonify({'success': False, 'message': 'An account with this email address already exists.', 'data': None}), 400

    # Calculate initial BMI if height and weight provided
    init_age = data.get('age')
    init_gender = data.get('gender')
    init_h = float(data.get('height_cm') or 0.0)
    init_w = float(data.get('weight_kg') or 0.0)
    init_bmi = round(init_w / ((init_h / 100.0) ** 2), 2) if (init_h > 0 and init_w > 0) else None

    new_user = {
        'name': name,
        'email': email,
        'password_hash': hash_password(password),
        'created_at': datetime.now(timezone.utc).isoformat(),
        'profile': {
            'age': int(init_age) if init_age else None,
            'gender': str(init_gender).lower() if init_gender else None,
            'height_cm': init_h if init_h > 0 else None,
            'weight_kg': init_w if init_w > 0 else None,
            'bmi': init_bmi,
            'bmi_category': 'Normal weight' if init_bmi else None,
            'activity_level': str(data.get('activity_level') or 'sedentary').lower(),
            'diet_preference': str(data.get('diet_preference') or 'veg').lower(),
            'special_condition': str(data.get('special_condition') or 'none').lower(),
            'updated_at': datetime.now(timezone.utc).isoformat() if init_age else None
        }
    }

    insert_result = db.users.insert_one(new_user)
    user_id = str(insert_result.inserted_id)

    token = generate_jwt_token(user_id, email)
    user_payload = {
        'id': user_id,
        'name': name,
        'email': email,
        'profile': new_user['profile']
    }

    return jsonify({
        'success': True,
        'message': 'User registration successful.',
        'data': {
            'token': token,
            'user': user_payload
        }
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'success': False, 'message': 'Both email and password are required.', 'data': None}), 400

    db = get_db()
    user = db.users.find_one({'email': email})
    if not user or not verify_password(password, user.get('password_hash', '')):
        return jsonify({'success': False, 'message': 'Invalid email or password credentials.', 'data': None}), 401

    user_id = str(user['_id'])
    token = generate_jwt_token(user_id, email)

    user_payload = {
        'id': user_id,
        'name': user.get('name', ''),
        'email': user.get('email', ''),
        'profile': user.get('profile', {})
    }

    return jsonify({
        'success': True,
        'message': 'Login successful.',
        'data': {
            'token': token,
            'user': user_payload
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    return jsonify({
        'success': True,
        'message': 'Current user retrieved.',
        'data': {
            'user': g.current_user
        }
    }), 200
