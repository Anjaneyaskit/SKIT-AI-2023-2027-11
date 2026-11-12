"""
Dietary Intake Logging Routes for NutriScan
"""

from datetime import datetime, timezone
import re
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from backend.db import get_db
from backend.auth_utils import jwt_required
from backend.schemas import ALLOWED_MEAL_TYPES

intake_bp = Blueprint('intake', __name__)


def validate_and_enrich_entries(entries_raw, db):
    """Validates each entry and enriches with current food name and nutrients."""
    if not isinstance(entries_raw, list) or len(entries_raw) == 0:
        return False, "At least one food entry is required.", []

    enriched = []
    for idx, e in enumerate(entries_raw):
        if not isinstance(e, dict):
            return False, f"Entry {idx + 1} must be an object.", []

        food_code = (e.get('food_code') or '').strip()
        if not food_code:
            return False, f"Entry {idx + 1}: food_code is required.", []

        food = db.foods.find_one({'code': re.compile(f"^{re.escape(food_code)}$", re.IGNORECASE)})
        if not food:
            return False, f"Entry {idx + 1}: Food with code '{food_code}' does not exist in the database.", []

        try:
            quantity_g = float(e.get('quantity_g', 0))
        except (ValueError, TypeError):
            return False, f"Entry {idx + 1}: quantity_g must be numeric.", []

        if quantity_g <= 0 or quantity_g > 5000:
            return False, f"Entry {idx + 1}: quantity_g must be greater than 0 and less than 5000g.", []

        meal_type = (e.get('meal_type') or 'breakfast').strip().lower()
        if meal_type not in ALLOWED_MEAL_TYPES:
            meal_type = 'breakfast'

        freq = e.get('frequency_per_week')
        if freq is not None:
            try:
                freq = float(freq)
                if not (0.1 <= freq <= 21):
                    freq = 7.0
            except (ValueError, TypeError):
                freq = 7.0

        enriched.append({
            'food_code': food['code'],
            'food_name': food['name'],
            'quantity_g': quantity_g,
            'meal_type': meal_type,
            'frequency_per_week': freq,
            'nutrients': food.get('nutrients', {})
        })

    return True, None, enriched


@intake_bp.route('', methods=['POST'])
@jwt_required
def create_intake():
    data = request.get_json(silent=True) or {}
    user_id = str(g.current_user['id'])
    date_str = (data.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')).strip()

    entries_raw = data.get('entries', [])
    db = get_db()
    is_valid, err_msg, enriched_entries = validate_and_enrich_entries(entries_raw, db)
    if not is_valid:
        return jsonify({'success': False, 'message': err_msg, 'data': None}), 400

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        'user_id': user_id,
        'date': date_str,
        'entries': enriched_entries,
        'created_at': now_iso,
        'updated_at': now_iso
    }

    res = db.intakes.insert_one(record)
    record['_id'] = str(res.inserted_id)

    return jsonify({
        'success': True,
        'message': 'Intake log recorded successfully.',
        'data': {
            'intake': record
        }
    }), 201


@intake_bp.route('', methods=['GET'])
@jwt_required
def get_intakes():
    user_id = str(g.current_user['id'])
    date_filter = request.args.get('date')

    query = {'user_id': user_id}
    if date_filter:
        query['date'] = date_filter.strip()

    db = get_db()
    cursor = db.intakes.find(query).sort('created_at', -1)

    records = []
    for doc in cursor:
        doc['_id'] = str(doc['_id'])
        records.append(doc)

    return jsonify({
        'success': True,
        'message': f"Retrieved {len(records)} intake logs.",
        'data': {
            'count': len(records),
            'intakes': records
        }
    }), 200


@intake_bp.route('/<intake_id>', methods=['PUT'])
@jwt_required
def update_intake(intake_id: str):
    user_id = str(g.current_user['id'])
    data = request.get_json(silent=True) or {}
    db = get_db()

    try:
        filter_q = {'_id': ObjectId(intake_id)}
    except Exception:
        filter_q = {'_id': intake_id}

    existing = db.intakes.find_one(filter_q)
    if not existing:
        return jsonify({'success': False, 'message': 'Intake record not found.', 'data': None}), 404

    if str(existing.get('user_id')) != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized: You do not own this intake record.', 'data': None}), 403

    entries_raw = data.get('entries')
    update_doc = {'updated_at': datetime.now(timezone.utc).isoformat()}

    if 'date' in data:
        update_doc['date'] = str(data['date']).strip()

    if entries_raw is not None:
        is_valid, err_msg, enriched = validate_and_enrich_entries(entries_raw, db)
        if not is_valid:
            return jsonify({'success': False, 'message': err_msg, 'data': None}), 400
        update_doc['entries'] = enriched

    db.intakes.update_one(filter_q, {'$set': update_doc})
    updated_rec = db.intakes.find_one(filter_q)
    updated_rec['_id'] = str(updated_rec['_id'])

    return jsonify({
        'success': True,
        'message': 'Intake record updated successfully.',
        'data': {
            'intake': updated_rec
        }
    }), 200


@intake_bp.route('/<intake_id>', methods=['DELETE'])
@jwt_required
def delete_intake(intake_id: str):
    user_id = str(g.current_user['id'])
    db = get_db()

    try:
        filter_q = {'_id': ObjectId(intake_id)}
    except Exception:
        filter_q = {'_id': intake_id}

    existing = db.intakes.find_one(filter_q)
    if not existing:
        return jsonify({'success': False, 'message': 'Intake record not found.', 'data': None}), 404

    if str(existing.get('user_id')) != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized: You do not own this intake record.', 'data': None}), 403

    db.intakes.delete_one(filter_q)
    return jsonify({
        'success': True,
        'message': 'Intake record deleted successfully.',
        'data': {'deleted_id': intake_id}
    }), 200


@intake_bp.route('/<intake_id>/entry/<int:entry_index>', methods=['DELETE'])
@jwt_required
def delete_intake_entry(intake_id: str, entry_index: int):
    """Deletes a single item entry from a saved intake log."""
    user_id = str(g.current_user['id'])
    db = get_db()
    try:
        filter_q = {'_id': ObjectId(intake_id)}
    except Exception:
        filter_q = {'_id': intake_id}

    existing = db.intakes.find_one(filter_q)
    if not existing:
        return jsonify({'success': False, 'message': 'Intake record not found.', 'data': None}), 404

    if str(existing.get('user_id')) != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized.', 'data': None}), 403

    entries = existing.get('entries', [])
    if 0 <= entry_index < len(entries):
        entries.pop(entry_index)
        if len(entries) == 0:
            db.intakes.delete_one(filter_q)
        else:
            db.intakes.update_one(filter_q, {'$set': {'entries': entries, 'updated_at': datetime.now(timezone.utc).isoformat()}})
        return jsonify({'success': True, 'message': 'Entry deleted successfully.'}), 200

    return jsonify({'success': False, 'message': 'Invalid entry index.'}), 400
