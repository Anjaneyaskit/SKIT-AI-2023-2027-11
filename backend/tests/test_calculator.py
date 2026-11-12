"""
Unit Tests for Nutrient Calculator Service
Verifies:
  1. Hand-computed portion calculations
  2. Weekly to daily frequency conversion
  3. RDA percentage calculations and missing RDA handling
"""

import pytest
from backend.services.nutrient_calculator import calculate_intake_summary


def test_single_food_direct_calculation():
    # 150g of food with 10g protein and 200 kcal per 100g
    # Expected: 15g protein, 300 kcal
    entries = [{
        'food_code': 'TEST1',
        'food_name': 'Test Grains',
        'quantity_g': 150.0,
        'frequency_per_week': 7.0,
        'nutrients': {
            'energy_kcal': 200.0,
            'protein_g': 10.0,
            'iron_mg': 4.0,
            'calcium_mg': 50.0
        }
    }]

    # Adult male (19-30): RDA protein = 54.0g, iron = 19.0mg, calcium = 1000mg
    res = calculate_intake_summary(entries, user_gender='male', user_age=25)

    assert res['item_count'] == 1
    assert res['total_grams_daily'] == 150.0

    nuts = res['nutrients']
    assert nuts['energy_kcal']['total_amount'] == 300.0
    assert nuts['protein_g']['total_amount'] == 15.0
    assert nuts['iron_mg']['total_amount'] == 6.0
    assert nuts['calcium_mg']['total_amount'] == 75.0

    # Hand-computed RDA percentages:
    # Protein: 15 / 54 * 100 = 27.8%
    assert nuts['protein_g']['rda_percent'] == pytest.approx(27.8, abs=0.1)
    # Iron: 6 / 19 * 100 = 31.6%
    assert nuts['iron_mg']['rda_percent'] == pytest.approx(31.6, abs=0.1)


def test_frequency_conversion():
    # 140g consumed 3 days a week -> daily equivalent is 140 * 3 / 7 = 60g daily
    entries = [{
        'food_code': 'TEST2',
        'food_name': 'Test Pulse',
        'quantity_g': 140.0,
        'frequency_per_week': 3.0,
        'nutrients': {
            'protein_g': 20.0
        }
    }]

    res = calculate_intake_summary(entries, user_gender='male', user_age=25)
    assert res['total_grams_daily'] == 60.0
    # 60g portion -> (60/100) * 20g = 12g protein
    assert res['nutrients']['protein_g']['total_amount'] == 12.0


def test_missing_rda_cohort_handling():
    # Testing age where RDA is marked TODO (e.g. child 2 years)
    entries = [{
        'food_code': 'TEST3',
        'food_name': 'Milk',
        'quantity_g': 200.0,
        'nutrients': {'calcium_mg': 120.0}
    }]

    res = calculate_intake_summary(entries, user_gender='male', user_age=2)
    calcium_info = res['nutrients']['calcium_mg']
    assert calcium_info['total_amount'] == 240.0
    # Must be None, not fabricated
    assert calcium_info['rda_value'] is None
    assert calcium_info['rda_percent'] is None
    assert 'pending' in calcium_info['status_note'].lower()
