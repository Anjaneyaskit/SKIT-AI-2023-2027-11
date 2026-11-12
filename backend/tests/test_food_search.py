"""
Unit Tests for Food Catalog Search and Detail Endpoints
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


def test_food_search_query(client):
    # Search for bajra
    res = client.get('/api/foods?q=bajra')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['count'] >= 1
    first_item = data['data']['foods'][0]
    assert 'bajra' in first_item['name'].lower()
    assert 'headline_nutrients' in first_item
    assert 'energy_kcal' in first_item['headline_nutrients']


def test_food_get_by_code(client):
    # Food code A001 (Amaranth seed, black)
    res = client.get('/api/foods/A001')
    assert res.status_code == 200
    food = res.get_json()['data']['food']
    assert food['code'] == 'A001'
    assert 'Amaranth' in food['name']
    assert 'nutrients' in food
    assert food['nutrients']['protein_g'] > 0


def test_food_get_invalid_code(client):
    res = client.get('/api/foods/INVALID_CODE_999')
    assert res.status_code == 404
    assert res.get_json()['success'] is False
