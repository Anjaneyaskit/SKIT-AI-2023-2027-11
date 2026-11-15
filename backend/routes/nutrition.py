"""
Nutrition Analysis & Calculation Routes for NutriScan
"""

import os
from datetime import datetime, timezone
import re
from flask import Blueprint, request, jsonify, g
from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.services.nutrient_calculator import calculate_intake_summary
from backend.services.rda_service import get_rda_service

nutrition_bp = Blueprint('nutrition', __name__)


@nutrition_bp.route('/calculate', methods=['POST'])
def calculate_on_the_fly():
    """Calculates nutrient totals for an ad-hoc set of foods and quantities."""
    data = request.get_json(silent=True) or {}
    entries_raw = data.get('entries', [])
    if not isinstance(entries_raw, list) or len(entries_raw) == 0:
        return jsonify({'success': False, 'message': 'At least one food entry is required.', 'data': None}), 400

    gender = data.get('gender')
    age = data.get('age')
    special_cond = data.get('special_condition', 'none')

    db = get_db()
    enriched_entries = []
    for idx, e in enumerate(entries_raw):
        code = (e.get('food_code') or '').strip()
        quantity_g = float(e.get('quantity_g', 0.0) or 0.0)
        freq = e.get('frequency_per_week')

        food = db.foods.find_one({'code': re.compile(f"^{re.escape(code)}$", re.IGNORECASE)}) if code else None
        if not food:
            return jsonify({'success': False, 'message': f"Food with code '{code}' not found.", 'data': None}), 400

        enriched_entries.append({
            'food_code': food['code'],
            'food_name': food['name'],
            'quantity_g': quantity_g,
            'frequency_per_week': freq,
            'nutrients': food.get('nutrients', {})
        })

    summary = calculate_intake_summary(
        entries=enriched_entries,
        user_gender=gender,
        user_age=int(age) if age is not None else None,
        special_condition=special_cond
    )

    return jsonify({
        'success': True,
        'message': 'Nutrient calculations computed successfully.',
        'data': summary
    }), 200


@nutrition_bp.route('/summary', methods=['GET'])
@jwt_required
def get_user_daily_summary():
    """Aggregates all intake records for current user on given date and benchmarks vs RDA."""
    user = g.current_user
    user_id = str(user['id'])
    profile = user.get('profile', {})

    date_str = (request.args.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')).strip()
    db = get_db()

    intakes_cursor = db.intakes.find({'user_id': user_id, 'date': date_str})
    all_entries = []
    for doc in intakes_cursor:
        for entry in doc.get('entries', []):
            all_entries.append(entry)

    age = profile.get('age')
    gender = profile.get('gender')
    special_condition = profile.get('special_condition', 'none')

    summary = calculate_intake_summary(
        entries=all_entries,
        user_gender=gender,
        user_age=int(age) if age is not None else None,
        special_condition=special_condition
    )

    return jsonify({
        'success': True,
        'message': f"Nutritional summary computed for {date_str}.",
        'data': {
            'date': date_str,
            'user_profile': {
                'gender': gender,
                'age': age,
                'bmi': profile.get('bmi'),
                'bmi_category': profile.get('bmi_category'),
                'activity_level': profile.get('activity_level')
            },
            'summary': summary
        }
    }), 200
