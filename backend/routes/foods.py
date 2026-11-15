"""
Food Catalog & Search Routes for NutriScan
"""

import re
from flask import Blueprint, request, jsonify
from backend.db import get_db

foods_bp = Blueprint('foods', __name__)


@foods_bp.route('', methods=['GET'])
def search_foods():
    query_str = (request.args.get('q') or '').strip()
    try:
        limit = min(int(request.args.get('limit', 20)), 100)
    except (ValueError, TypeError):
        limit = 20

    db = get_db()
    results = []

    if query_str:
        regex_pattern = re.compile(re.escape(query_str), re.IGNORECASE)
        cursor = db.foods.find({'name': {'$regex': regex_pattern}}).limit(limit)
    else:
        cursor = db.foods.find().limit(limit)

    for item in cursor:
        nutrients = item.get('nutrients', {})
        results.append({
            'code': item.get('code'),
            'name': item.get('name'),
            'scie': item.get('scie'),
            'region': item.get('region'),
            'headline_nutrients': {
                'energy_kcal': nutrients.get('energy_kcal', 0.0),
                'protein_g': nutrients.get('protein_g', 0.0),
                'fat_g': nutrients.get('fat_g', 0.0),
                'carbs_g': nutrients.get('carbs_g', 0.0),
                'iron_mg': nutrients.get('iron_mg', 0.0),
                'calcium_mg': nutrients.get('calcium_mg', 0.0)
            }
        })

    return jsonify({
        'success': True,
        'message': f"Found {len(results)} matching foods.",
        'data': {
            'query': query_str,
            'count': len(results),
            'foods': results
        }
    }), 200


@foods_bp.route('/<code>', methods=['GET'])
def get_food_by_code(code: str):
    code_clean = code.strip()
    db = get_db()
    # Case-insensitive code match
    item = db.foods.find_one({'code': re.compile(f"^{re.escape(code_clean)}$", re.IGNORECASE)})
    if not item:
        return jsonify({
            'success': False,
            'message': f"Food item with code '{code}' not found.",
            'data': None
        }), 404

    item['_id'] = str(item['_id'])
    return jsonify({
        'success': True,
        'message': 'Food details retrieved successfully.',
        'data': {
            'food': item
        }
    }), 200
