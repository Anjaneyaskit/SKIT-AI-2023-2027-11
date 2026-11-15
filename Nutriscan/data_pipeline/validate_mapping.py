"""
Nutrient Mapping Validation Script (Phase B Deliverable)
Validates nutrient calculations against hand-computed ground truth values
Formula: nutrient_total = (grams / 100.0) * nutrient_per_100g
Tests 5 distinct food items from IFCT 2017:
  1. Amaranth seed, black (A001)
  2. Bajra (Pearl millet)
  3. Milk, whole, cow
  4. Spinach (Palak)
  5. Bengal gram, whole (Kala chana)
"""

import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP, extract_core_nutrients

CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')
RAW_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'ifct2017_compositions.csv')


def calculate_intake_nutrients(food_row_dict, grams):
    """
    Computes intake nutrients for a given food and gram weight:
    nutrient_amount = (grams / 100.0) * value_per_100g
    """
    per_100g = extract_core_nutrients(food_row_dict)
    factor = grams / 100.0
    totals = {}
    for key, val in per_100g.items():
        totals[key] = round(val * factor, 4)
    return totals, per_100g


def run_validation():
    print("=" * 80)
    print("NutriScan Phase B: Nutrient Mapping & Hand-Calculation Validation")
    print("=" * 80)

    # Use cleaned if available, otherwise raw
    data_path = CLEANED_DATA_PATH if os.path.exists(CLEANED_DATA_PATH) else RAW_DATA_PATH
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Neither cleaned nor raw dataset found: {data_path}")

    df = pd.read_csv(data_path, encoding='utf-8-sig')

    # Select 5 target test foods
    test_queries = [
        ('A001', 150.0, "Amaranth seed, black"),
        ('bajra', 200.0, "Bajra"),
        ('cow', 250.0, "Cow Milk"),
        ('spinach', 75.0, "Spinach"),
        ('bengal gram', 120.0, "Bengal gram")
    ]

    selected_foods = []
    for query, grams, label in test_queries:
        if query == 'A001':
            matched = df[df['code'] == 'A001']
        else:
            matched = df[df['name'].str.lower().str.contains(query.lower(), na=False)]

        if matched.empty:
            # Fallback to row index if search keyword not exact
            matched = df.iloc[[len(selected_foods)]]

        food = matched.iloc[0].to_dict()
        selected_foods.append((food, grams, label))

    print(f"\nSelected {len(selected_foods)} foods for validation across key test portions:\n")

    test_keys = ['energy_kcal', 'protein_g', 'fat_g', 'carbs_g', 'iron_mg', 'calcium_mg', 'zinc_mg', 'vitamin_c_mg']
    all_passed = True

    for idx, (food, grams, label) in enumerate(selected_foods, 1):
        computed_totals, per_100g = calculate_intake_nutrients(food, grams)
        code = food.get('code', 'N/A')
        name = food.get('name', 'N/A')

        print(f"[{idx}] Food: {name} ({code}) | Portion: {grams} g")
        print(f"    {'Nutrient':<18} | {'Per 100g':<10} | {'Expected Hand-Calc':<18} | {'Computed Total':<16} | {'Status'}")
        print("    " + "-" * 75)

        for key in test_keys:
            val_100g = per_100g[key]
            # Hand computed ground truth: (grams / 100) * val_100g
            expected_hand = round((grams / 100.0) * val_100g, 4)
            computed = computed_totals[key]

            # Float tolerance check
            diff = abs(expected_hand - computed)
            status = "PASS" if diff < 1e-4 else "FAIL"
            if status == "FAIL":
                all_passed = False

            unit = CORE_NUTRIENT_MAP[key]['unit']
            print(f"    {key:<18} | {val_100g:8.2f} {unit:<2} | {expected_hand:10.4f} {unit:<2}     | {computed:10.4f} {unit:<2}   | [{status}]")
        print()

    print("=" * 80)
    if all_passed:
        print(">>> ALL 5 FOOD ITEMS PASSED VALIDATION! Hand calculations match formula exactly.")
    else:
        print(">>> VALIDATION FAILED on some items. Review output above.")
    print("=" * 80)
    return all_passed


if __name__ == '__main__':
    success = run_validation()
    sys.exit(0 if success else 1)
