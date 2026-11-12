"""
History, Trend Analysis, and NLP Parsing Routes for NutriScan (Sprint 4 & Phase N)
"""

from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.services.llm_service import get_llm_service

history_bp = Blueprint('history', __name__)


import math

@history_bp.route('', methods=['GET'])
@jwt_required
def get_user_history():
    """Returns paginated assessment history for the user."""
    user_id = str(g.current_user['id'])
    try:
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(int(request.args.get('limit', 10)), 50)
    except (ValueError, TypeError):
        page, limit = 1, 10

    skip = (page - 1) * limit
    db = get_db()

    total_count = db.assessments.count_documents({'user_id': user_id})
    cursor = db.assessments.find({'user_id': user_id}).sort('created_at', -1).skip(skip).limit(limit)

    records = []
    for doc in cursor:
        doc_id = str(doc['_id'])
        preds = doc.get('risk_predictions', {})

        high_risk = [k.replace('_g', '').replace('_mg', '').replace('_ug', '') for k, v in preds.items() if v.get('predicted_risk_label') == 'High Risk']
        mod_risk = [k.replace('_g', '').replace('_mg', '').replace('_ug', '') for k, v in preds.items() if v.get('predicted_risk_label') == 'Moderate Risk']

        rda_pcts = [v.get('rda_percent') for v in preds.values() if v.get('rda_percent') is not None]
        avg_rda = sum(rda_pcts) / len(rda_pcts) if rda_pcts else 0.0

        records.append({
            '_id': doc_id,
            'id': doc_id,
            'date': doc.get('date'),
            'timestamp': doc.get('created_at') or doc.get('date'),
            'created_at': doc.get('created_at') or doc.get('date'),
            'model_variant': doc.get('model_variant', 'Variant A (NHANES)'),
            'calories': doc.get('nutrient_totals', {}).get('energy_kcal', 0.0),
            'protein': doc.get('nutrient_totals', {}).get('protein_g', 0.0),
            'high_risk': high_risk,
            'moderate_risk': mod_risk,
            'avg_rda_pct': round(avg_rda, 1),
            'risk_summary': {k: v.get('predicted_risk_label') for k, v in preds.items()},
            'results': preds,
            'nutrient_totals': doc.get('nutrient_totals', {})
        })

    total_pages = max(math.ceil(total_count / limit), 1)

    return jsonify({
        'success': True,
        'message': f"Retrieved page {page} of assessment history.",
        'assessments': records,
        'total_pages': total_pages,
        'total_count': total_count,
        'data': {
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'total_pages': total_pages,
            'assessments': records
        }
    }), 200


@history_bp.route('/daily-meals', methods=['GET'])
@jwt_required
def get_daily_meal_history():
    """Returns day-wise aggregated meal intake logs for the user."""
    user_id = str(g.current_user['id'])
    db = get_db()
    cursor = db.intakes.find({'user_id': user_id}).sort('date', -1)

    daily_logs = {}
    for doc in cursor:
        d = doc.get('date', 'Unknown')
        if d not in daily_logs:
            daily_logs[d] = {
                'date': d,
                'entries': [],
                'total_items': 0,
                'total_calories': 0.0,
                'total_protein': 0.0,
                'total_carbs': 0.0,
                'total_fat': 0.0,
                'created_at': doc.get('created_at')
            }
        for entry in doc.get('entries', []):
            qty = float(entry.get('quantity_g', 100.0) or 100.0)
            nutr = entry.get('nutrients', {})
            factor = qty / 100.0
            cal = float(nutr.get('energy_kcal', 0.0) or 0.0) * factor
            prot = float(nutr.get('protein_g', 0.0) or 0.0) * factor
            carbs = float(nutr.get('carbs_g', 0.0) or 0.0) * factor
            fat = float(nutr.get('fat_g', 0.0) or 0.0) * factor

            daily_logs[d]['entries'].append({
                'food_code': entry.get('food_code'),
                'food_name': entry.get('food_name'),
                'meal_type': entry.get('meal_type', 'lunch'),
                'quantity_g': qty,
                'calories': round(cal, 1),
                'protein_g': round(prot, 1)
            })
            daily_logs[d]['total_items'] += 1
            daily_logs[d]['total_calories'] += cal
            daily_logs[d]['total_protein'] += prot
            daily_logs[d]['total_carbs'] += carbs
            daily_logs[d]['total_fat'] += fat

    result_list = []
    for d, info in daily_logs.items():
        info['total_calories'] = round(info['total_calories'], 1)
        info['total_protein'] = round(info['total_protein'], 1)
        info['total_carbs'] = round(info['total_carbs'], 1)
        info['total_fat'] = round(info['total_fat'], 1)
        result_list.append(info)

    return jsonify({
        'success': True,
        'message': f"Retrieved {len(result_list)} days of meal logs.",
        'data': {
            'days': result_list,
            'count': len(result_list)
        }
    }), 200


@history_bp.route('/trend', methods=['GET'])
@jwt_required
def get_nutrient_trend():
    """Returns longitudinal time-series data for a specific target nutrient."""
    user_id = str(g.current_user['id'])
    nutrient = request.args.get('nutrient', 'protein_g').strip()

    db = get_db()
    cursor = db.assessments.find({'user_id': user_id}).sort('created_at', 1)

    timeline = []
    for doc in cursor:
        pred_item = doc.get('risk_predictions', {}).get(nutrient, {})
        timeline.append({
            'date': doc.get('date'),
            'created_at': doc.get('created_at'),
            'total_intake': pred_item.get('total_intake', doc.get('nutrient_totals', {}).get(nutrient, 0.0)),
            'rda_percent': pred_item.get('rda_percent'),
            'risk_label': pred_item.get('predicted_risk_label', 'Unknown')
        })

    return jsonify({
        'success': True,
        'message': f"Retrieved trend data for {nutrient}.",
        'data': {
            'nutrient': nutrient,
            'count': len(timeline),
            'timeline': timeline,
            'data_points': timeline
        }
    }), 200


@history_bp.route('/nlp/parse-meal', methods=['POST'])
def parse_natural_language_meal():
    """
    Feature N1: Natural language free-text meal parser.
    Uses LLM entity extraction with fuzzy matching and Indian household gram conversions.
    """
    data = request.get_json(silent=True) or {}
    meal_text = (data.get('meal_text') or data.get('text') or '').strip()

    if not meal_text or len(meal_text) < 3:
        return jsonify({
            'success': False,
            'message': 'Please enter a valid meal description (e.g. 2 rotis, 1 katori dal and a banana).',
            'data': None
        }), 400

    db = get_db()
    llm = get_llm_service()
    result = llm.parse_free_text_meal(meal_text, db=db)
    result['matched_items'] = result.get('resolved_foods', [])

    return jsonify({
        'success': True,
        'message': f"Parsed {result['items_parsed']} food items.",
        'data': result
    }), 200
