"""
Dietary Recommendations Route for NutriScan (Sprint 4 Phase L Deliverable)
Endpoint: GET /api/recommendations?assessment_id=
Returns ranked IFCT 2017 foods, typical portion sizes, % RDA per serving, antinutrient alerts, and pairing advice.
"""

from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.services.recommender import get_recommender_service

recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('', methods=['GET'])
@jwt_required
def get_recommendations():
    """
    Retrieves targeted IFCT food recommendations for deficient nutrients.
    Query param: assessment_id (optional, defaults to user's latest assessment)
    """
    user = g.current_user
    user_id = str(user['id'])
    assessment_id = request.args.get('assessment_id')

    db = get_db()

    if assessment_id:
        try:
            filter_q = {'_id': ObjectId(assessment_id)}
        except Exception:
            filter_q = {'_id': assessment_id}
        assessment = db.assessments.find_one(filter_q)
    else:
        assessment = db.assessments.find_one({'user_id': user_id}, sort=[('created_at', -1)])

    if not assessment:
        return jsonify({
            'success': False,
            'message': 'No assessment found. Please run an assessment first.',
            'data': None
        }), 404

    # Check authorization
    if str(assessment.get('user_id')) != user_id:
        return jsonify({
            'success': False,
            'message': 'Unauthorized access to assessment recommendations.',
            'data': None
        }), 403

    recommender = get_recommender_service()
    profile = assessment.get('user_profile_snapshot') or user.get('profile', {})
    diet = (request.args.get('diet') or profile.get('diet_preference', 'all')).strip().lower()
    gender = profile.get('gender', 'male')
    age = int(profile.get('age', 25) or 25)
    risk_preds = assessment.get('risk_predictions', {})

    # Re-compute recommendations if diet param specified or not yet generated
    if request.args.get('diet') or not assessment.get('recommendations'):
        package = recommender.get_full_recommendation_package(
            risk_assessment=risk_preds,
            user_diet=diet,
            gender=gender,
            age=age
        )
        recs_dict = package.get('recommendations', {})
    else:
        stored_recs = assessment.get('recommendations', {})
        if isinstance(stored_recs, dict) and 'recommendations' in stored_recs:
            recs_dict = stored_recs['recommendations']
        elif isinstance(stored_recs, dict):
            recs_dict = stored_recs
        else:
            recs_dict = {}

    def normalize_rec_item(nut_key, item):
        pred = risk_preds.get(nut_key, {})
        u_intake = item.get('user_intake')
        if u_intake is None or u_intake == 'NaN':
            u_intake = pred.get('total_intake', 0.0)
        u_rda = item.get('user_rda')
        if u_rda is None or u_rda == 'NaN':
            u_rda = pred.get('rda_value', 0.0)
        u_pct = item.get('rda_percent')
        if u_pct is None or u_pct == 'NaN':
            u_pct = pred.get('rda_percent', 0.0)

        tips = item.get('clinical_pairing_tips', [])
        synergy_tip = item.get('synergy_tip') or (tips[0] if tips else '')

        raw_foods = item.get('foods') or item.get('top_foods') or []
        normalized_foods = []
        for f in raw_foods:
            clean_name = (f.get('name') or f.get('food_name') or '').split(',')[0].strip()
            diet_cat = f.get('diet_category') or f.get('diet_type') or 'vegan'
            portion = float(f.get('typical_portion_g') or f.get('typical_serving_g') or 100.0)
            yield_val = float(f.get('yield_per_serving') or f.get('nutrient_per_serving') or 0.0)
            rda_pct = float(f.get('percent_daily_rda') or f.get('rda_pct_per_serving') or 0.0)

            normalized_foods.append({
                'food_code': f.get('food_code', ''),
                'name': clean_name,
                'food_name': f.get('food_name') or clean_name,
                'category': f.get('category') or f.get('region') or 'IFCT 2017 Food',
                'region': f.get('region', 'All India'),
                'diet_type': diet_cat,
                'diet_category': diet_cat,
                'typical_portion_g': portion,
                'typical_serving_g': portion,
                'yield_per_serving': yield_val,
                'nutrient_per_serving': yield_val,
                'percent_daily_rda': rda_pct,
                'rda_pct_per_serving': rda_pct,
                'unit': f.get('unit', item.get('unit', '')),
                'antinutrient_note': f.get('antinutrient_note')
            })

        return {
            'nutrient_key': nut_key,
            'nutrient_name': item.get('nutrient_name', nut_key),
            'unit': item.get('unit', ''),
            'risk_level': item.get('risk_level') or pred.get('predicted_risk_label', 'Flagged Deficiency'),
            'user_intake': round(float(u_intake or 0.0), 2),
            'user_rda': round(float(u_rda or 0.0), 2),
            'rda_percent': round(float(u_pct or 0.0), 1),
            'synergy_tip': synergy_tip,
            'clinical_pairing_tips': tips or ([synergy_tip] if synergy_tip else []),
            'foods': normalized_foods,
            'top_foods': normalized_foods
        }

    # Normalize flagged recommendations
    normalized_recs = {}
    for k, v in recs_dict.items():
        normalized_recs[k] = normalize_rec_item(k, v)

    # Also build full catalog across all 6 target nutrients for exploratory browsing
    all_nutrients_catalog = recommender.get_all_nutrient_recommendations(
        user_diet=diet, gender=gender, age=age, limit=6
    )
    for k, v in all_nutrients_catalog.items():
        all_nutrients_catalog[k] = normalize_rec_item(k, v)

    totals = assessment.get('nutrient_totals', {})

    return jsonify({
        'success': True,
        'message': 'Recommendations retrieved successfully.',
        'data': {
            'assessment_id': str(assessment['_id']),
            'assessment_date': assessment.get('date'),
            'diet_preference': diet,
            'user_profile': {
                'gender': gender,
                'age': age,
                'diet_preference': profile.get('diet_preference', 'all')
            },
            'daily_summary': {
                'calories': totals.get('energy_kcal', 0.0),
                'protein': totals.get('protein_g', 0.0)
            },
            'deficient_nutrients_count': len(normalized_recs),
            'recommendations': normalized_recs,
            'all_nutrients': all_nutrients_catalog
        }
    }), 200
