"""
Nutritional Risk Assessment & Screening Routes for NutriScan (Sprint 3 & 4)
Handles questionnaire delivery, symptom intake, and ML risk detection.
"""

import os
import json
from datetime import datetime, timezone
import time
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.services.nutrient_calculator import calculate_intake_summary
from backend.services.recommender import get_recommender_service
from backend.services.llm_service import get_llm_service
from ml.config import QUESTIONNAIRE_PATH, TARGET_NUTRIENTS
from ml.predict import predict_all

assessment_bp = Blueprint('assessment', __name__)


@assessment_bp.route('/questionnaire', methods=['GET'])
def get_symptom_questionnaire():
    """Serves the standardized clinical symptom screening questions."""
    if os.path.exists(QUESTIONNAIRE_PATH):
        with open(QUESTIONNAIRE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'questions': []}

    return jsonify({
        'success': True,
        'message': 'Symptom questionnaire retrieved successfully.',
        'data': data
    }), 200


@assessment_bp.route('/symptoms', methods=['POST'])
@jwt_required
def save_symptoms():
    """Saves user's symptom responses (0-4 scale)."""
    data = request.get_json(silent=True) or {}
    symptoms = data.get('symptoms') or data.get('answers') or {}

    if not isinstance(symptoms, dict) or not symptoms:
        return jsonify({'success': False, 'message': 'Symptom responses dictionary is required.', 'data': None}), 400

    user_id = str(g.current_user['id'])
    db = get_db()

    # Save to user document or dedicated symptom log
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        'user_id': user_id,
        'symptoms': symptoms,
        'symptoms_saved': len(symptoms),
        'updated_at': now_iso
    }

    try:
        filter_q = {'_id': ObjectId(user_id)}
    except Exception:
        filter_q = {'_id': user_id}

    db.users.update_one(filter_q, {'$set': {'latest_symptoms': symptoms, 'symptoms_updated_at': now_iso}})

    return jsonify({
        'success': True,
        'message': 'Symptom responses saved successfully.',
        'data': record
    }), 200


