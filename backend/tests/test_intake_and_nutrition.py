"""
Integration Tests for Intake Logging and Nutrition Summary
"""

import pytest
from backend.app import create_app
from backend.db import get_db, reset_db_instance
from data_pipeline.seed_db import seed_database


@pytest.fixture(scope="module")
def client():
    reset_db_instance()
    app = create_app({
        'TESTING': True,
        'USE_MOCK_DB': True
    })
    with app.app_context():
        seed_database()
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get('/api/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['status'] == 'healthy'


def test_intake_logging_and_summary_flow(client):
    import uuid
    email = f"intake_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post('/api/auth/register', json={
        'name': 'Intake User',
        'email': email,
        'password': 'password123'
    })
    token = reg.get_json()['data']['token']
    auth_header = {'Authorization': f"Bearer {token}"}

    client.put('/api/profile', json={
        'age': 25,
        'gender': 'male',
        'height_cm': 175.0,
        'weight_kg': 70.0,
        'activity_level': 'sedentary',
        'diet_preference': 'veg'
    }, headers=auth_header)

    # 2. Log intake for today: 200g of Bajra (A003)
    intake_res = client.post('/api/intake', json={
        'date': '2026-10-25',
        'entries': [{
            'food_code': 'A003',
            'quantity_g': 200.0,
            'meal_type': 'breakfast',
            'frequency_per_week': 7.0
        }]
    }, headers=auth_header)

    assert intake_res.status_code == 201
    assert intake_res.get_json()['success'] is True

    # 3. Fetch summary for today
    sum_res = client.get('/api/nutrition/summary?date=2026-10-25', headers=auth_header)
    assert sum_res.status_code == 200
    sum_data = sum_res.get_json()['data']['summary']

    assert sum_data['item_count'] == 1
    assert sum_data['total_grams_daily'] == 200.0
    # Bajra per 100g has ~10.96g protein -> for 200g should have ~21.92g
    prot_info = sum_data['nutrients']['protein_g']
    assert prot_info['total_amount'] == pytest.approx(21.92, abs=0.1)
    # Adult male protein RDA is 54g -> 21.92 / 54 = 40.6%
    assert prot_info['rda_percent'] == pytest.approx(40.6, abs=0.2)
