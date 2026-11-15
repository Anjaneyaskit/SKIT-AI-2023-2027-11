"""
Database Seeding Script for NutriScan (Phase D Deliverable)
Loads cleaned food compositions and ICMR-NIN RDA reference tables into MongoDB collections.
Ensures collection indexes are created and operations are strictly idempotent.
"""

import os
import sys
import csv
import pandas as pd
from typing import Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.db import get_db
from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP, extract_core_nutrients

SLIM_FOODS_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'foods_for_db.csv')
CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')
RDA_CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'rda_icmr_nin_2020.csv')


def seed_database():
    print("=" * 70)
    print("NutriScan Database Seeder")
    print("=" * 70)

    db_wrapper = get_db()
    db_wrapper.create_indexes()

    # 1. Seed Foods Collection
    print("\n[1/2] Seeding 'foods' collection...")
    if os.path.exists(CLEANED_DATA_PATH):
        df_foods = pd.read_csv(CLEANED_DATA_PATH)
    elif os.path.exists(SLIM_FOODS_PATH):
        df_foods = pd.read_csv(SLIM_FOODS_PATH)
    else:
        raise FileNotFoundError(f"Cleaned food dataset not found at {CLEANED_DATA_PATH}")

    food_count = 0
    for _, row in df_foods.iterrows():
        row_dict = row.to_dict()
        nutrients = extract_core_nutrients(row_dict)

        doc = {
            'code': str(row['code']).strip(),
            'name': str(row['name']).strip(),
            'scie': str(row.get('scie', 'Unknown')).strip(),
            'region': str(row.get('region', 'Other')).strip(),
            'nutrients': nutrients
        }

        # Upsert by unique food code
        db_wrapper.foods.replace_one({'code': doc['code']}, doc, upsert=True)
        food_count += 1

    print(f"Successfully seeded/updated {food_count} food items in 'foods' collection.")

    # 2. Seed RDA Collection
    print("\n[2/2] Seeding 'rda' collection...")
    if not os.path.exists(RDA_CSV_PATH):
        raise FileNotFoundError(f"RDA reference table not found at {RDA_CSV_PATH}")

    rda_count = 0
    with open(RDA_CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rda_raw = row.get('rda_value', '').strip()
            if not rda_raw or 'TODO' in rda_raw:
                continue

            try:
                rda_val = float(rda_raw)
            except ValueError:
                continue

            ear_raw = row.get('ear_value', '').strip()
            ear_val = float(ear_raw) if (ear_raw and 'TODO' not in ear_raw) else None

            doc = {
                'group_label': row.get('group_label', '').strip(),
                'gender': row.get('gender', '').strip().lower(),
                'age_min': int(float(row.get('age_min', 0))),
                'age_max': int(float(row.get('age_max', 120))),
                'special_condition': row.get('special_condition', 'none').strip().lower(),
                'nutrient_key': row.get('nutrient_key', '').strip(),
                'rda_value': rda_val,
                'unit': row.get('unit', '').strip(),
                'ear_value': ear_val
            }

            query = {
                'gender': doc['gender'],
                'age_min': doc['age_min'],
                'age_max': doc['age_max'],
                'special_condition': doc['special_condition'],
                'nutrient_key': doc['nutrient_key']
            }
            db_wrapper.rda.replace_one(query, doc, upsert=True)
            rda_count += 1

    print(f"Successfully seeded/updated {rda_count} verified RDA benchmark values.")
    print("=" * 70)
    print("Database seeding completed successfully!")
    print("=" * 70)
    return food_count, rda_count


if __name__ == '__main__':
    seed_database()