@assessment_bp.route('/run', methods=['POST'])
@jwt_required
def run_nutritional_assessment():
    """
    Executes end-to-end nutritional assessment pipeline (Target latency < 3s, NFR-001):
      1. Profile Demographics & Anthropometrics
      2. Intake Aggregation & Nutrient Total Calculations
      3. ICMR-NIN 2020 RDA Benchmarking
      4. ML Risk Classification & SHAP Feature Attribution
      5. Food Recommendations & Absorption Pairing Tips
      6. Persists to 'assessments' collection
    """
    start_time = time.time()
    user = g.current_user
    user_id = str(user['id'])
    profile = user.get('profile', {})

    if not profile or not profile.get('age') or not profile.get('gender'):
        return jsonify({
            'success': False,
            'message': 'Please complete your demographic profile (age, gender, height, weight) before running assessment.',
            'data': None
        }), 400

    data = request.get_json(silent=True) or {}
    date_str = (data.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')).strip()
    variant = data.get('variant', 'A').upper()  # 'A' = real NHANES baseline, 'B' = prototype

    db = get_db()

    # Gather user's dietary entries for the target date
    intake_records = list(db.intakes.find({'user_id': user_id, 'date': date_str}))
    entries = []
    for doc in intake_records:
        for entry in doc.get('entries', []):
            entries.append(entry)

    if not entries:
        return jsonify({
            'success': False,
            'message': f"No meals logged for {date_str}. Please log at least one food before running assessment.",
            'data': None
        }), 400

    # 1. Compute nutrient totals and % of RDA
    summary = calculate_intake_summary(
        entries=entries,
        user_gender=profile.get('gender'),
        user_age=profile.get('age'),
        special_condition=profile.get('special_condition', 'none')
    )

    nutrient_totals = {k: v['total_amount'] for k, v in summary['nutrients'].items()}

    # 2. Retrieve latest symptom scores
    symptoms = user.get('latest_symptoms', {})
    if data.get('symptoms'):
        symptoms.update(data['symptoms'])

    # 3. Execute ML Risk Prediction + SHAP Attribution
    ml_predictions = predict_all(
        profile=profile,
        nutrient_totals=nutrient_totals,
        symptoms=symptoms,
        variant=variant
    )

    # 4. Generate Targeted Food Recommendations & Antinutrient Alerts
    recommender = get_recommender_service()
    recommendation_package = recommender.get_full_recommendation_package(
        risk_assessment=ml_predictions,
        user_diet=profile.get('diet_preference', 'veg'),
        gender=profile.get('gender', 'male'),
        age=profile.get('age', 25)
    )

    # 5. Generate AI Plain-Language Coaching Summaries
    llm = get_llm_service()
    coaching_notes = {}
    for nut_key, rec_data in recommendation_package.get('recommendations', {}).items():
        pred_item = ml_predictions.get(nut_key, {})
        top_food_names = [f['food_name'] for f in rec_data.get('top_foods', [])]
        coaching_notes[nut_key] = llm.generate_coaching_explanation(
            nutrient_key=nut_key,
            risk_level=pred_item.get('predicted_risk_label', 'Moderate Risk'),
            rda_percent=pred_item.get('rda_percent'),
            shap_factors=pred_item.get('shap_top_factors', []),
            recommended_foods=top_food_names
        )

    duration_sec = round(time.time() - start_time, 3)

    # 6. Save Assessment Record
    now_iso = datetime.now(timezone.utc).isoformat()
    assessment_doc = {
        'user_id': user_id,
        'date': date_str,
        'created_at': now_iso,
        'duration_seconds': duration_sec,
        'model_variant': variant,
        'user_profile_snapshot': profile,
        'nutrient_totals': nutrient_totals,
        'summary': summary,
        'risk_predictions': ml_predictions,
        'recommendations': recommendation_package,
        'coaching_notes': coaching_notes
    }

    insert_res = db.assessments.insert_one(assessment_doc)
    doc_id = str(insert_res.inserted_id)
    assessment_doc['_id'] = doc_id
    assessment_doc['assessment_id'] = doc_id
    assessment_doc['results'] = ml_predictions

    return jsonify({
        'success': True,
        'message': f"Nutritional screening completed in {duration_sec}s.",
        'data': assessment_doc
    }), 201


@assessment_bp.route('/latest', methods=['GET'])
@jwt_required
def get_latest_assessment():
    """Retrieves the most recent assessment for the logged-in user."""
    user_id = str(g.current_user['id'])
    db = get_db()
    latest = db.assessments.find_one({'user_id': user_id}, sort=[('created_at', -1)])
    if not latest:
        return jsonify({
            'success': False,
            'message': 'No assessments found for this user.',
            'data': None
        }), 404

    latest['_id'] = str(latest['_id'])
    latest['id'] = str(latest['_id'])
    return jsonify({
        'success': True,
        'message': 'Latest assessment retrieved.',
        'data': latest
    }), 200


@assessment_bp.route('/<assessment_id>', methods=['GET'])
@jwt_required
def get_assessment_by_id(assessment_id: str):
    """Retrieves a specific assessment by ObjectId."""
    user_id = str(g.current_user['id'])
    db = get_db()
    try:
        filter_q = {'_id': ObjectId(assessment_id)}
    except Exception:
        filter_q = {'_id': assessment_id}

    item = db.assessments.find_one(filter_q)
    if not item or str(item.get('user_id')) != user_id:
        return jsonify({
            'success': False,
            'message': 'Assessment record not found or unauthorized.',
            'data': None
        }), 404

    item['_id'] = str(item['_id'])
    item['id'] = str(item['_id'])
    return jsonify({
        'success': True,
        'message': 'Assessment retrieved.',
        'data': item
    }), 200
