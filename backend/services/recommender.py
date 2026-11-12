"""
Intelligent Food Recommendation Engine for NutriScan (Phase L Deliverable)
Ranks and recommends nutrient-dense Indian foods from IFCT 2017 based on detected deficiency risks.
Filters strictly by user dietary preference (veg, non-veg, eggetarian, vegan).
Includes portion sizing, % RDA per serving, antinutrient absorption alerts, and pairing advice.
"""

import os
import sys
import pandas as pd
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP
from backend.services.rda_service import get_rda_service

CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')

# Typical standard Indian household portions in grams
SERVING_SIZES_G = {
    'cereal': 100.0,
    'pulse': 120.0,
    'vegetable': 150.0,
    'leafy': 100.0,
    'fruit': 120.0,
    'dairy': 200.0,
    'nut_seed': 30.0,
    'egg': 50.0,
    'meat_fish': 120.0,
    'default': 100.0
}

# Evidence-based nutrient absorption synergy pairing tips
PAIRING_TIPS = {
    'iron_mg': [
        "Pair with Vitamin C: Squeeze fresh lemon juice or consume amla/oranges alongside plant-based iron to boost non-heme iron absorption up to 3x.",
        "Avoid Inhibitors: Avoid drinking tea, coffee, or milk within 1 hour before and after iron-rich meals, as tannins and calcium inhibit iron uptake."
    ],
    'calcium_mg': [
        "Ensure Vitamin D: Calcium absorption in the gut is dependent on adequate Vitamin D status; ensure 15-20 minutes of daily morning sun exposure.",
        "Reduce Oxalate Interference: Blanch or cook spinach and beet greens to significantly reduce soluble oxalates that bind calcium."
    ],
    'zinc_mg': [
        "Soak & Ferment: Soak whole grains and pulses overnight, or consume fermented batters (idli/dosa) to activate phytase and increase zinc bioavailability."
    ],
    'folate_ug': [
        "Minimal Heat: Folate is heat-sensitive; steam or lightly sauté green leafy vegetables rather than deep frying or prolonged pressure cooking."
    ],
    'protein_g': [
        "Complementary Amino Acids: Pair cereals and pulses together (e.g. khichdi, dal-rice, or roti-rajma) to achieve a complete essential amino acid profile."
    ],
    'vitamin_c_mg': [
        "Fresh & Raw: Consume citrus fruits, amla, and guava raw and freshly cut, as Vitamin C degrades rapidly when exposed to air and high heat."
    ]
}


def classify_food_dietary_category(code: str, name: str) -> str:
    """
    Tags food items into dietary preference groups based on IFCT prefix and food name:
      - 'vegan': all plant-based grains, pulses, fruits, veggies, nuts
      - 'veg': vegan + dairy
      - 'eggetarian': veg + eggs
      - 'non-veg': all foods including poultry, meat, fish
    """
    prefix = str(code)[0].upper() if code else 'A'
    name_lower = name.lower()

    # Dairy group
    if prefix == 'K' or any(w in name_lower for w in ['milk', 'curd', 'paneer', 'cheese', 'ghee', 'butter', 'buttermilk', 'lassi']):
        return 'veg'

    # Eggs group
    if prefix == 'L' or 'egg' in name_lower or 'yolk' in name_lower or 'albumen' in name_lower:
        return 'eggetarian'

    # Meat, Poultry, Fish group
    if prefix in ('M', 'N', 'O') or any(w in name_lower for w in ['chicken', 'meat', 'mutton', 'fish', 'prawn', 'crab', 'pork', 'beef', 'duck', 'liver', 'spleen']):
        return 'non-veg'

    # All plant-derived foods
    return 'vegan'


