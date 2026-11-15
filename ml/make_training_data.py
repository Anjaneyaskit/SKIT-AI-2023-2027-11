"""
Synthetic Prototype Dataset Generator for NutriScan ML (Phase G Deliverable)
Generates 3,000 synthetic Indian user profiles with realistic demographic variations,
dietary intakes drawn from IFCT 2017 foods, computed daily nutrient totals,
ICMR-NIN 2020 RDA percentage comparisons, rule-based deficiency risk labels,
and correlated clinical symptom scores.

PROMINENT RESEARCH NOTE:
This dataset is a prototype baseline generator for Sprint 2 model architecture development.
It will be replaced with real-world survey data (e.g. NHANES / clinical trials) in Sprint 3.
"""

import os
import sys
import random
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import RANDOM_STATE, SYNTHETIC_DATA_PATH, TARGET_NUTRIENTS
from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP, extract_core_nutrients
from backend.services.nutrient_calculator import calculate_intake_summary
from backend.services.rda_service import get_rda_service

CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')


def generate_synthetic_dataset(num_users=3000, random_seed=RANDOM_STATE):
    print("=" * 75)
    print(f"Generating Synthetic Prototype Training Dataset ({num_users} virtual users)")
    print("=" * 75)

    random.seed(random_seed)
    np.random.seed(random_seed)

    if not os.path.exists(CLEANED_DATA_PATH):
        raise FileNotFoundError(f"Cleaned dataset not found at {CLEANED_DATA_PATH}")

    df_foods = pd.read_csv(CLEANED_DATA_PATH)
    food_records = df_foods.to_dict('records')
    rda_service = get_rda_service()

    activity_levels = ['sedentary', 'light', 'moderate', 'active']
    diet_preferences = ['veg', 'non-veg', 'eggetarian', 'vegan']

    records = []

    for user_idx in range(num_users):
        gender = random.choice(['male', 'female'])
        age = random.randint(19, 58)
        
        # Anthropometrics
        if gender == 'male':
            height_cm = round(random.gauss(170, 7), 1)
            weight_kg = round(random.gauss(68, 11), 1)
        else:
            height_cm = round(random.gauss(158, 6), 1)
            weight_kg = round(random.gauss(56, 10), 1)

        height_cm = max(145.0, min(195.0, height_cm))
        weight_kg = max(40.0, min(110.0, weight_kg))
        bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 2)

        activity = random.choices(activity_levels, weights=[0.45, 0.25, 0.20, 0.10])[0]
        diet = random.choices(diet_preferences, weights=[0.50, 0.35, 0.10, 0.05])[0]

        # Draw a realistic daily diet (3 to 7 food items)
        num_items = random.randint(3, 7)
        sampled_foods = random.sample(food_records, num_items)

        entries = []
        for f in sampled_foods:
            portion_g = round(random.uniform(40.0, 300.0), 0)
            entries.append({
                'food_code': f['code'],
                'food_name': f['name'],
                'quantity_g': portion_g,
                'nutrients': extract_core_nutrients(f),
                'frequency_per_week': 7.0
            })

        summary = calculate_intake_summary(
            entries=entries,
            user_gender=gender,
            user_age=age,
            special_condition='none'
        )

        user_row = {
            'user_id': f"SYN_{user_idx+1:05d}",
            'age': age,
            'gender': gender,
            'height_cm': height_cm,
            'weight_kg': weight_kg,
            'bmi': bmi,
            'activity_level': activity,
            'diet_preference': diet,
            'total_grams_daily': summary['total_grams_daily']
        }

        # Add computed intake totals & RDA %
        nutrients_data = summary['nutrients']
        for nut in CORE_NUTRIENT_MAP.keys():
            nut_info = nutrients_data.get(nut, {})
            user_row[f"intake_{nut}"] = nut_info.get('total_amount', 0.0)
            user_row[f"rda_pct_{nut}"] = nut_info.get('rda_percent')

        # Rule-based deficiency risk ground truth labels per target nutrient:
        # <50% RDA = High risk (0)
        # 50-80% RDA = Moderate risk (1)
        # >=80% RDA = Low risk (2)
        for target_nut in TARGET_NUTRIENTS:
            pct = user_row.get(f"rda_pct_{target_nut}")
            if pct is None or np.isnan(pct):
                # Fallback if RDA is pending
                risk_code = 1
                risk_label = 'Moderate Risk'
            elif pct < 50.0:
                risk_code = 0
                risk_label = 'High Risk'
            elif pct < 80.0:
                risk_code = 1
                risk_label = 'Moderate Risk'
            else:
                risk_code = 2
                risk_label = 'Low Risk'

            user_row[f"target_{target_nut}_code"] = risk_code
            user_row[f"target_{target_nut}_label"] = risk_label

        # Simulated clinical symptom scores (0 to 4) correlated with risks plus Gaussian noise
        # Fatigue: correlated with Iron & Energy deficiency
        iron_def = 1 if user_row['target_iron_mg_code'] == 0 else (0.5 if user_row['target_iron_mg_code'] == 1 else 0)
        user_row['symptom_fatigue'] = int(np.clip(round(iron_def * 3.0 + np.random.normal(0.5, 0.7)), 0, 4))

        # Pale skin & cold hands: correlated with Iron
        user_row['symptom_pale_skin'] = int(np.clip(round(iron_def * 3.2 + np.random.normal(0.4, 0.6)), 0, 4))

        # Muscle weakness & bone aches: correlated with Calcium & Vitamin D
        ca_def = 1 if user_row['target_calcium_mg_code'] == 0 else (0.5 if user_row['target_calcium_mg_code'] == 1 else 0)
        user_row['symptom_muscle_cramps'] = int(np.clip(round(ca_def * 3.0 + np.random.normal(0.5, 0.7)), 0, 4))

        # Hair loss / brittle nails: correlated with Protein & Zinc
        prot_def = 1 if user_row['target_protein_g_code'] == 0 else (0.5 if user_row['target_protein_g_code'] == 1 else 0)
        user_row['symptom_hair_fall'] = int(np.clip(round(prot_def * 2.8 + np.random.normal(0.5, 0.8)), 0, 4))

        # Slow wound healing & frequent infections: correlated with Vitamin C & Zinc
        vitc_def = 1 if user_row['target_vitamin_c_mg_code'] == 0 else (0.5 if user_row['target_vitamin_c_mg_code'] == 1 else 0)
        user_row['symptom_slow_healing'] = int(np.clip(round(vitc_def * 3.0 + np.random.normal(0.4, 0.7)), 0, 4))

        records.append(user_row)

    out_df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(SYNTHETIC_DATA_PATH), exist_ok=True)
    out_df.to_csv(SYNTHETIC_DATA_PATH, index=False)
    print(f"\nGenerated {len(out_df)} synthetic profiles. Saved -> {SYNTHETIC_DATA_PATH}")
    print("\nRisk Class Distributions (Target Nutrients):")
    for nut in TARGET_NUTRIENTS:
        col = f"target_{nut}_label"
        counts = out_df[col].value_counts().to_dict()
        print(f"  {nut:<16}: {counts}")

    print("=" * 75)
    return out_df


if __name__ == '__main__':
    generate_synthetic_dataset()
