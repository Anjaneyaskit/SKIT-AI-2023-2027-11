"""
Unit and Integration Tests for Assessment Pipeline and Recommendation Engine
(Sprint 3 Phase K, Sprint 4 Phase L & M)
"""

import pytest
from backend.app import create_app
from backend.services.recommender import (
    get_recommender_service,
    classify_food_dietary_category,
    PAIRING_TIPS
)


@pytest.fixture
def app():
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture
def client(app):
    return app.test_client()


import uuid

@pytest.fixture
def auth_token(client):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@nutriscan.org"
    register_res = client.post('/api/auth/register', json={
        "name": "Clinical Test User",
        "email": unique_email,
        "password": "Password123!",
        "age": 28,
        "gender": "female",
        "height_cm": 160.0,
        "weight_kg": 52.0,
        "activity_level": "moderate",
        "diet_preference": "veg"
    })
    assert register_res.status_code == 201
    token = register_res.get_json()['data']['token']

    # Explicitly ensure profile is saved
    client.put('/api/profile', json={
        "age": 28,
        "gender": "female",
        "height_cm": 160.0,
        "weight_kg": 52.0,
        "activity_level": "moderate",
        "diet_preference": "veg",
        "special_condition": "none"
    }, headers={"Authorization": f"Bearer {token}"})

    return token


def test_questionnaire_endpoint(client):
    """Verify standard 12-question screening questionnaire is served."""
    res = client.get('/api/assessment/questionnaire')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'scale' in data['data']
    questions = data['data']['questions']
    assert len(questions) == 12


def test_submit_symptoms_endpoint(client, auth_token):
    """Verify symptoms submission and persistence."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    sample_symptoms = {
        "fatigue_pallor": 3,
        "cold_sensitivity": 2,
        "bone_joint_pain": 1,
        "muscle_weakness": 0,
        "numbness_tingling": 1,
        "mouth_ulcers": 2,
        "easy_bruising": 0,
        "slow_wound_healing": 1,
        "hair_thinning": 2,
        "frequent_infections": 0,
        "muscle_loss": 1,
        "edema": 0
    }

    res = client.post('/api/assessment/symptoms', json={"answers": sample_symptoms}, headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['symptoms_saved'] == 12


def test_assessment_run_endpoint(client, auth_token):
    """Verify complete end-to-end assessment execution."""
    headers = {"Authorization": f"Bearer {auth_token}"}

    # 1. Log a meal first
    intake_res = client.post('/api/intake', json={
        "date": "2026-10-25",
        "entries": [
            {"food_code": "A001", "food_name": "Bajra", "quantity_g": 100, "meal_type": "lunch", "frequency_per_week": 7},
            {"food_code": "B014", "food_name": "Moong dal", "quantity_g": 60, "meal_type": "lunch", "frequency_per_week": 7}
        ]
    }, headers=headers)
    assert intake_res.status_code in (200, 201)

    # 2. Run assessment
    res = client.post('/api/assessment/run', json={"date": "2026-10-25", "variant": "A"}, headers=headers)
    assert res.status_code in (200, 201)
    data = res.get_json()
    assert data['success'] is True
    
    results = data['data']['results']
    assert 'iron_mg' in results
    assert 'protein_g' in results
    assert 'calcium_mg' in results

    # Verify risk classes are valid
    valid_classes = {"Low Risk", "Moderate Risk", "High Risk"}
    for nutrient, n_res in results.items():
        assert n_res['predicted_risk_label'] in valid_classes
        assert 'class_probabilities' in n_res
        assert 'shap_top_factors' in n_res
        assert isinstance(n_res['shap_top_factors'], list)

    assessment_id = data['data']['assessment_id']
    assert assessment_id is not None

    # 3. Retrieve assessment by ID
    get_res = client.get(f'/api/assessment/{assessment_id}', headers=headers)
    assert get_res.status_code == 200
    assert get_res.get_json()['data']['id'] == assessment_id

    # 4. Retrieve latest assessment
    latest_res = client.get('/api/assessment/latest', headers=headers)
    assert latest_res.status_code == 200
    assert latest_res.get_json()['data']['id'] == assessment_id


def test_recommender_diet_classification():
    """Verify IFCT food group and name categorization."""
    assert classify_food_dietary_category("K001", "Cow milk") == "veg"
    assert classify_food_dietary_category("K006", "Paneer") == "veg"
    assert classify_food_dietary_category("L001", "Hen egg whole") == "eggetarian"
    assert classify_food_dietary_category("N005", "Rohu fish") == "non-veg"
    assert classify_food_dietary_category("M002", "Chicken meat") == "non-veg"
    assert classify_food_dietary_category("A001", "Rice raw") == "vegan"
    assert classify_food_dietary_category("B014", "Moong dal") == "vegan"


def test_recommender_service_generation():
    """Test recommender rankings and antinutrient notes on mock assessment."""
    recommender = get_recommender_service()
    mock_risk_assessment = {
        "iron_mg": {"predicted_risk_label": "High Risk", "percent_rda": 35.0},
        "protein_g": {"predicted_risk_label": "Moderate Risk", "percent_rda": 62.0},
        "zinc_mg": {"predicted_risk_label": "Low Risk", "percent_rda": 88.0}
    }

    full_package = recommender.get_full_recommendation_package(
        risk_assessment=mock_risk_assessment,
        user_diet="veg",
        gender="female",
        age=28
    )

    recs = full_package['recommendations']
    # Only High and Moderate nutrients should be included
    assert "iron_mg" in recs
    assert "protein_g" in recs
    assert "zinc_mg" not in recs  # Low risk should not trigger intervention recommendations

    iron_recs = recs["iron_mg"]
    top_foods = iron_recs["top_foods"]
    assert len(top_foods) > 0
    # Veg diet filter check: no meat/fish/egg in veg profile
    for f in top_foods:
        assert f["diet_category"] in {"veg", "vegan"}
        assert f["typical_portion_g"] > 0
        assert f["percent_daily_rda"] > 0

    assert "clinical_pairing_tips" in iron_recs
    assert len(iron_recs["clinical_pairing_tips"]) > 0


def test_recommendations_api_endpoint(client, auth_token):
    """Verify /api/recommendations endpoint returns structured food guidance."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # 1. Log a meal first so assessment can run
    client.post('/api/intake', json={
        "date": "2026-10-25",
        "entries": [
            {"food_code": "A001", "food_name": "Bajra", "quantity_g": 80, "meal_type": "lunch", "frequency_per_week": 7}
        ]
    }, headers=headers)

    # 2. Run assessment
    run_res = client.post('/api/assessment/run', json={"date": "2026-10-25", "variant": "A"}, headers=headers)
    assert run_res.status_code in (200, 201)

    # 3. Retrieve recommendations
    res = client.get('/api/recommendations', headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'recommendations' in data['data']
    assert data['data']['diet_preference'] == 'veg'
