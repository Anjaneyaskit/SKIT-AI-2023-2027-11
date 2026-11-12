"""
Unit and Integration Tests for Auth and Profile Endpoints
"""

import pytest
from backend.app import create_app
from backend.db import get_db, reset_db_instance
from backend.schemas import calculate_bmi, validate_profile


@pytest.fixture
def client():
    reset_db_instance()
    app = create_app({
        'TESTING': True,
        'USE_MOCK_DB': True
    })
    with app.test_client() as client:
        yield client


def test_bmi_calculation():
    # Normal weight: 175cm, 70kg -> 70 / (1.75^2) = 22.86
    bmi, cat = calculate_bmi(175.0, 70.0)
    assert bmi == 22.86
    assert cat == "Normal weight"

    # Underweight: 180cm, 55kg -> 55 / (1.8^2) = 16.98
    bmi_uw, cat_uw = calculate_bmi(180.0, 55.0)
    assert bmi_uw == 16.98
    assert cat_uw == "Underweight"


def test_profile_validation():
    # Valid profile
    valid, err, cleaned = validate_profile({
        'age': 25,
        'gender': 'male',
        'height_cm': 175,
        'weight_kg': 68,
        'activity_level': 'sedentary',
        'diet_preference': 'veg'
    })
    assert valid is True
    assert err is None
    assert cleaned['bmi'] == 22.2

    # Invalid age
    valid_age, err_age, _ = validate_profile({'age': 150, 'gender': 'male', 'height_cm': 170, 'weight_kg': 60})
    assert valid_age is False
    assert "between 1 and 120" in err_age


def test_auth_registration_and_login_flow(client):
    import uuid
    rand_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    # 1. Register new user
    res = client.post('/api/auth/register', json={
        'name': 'Test User',
        'email': rand_email,
        'password': 'password123'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    token = data['data']['token']
    assert token is not None

    # 2. Reject duplicate email
    res_dup = client.post('/api/auth/register', json={
        'name': 'Duplicate User',
        'email': rand_email,
        'password': 'password123'
    })
    assert res_dup.status_code == 400
    assert "already exists" in res_dup.get_json()['message']

    # 3. Login with credentials
    res_login = client.post('/api/auth/login', json={
        'email': rand_email,
        'password': 'password123'
    })
    assert res_login.status_code == 200
    login_token = res_login.get_json()['data']['token']

    # 4. Access protected me route
    res_me = client.get('/api/auth/me', headers={'Authorization': f"Bearer {login_token}"})
    assert res_me.status_code == 200
    assert res_me.get_json()['data']['user']['email'] == rand_email


def test_protected_profile_update(client):
    import uuid
    p_email = f"profile_{uuid.uuid4().hex[:8]}@example.com"
    # Register user
    reg = client.post('/api/auth/register', json={
        'name': 'Profile Tester',
        'email': p_email,
        'password': 'password123'
    })
    token = reg.get_json()['data']['token']

    # Update profile
    put_res = client.put('/api/profile', json={
        'age': 28,
        'gender': 'female',
        'height_cm': 162.0,
        'weight_kg': 58.0,
        'activity_level': 'light',
        'diet_preference': 'veg'
    }, headers={'Authorization': f"Bearer {token}"})

    assert put_res.status_code == 200
    prof = put_res.get_json()['data']['profile']
    assert prof['age'] == 28
    assert prof['bmi'] == 22.1
    assert prof['bmi_category'] == 'Normal weight'