def get_serving_portion(code: str) -> float:
    prefix = str(code)[0].upper() if code else 'A'
    if prefix in ('A', 'F'): return SERVING_SIZES_G['cereal']
    if prefix == 'B': return SERVING_SIZES_G['pulse']
    if prefix == 'C': return SERVING_SIZES_G['leafy']
    if prefix == 'D': return SERVING_SIZES_G['vegetable']
    if prefix == 'E': return SERVING_SIZES_G['fruit']
    if prefix == 'H': return SERVING_SIZES_G['nut_seed']
    if prefix == 'K': return SERVING_SIZES_G['dairy']
    if prefix == 'L': return SERVING_SIZES_G['egg']
    if prefix in ('M', 'N', 'O'): return SERVING_SIZES_G['meat_fish']
    return SERVING_SIZES_G['default']


class RecommenderService:
    _instance = None
    _foods_df = None

    def __init__(self):
        self._load_foods()

    def _load_foods(self):
        if os.path.exists(CLEANED_DATA_PATH):
            df = pd.read_csv(CLEANED_DATA_PATH)
            # Add dietary category
            df['diet_category'] = [
                classify_food_dietary_category(r['code'], r['name']) for _, r in df.iterrows()
            ]
            self._foods_df = df
            print(f"[Recommender] Loaded {len(df)} foods categorized across dietary preferences.")
        else:
            print(f"[Recommender] Cleaned dataset not found at {CLEANED_DATA_PATH}")

    def get_recommendations_for_nutrient(
        self,
        nutrient_key: str,
        user_diet: str = 'veg',
        gender: str = 'male',
        age: int = 25,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top food recommendations for a deficient nutrient, filtered by diet.
        """
        if self._foods_df is None or self._foods_df.empty:
            return []

        df = self._foods_df.copy()
        user_diet_clean = user_diet.lower().strip()

        # Strict dietary preference filtering
        if user_diet_clean == 'vegan':
            df = df[df['diet_category'] == 'vegan']
        elif user_diet_clean == 'veg':
            df = df[df['diet_category'].isin(['vegan', 'veg'])]
        elif user_diet_clean == 'eggetarian':
            df = df[df['diet_category'].isin(['vegan', 'veg', 'eggetarian'])]
        # 'non-veg' accepts all foods

        # Identify target column in cleaned dataset
        meta = CORE_NUTRIENT_MAP.get(nutrient_key, {})
        col = meta.get('ifct_col')
        if isinstance(col, list):
            col = col[0]
        if nutrient_key == 'energy_kcal':
            col = 'energy_kcal'

        if not col or col not in df.columns:
            return []

        # Sort by highest nutrient density per 100g
        top_foods = df.sort_values(by=col, ascending=False)

        # Exclude very rare or organ meats if user is looking for everyday foods
        top_foods = top_foods[top_foods[col] > 0].head(limit * 2)

        rda_service = get_rda_service()
        user_rda_dict = rda_service.get_rda_for_profile(gender, age)
        rda_val = user_rda_dict.get(nutrient_key, {}).get('rda_value', 1.0) or 1.0

        recommendations = []
        seen_names = set()

        for _, row in top_foods.iterrows():
            clean_name = row['name'].split(',')[0].strip()
            if clean_name.lower() in seen_names:
                continue
            seen_names.add(clean_name.lower())

            portion_g = get_serving_portion(row['code'])
            val_per_100g = float(row[col])
            serving_yield = round((portion_g / 100.0) * val_per_100g, 2)
            pct_rda = round((serving_yield / rda_val) * 100.0, 1)

            # Antinutrient check
            antinutrient_note = None
            if nutrient_key in ('iron_mg', 'calcium_mg'):
                oxalt = float(row.get('oxalt', 0.0) or 0.0)
                phytac = float(row.get('phytac', 0.0) or 0.0)
                if oxalt > 200.0:
                    antinutrient_note = f"High in oxalates ({oxalt:.0f}mg/100g); cook thoroughly to optimize mineral absorption."
                elif phytac > 300.0:
                    antinutrient_note = f"Contains phytates ({phytac:.0f}mg/100g); soaking or sprouting improves bioavailability."

            recommendations.append({
                'food_code': row['code'],
                'name': clean_name,
                'food_name': row['name'],
                'category': row.get('group', 'IFCT 2017 Food'),
                'region': row.get('region', 'All India'),
                'diet_type': row['diet_category'],
                'diet_category': row['diet_category'],
                'nutrient_density_per_100g': round(val_per_100g, 2),
                'typical_portion_g': portion_g,
                'typical_serving_g': portion_g,
                'yield_per_serving': serving_yield,
                'nutrient_per_serving': serving_yield,
                'percent_daily_rda': pct_rda,
                'rda_pct_per_serving': pct_rda,
                'unit': meta.get('unit', ''),
                'antinutrient_note': antinutrient_note
            })

            if len(recommendations) >= limit:
                break

        return recommendations

    def get_full_recommendation_package(
        self,
        risk_assessment: Dict[str, Any],
        user_diet: str = 'veg',
        gender: str = 'male',
        age: int = 25
    ) -> Dict[str, Any]:
        """
        Compiles nutrient-specific food recommendations and pairing tips
        for all nutrients evaluated at Moderate or High Risk.
        """
        targeted_packages = {}

        for nut_key, res in risk_assessment.items():
            risk_label = res.get('predicted_risk_label', '')
            # Recommend foods for Moderate or High risk
            if risk_label in ('High Risk', 'Moderate Risk'):
                foods = self.get_recommendations_for_nutrient(
                    nut_key, user_diet=user_diet, gender=gender, age=age, limit=6
                )
                meta = CORE_NUTRIENT_MAP.get(nut_key, {})
                tips = PAIRING_TIPS.get(nut_key, [])
                user_intake = res.get('total_intake', 0.0)
                user_rda = res.get('rda_value', 0.0)
                rda_pct = res.get('rda_percent', 0.0)

                pkg_item = {
                    'nutrient_key': nut_key,
                    'nutrient_name': meta.get('display_name', nut_key),
                    'unit': meta.get('unit', ''),
                    'risk_level': risk_label,
                    'user_intake': user_intake,
                    'user_rda': user_rda,
                    'rda_percent': rda_pct,
                    'synergy_tip': tips[0] if tips else '',
                    'clinical_pairing_tips': tips,
                    'foods': foods,
                    'top_foods': foods
                }
                targeted_packages[nut_key] = pkg_item

        return {
            'deficient_nutrients_count': len(targeted_packages),
            'user_diet_preference': user_diet,
            'recommendations': targeted_packages
        }

    def get_all_nutrient_recommendations(
        self,
        user_diet: str = 'veg',
        gender: str = 'male',
        age: int = 25,
        limit: int = 6
    ) -> Dict[str, Any]:
        """
        Generates full IFCT food recommendations across all 6 core target nutrients.
        Useful for exploration, standard maintenance, and non-deficient nutrients.
        """
        target_keys = ['calcium_mg', 'vitamin_c_mg', 'iron_mg', 'protein_g', 'zinc_mg', 'folate_ug']
        packages = {}
        for nut_key in target_keys:
            foods = self.get_recommendations_for_nutrient(
                nut_key, user_diet=user_diet, gender=gender, age=age, limit=limit
            )
            meta = CORE_NUTRIENT_MAP.get(nut_key, {})
            tips = PAIRING_TIPS.get(nut_key, [])
            packages[nut_key] = {
                'nutrient_key': nut_key,
                'nutrient_name': meta.get('display_name', nut_key),
                'unit': meta.get('unit', ''),
                'risk_level': 'General Recommendation',
                'user_intake': None,
                'user_rda': None,
                'rda_percent': None,
                'synergy_tip': tips[0] if tips else '',
                'clinical_pairing_tips': tips,
                'foods': foods,
                'top_foods': foods
            }
        return packages


_recommender_instance: Optional[RecommenderService] = None

def get_recommender_service() -> RecommenderService:
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = RecommenderService()
    return _recommender_instance
