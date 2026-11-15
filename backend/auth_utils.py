"""
Authentication and JWT Utilities for NutriScan
Handles secure password hashing (scrypt via Werkzeug) and JWT issuance / verification.
"""

from datetime import datetime, timezone
from functools import wraps
from typing import Optional, Dict, Any
from flask import request, jsonify, g
import jwt
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from backend.db import get_db


def hash_password(password: str) -> str:
    """Hashes a plaintext password securely."""
    return generate_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a stored hash."""
    return check_password_hash(hashed_password, plain_password)


def generate_jwt_token(user_id: str, email: str) -> str:
    """Issues a signed JWT token valid for the configured duration."""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user_id),
        'email': email,
        'iat': now,
        'exp': now + Config.JWT_EXPIRATION
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def jwt_required(f):
    """
    Decorator to protect API routes requiring valid JWT authentication.
    Injects g.current_user with the user document from the database.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': 'Missing or invalid Authorization header. Expected Bearer token.',
                'data': None
            }), 401

        token = auth_header.split(' ', 1)[1].strip()
        payload = decode_jwt_token(token)
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Token has expired or is invalid. Please log in again.',
                'data': None
            }), 401

        user_id = payload.get('sub')
        db = get_db()
        try:
            # Query by ObjectId or string id
            user = db.users.find_one({'_id': ObjectId(user_id)})
            if not user:
                user = db.users.find_one({'_id': user_id})
        except Exception:
            user = db.users.find_one({'_id': user_id})

        if not user:
            return jsonify({
                'success': False,
                'message': 'User associated with this token no longer exists.',
                'data': None
            }), 401

        user_str_id = str(user['_id'])
        user['_id'] = user_str_id
        user['id'] = user_str_id
        user.pop('password_hash', None)
        g.current_user = user
        return f(*args, **kwargs)

    return decorated_function
