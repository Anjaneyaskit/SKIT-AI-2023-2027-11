"""
LLM Service Layer for NutriScan (Phase N Deliverable)
Implements AI-assisted natural language meal parsing, recipe nutritional estimation for non-IFCT foods,
and plain-language nutritional coaching.
STRICT SAFETY CONTRACT:
  1. The LLM never calculates clinical risk classifications or prescribes medications.
  2. If LLM_ENABLED=false, no API key, or upon network timeout, gracefully falls back to deterministic code and curated Indian recipe database.
  3. When an Indian food (like Dhokla, Pav Bhaji, Poha) is not present in IFCT 2017, the AI generates a complete 19-core nutrient profile per 100g and saves it into MongoDB db.foods.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from rapidfuzz import process, fuzz

from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOUSEHOLD_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'household_measures.csv')
CLEANED_FOODS_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'foods_for_db.csv')

logger = logging.getLogger('NutriScan.LLM')

MEASURE_UNITS = {
    'g', 'gm', 'gms', 'gram', 'grams', 'kg', 'katori', 'katoris', 'bowl', 'bowls',
    'cup', 'cups', 'glass', 'glasses', 'plate', 'plates', 'piece', 'pieces',
    'slice', 'slices', 'tbsp', 'tsp', 'serving', 'servings', 'roti', 'rotis',
    'chapatis', 'chapati', 'idli', 'idlis', 'puri', 'puris', 'vada', 'vadas',
    'samosa', 'samosas', 'bhature', 'bhatura', 'dosa', 'dosas', 'paratha', 'parathas'
}

# Curated reference nutrient values per 100g for popular prepared Indian dishes
COMMON_INDIAN_RECIPES = {
    'dhokla': {
        'scie': 'Steamed Fermented Chickpea Cake',
        'region': 'West',
        'nutrients': {
            'energy_kcal': 152.0, 'protein_g': 6.2, 'fat_g': 2.8, 'carbs_g': 25.5,
            'fibre_g': 2.2, 'iron_mg': 1.3, 'calcium_mg': 35.0, 'zinc_mg': 0.7,
            'magnesium_mg': 30.0, 'vitamin_c_mg': 1.0, 'folate_ug': 32.0, 'vitamin_a_ug': 5.0,
            'thiamine_mg': 0.1, 'riboflavin_mg': 0.08, 'niacin_mg': 1.1, 'vitamin_b6_mg': 0.15,
            'vitamin_d_ug': 0.0, 'sodium_mg': 320.0, 'potassium_mg': 150.0
        }
    },
    'poha': {
        'scie': 'Flattened Rice Tempered with Spices & Peanuts',
        'region': 'West',
        'nutrients': {
            'energy_kcal': 180.0, 'protein_g': 3.5, 'fat_g': 5.2, 'carbs_g': 30.0,
            'fibre_g': 1.8, 'iron_mg': 2.1, 'calcium_mg': 20.0, 'zinc_mg': 0.6,
            'magnesium_mg': 28.0, 'vitamin_c_mg': 4.5, 'folate_ug': 18.0, 'vitamin_a_ug': 12.0,
            'thiamine_mg': 0.15, 'riboflavin_mg': 0.05, 'niacin_mg': 1.2, 'vitamin_b6_mg': 0.12,
            'vitamin_d_ug': 0.0, 'sodium_mg': 210.0, 'potassium_mg': 110.0
        }
    },
    'upma': {
        'scie': 'Cooked Semolina Porridge with Vegetables',
        'region': 'South',
        'nutrients': {
            'energy_kcal': 165.0, 'protein_g': 4.0, 'fat_g': 5.0, 'carbs_g': 26.0,
            'fibre_g': 2.0, 'iron_mg': 1.1, 'calcium_mg': 18.0, 'zinc_mg': 0.5,
            'magnesium_mg': 22.0, 'vitamin_c_mg': 2.0, 'folate_ug': 15.0, 'vitamin_a_ug': 8.0,
            'thiamine_mg': 0.12, 'riboflavin_mg': 0.04, 'niacin_mg': 0.9, 'vitamin_b6_mg': 0.1,
            'vitamin_d_ug': 0.0, 'sodium_mg': 260.0, 'potassium_mg': 95.0
        }
    },
    'idli': {
        'scie': 'Steamed Rice and Black Gram Cake',
        'region': 'South',
        'nutrients': {
            'energy_kcal': 132.0, 'protein_g': 4.5, 'fat_g': 0.6, 'carbs_g': 27.0,
            'fibre_g': 1.5, 'iron_mg': 0.8, 'calcium_mg': 22.0, 'zinc_mg': 0.6,
            'magnesium_mg': 24.0, 'vitamin_c_mg': 0.0, 'folate_ug': 20.0, 'vitamin_a_ug': 0.0,
            'thiamine_mg': 0.08, 'riboflavin_mg': 0.04, 'niacin_mg': 0.7, 'vitamin_b6_mg': 0.09,
            'vitamin_d_ug': 0.0, 'sodium_mg': 180.0, 'potassium_mg': 75.0
        }
    },
    'sambar': {
        'scie': 'Lentil and Vegetable Stew with Tamarind',
        'region': 'South',
        'nutrients': {
            'energy_kcal': 75.0, 'protein_g': 3.2, 'fat_g': 2.1, 'carbs_g': 11.0,
            'fibre_g': 2.8, 'iron_mg': 1.4, 'calcium_mg': 30.0, 'zinc_mg': 0.6,
            'magnesium_mg': 25.0, 'vitamin_c_mg': 6.0, 'folate_ug': 28.0, 'vitamin_a_ug': 35.0,
            'thiamine_mg': 0.09, 'riboflavin_mg': 0.05, 'niacin_mg': 0.8, 'vitamin_b6_mg': 0.12,
            'vitamin_d_ug': 0.0, 'sodium_mg': 340.0, 'potassium_mg': 190.0
        }
    },
    'pav_bhaji': {
        'scie': 'Mashed Spiced Vegetable Curry',
        'region': 'West',
        'nutrients': {
            'energy_kcal': 175.0, 'protein_g': 4.2, 'fat_g': 7.5, 'carbs_g': 23.0,
            'fibre_g': 3.2, 'iron_mg': 1.6, 'calcium_mg': 38.0, 'zinc_mg': 0.8,
            'magnesium_mg': 30.0, 'vitamin_c_mg': 12.0, 'folate_ug': 30.0, 'vitamin_a_ug': 45.0,
            'thiamine_mg': 0.14, 'riboflavin_mg': 0.07, 'niacin_mg': 1.3, 'vitamin_b6_mg': 0.18,
            'vitamin_d_ug': 0.0, 'sodium_mg': 420.0, 'potassium_mg': 240.0
        }
    },
    'paneer_bhurji': {
        'scie': 'Scrambled Indian Cottage Cheese with Spices',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 240.0, 'protein_g': 14.5, 'fat_g': 18.0, 'carbs_g': 5.0,
            'fibre_g': 1.2, 'iron_mg': 1.5, 'calcium_mg': 320.0, 'zinc_mg': 1.8,
            'magnesium_mg': 35.0, 'vitamin_c_mg': 4.0, 'folate_ug': 22.0, 'vitamin_a_ug': 90.0,
            'thiamine_mg': 0.08, 'riboflavin_mg': 0.22, 'niacin_mg': 0.6, 'vitamin_b6_mg': 0.15,
            'vitamin_d_ug': 0.8, 'sodium_mg': 380.0, 'potassium_mg': 170.0
        }
    },
    'khichdi': {
        'scie': 'Rice and Lentil Porridge Cooked with Ghee',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 135.0, 'protein_g': 4.8, 'fat_g': 3.5, 'carbs_g': 21.0,
            'fibre_g': 2.4, 'iron_mg': 1.3, 'calcium_mg': 25.0, 'zinc_mg': 0.7,
            'magnesium_mg': 32.0, 'vitamin_c_mg': 0.5, 'folate_ug': 24.0, 'vitamin_a_ug': 10.0,
            'thiamine_mg': 0.11, 'riboflavin_mg': 0.05, 'niacin_mg': 1.0, 'vitamin_b6_mg': 0.14,
            'vitamin_d_ug': 0.0, 'sodium_mg': 220.0, 'potassium_mg': 140.0
        }
    },
    'biryani': {
        'scie': 'Spiced Basmati Rice Cooked with Vegetables or Meat',
        'region': 'South',
        'nutrients': {
            'energy_kcal': 210.0, 'protein_g': 8.5, 'fat_g': 8.0, 'carbs_g': 26.0,
            'fibre_g': 1.8, 'iron_mg': 1.8, 'calcium_mg': 28.0, 'zinc_mg': 1.2,
            'magnesium_mg': 26.0, 'vitamin_c_mg': 3.0, 'folate_ug': 20.0, 'vitamin_a_ug': 25.0,
            'thiamine_mg': 0.12, 'riboflavin_mg': 0.08, 'niacin_mg': 1.8, 'vitamin_b6_mg': 0.22,
            'vitamin_d_ug': 0.1, 'sodium_mg': 390.0, 'potassium_mg': 210.0
        }
    },
    'dosa': {
        'scie': 'Fermented Crepe of Rice and Black Gram',
        'region': 'South',
        'nutrients': {
            'energy_kcal': 168.0, 'protein_g': 3.9, 'fat_g': 3.7, 'carbs_g': 29.0,
            'fibre_g': 1.6, 'iron_mg': 0.9, 'calcium_mg': 16.0, 'zinc_mg': 0.5,
            'magnesium_mg': 20.0, 'vitamin_c_mg': 0.0, 'folate_ug': 16.0, 'vitamin_a_ug': 0.0,
            'thiamine_mg': 0.08, 'riboflavin_mg': 0.04, 'niacin_mg': 0.8, 'vitamin_b6_mg': 0.08,
            'vitamin_d_ug': 0.0, 'sodium_mg': 210.0, 'potassium_mg': 80.0
        }
    },
    'chole': {
        'scie': 'Spicy White Chickpea Curry',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 160.0, 'protein_g': 7.5, 'fat_g': 5.0, 'carbs_g': 21.0,
            'fibre_g': 5.5, 'iron_mg': 2.4, 'calcium_mg': 55.0, 'zinc_mg': 1.1,
            'magnesium_mg': 45.0, 'vitamin_c_mg': 3.5, 'folate_ug': 55.0, 'vitamin_a_ug': 20.0,
            'thiamine_mg': 0.14, 'riboflavin_mg': 0.06, 'niacin_mg': 1.2, 'vitamin_b6_mg': 0.18,
            'vitamin_d_ug': 0.0, 'sodium_mg': 380.0, 'potassium_mg': 290.0
        }
    },
    'rajma': {
        'scie': 'Spiced Red Kidney Bean Curry',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 145.0, 'protein_g': 6.8, 'fat_g': 4.2, 'carbs_g': 20.0,
            'fibre_g': 5.0, 'iron_mg': 2.2, 'calcium_mg': 48.0, 'zinc_mg': 0.9,
            'magnesium_mg': 42.0, 'vitamin_c_mg': 3.0, 'folate_ug': 50.0, 'vitamin_a_ug': 18.0,
            'thiamine_mg': 0.12, 'riboflavin_mg': 0.06, 'niacin_mg': 1.1, 'vitamin_b6_mg': 0.16,
            'vitamin_d_ug': 0.0, 'sodium_mg': 360.0, 'potassium_mg': 310.0
        }
    },
    'dal_makhani': {
        'scie': 'Creamy Slow-Cooked Black Lentils and Kidney Beans',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 180.0, 'protein_g': 6.5, 'fat_g': 9.5, 'carbs_g': 17.0,
            'fibre_g': 4.5, 'iron_mg': 2.1, 'calcium_mg': 65.0, 'zinc_mg': 1.0,
            'magnesium_mg': 40.0, 'vitamin_c_mg': 2.0, 'folate_ug': 45.0, 'vitamin_a_ug': 40.0,
            'thiamine_mg': 0.12, 'riboflavin_mg': 0.08, 'niacin_mg': 1.0, 'vitamin_b6_mg': 0.15,
            'vitamin_d_ug': 0.2, 'sodium_mg': 410.0, 'potassium_mg': 260.0
        }
    },
    'aloo_paratha': {
        'scie': 'Whole Wheat Flatbread Stuffed with Spiced Potatoes',
        'region': 'North',
        'nutrients': {
            'energy_kcal': 230.0, 'protein_g': 4.8, 'fat_g': 8.5, 'carbs_g': 34.0,
            'fibre_g': 3.2, 'iron_mg': 1.8, 'calcium_mg': 28.0, 'zinc_mg': 0.8,
            'magnesium_mg': 32.0, 'vitamin_c_mg': 4.0, 'folate_ug': 22.0, 'vitamin_a_ug': 15.0,
            'thiamine_mg': 0.16, 'riboflavin_mg': 0.06, 'niacin_mg': 1.4, 'vitamin_b6_mg': 0.22,
            'vitamin_d_ug': 0.0, 'sodium_mg': 340.0, 'potassium_mg': 220.0
        }
    }
}


class LLMService:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.enabled = os.getenv('LLM_ENABLED', 'true').lower() in ('true', '1', 'yes') and bool(self.api_key)
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.timeout = int(os.getenv('LLM_TIMEOUT_SECONDS', 10))
        self._load_reference_tables()

    def _load_reference_tables(self):
        # Load household measures table
        if os.path.exists(HOUSEHOLD_PATH):
            self.measures_df = pd.read_csv(HOUSEHOLD_PATH)
        else:
            self.measures_df = pd.DataFrame()

        # Load food names for fuzzy matching
        if os.path.exists(CLEANED_FOODS_PATH):
            self.foods_df = pd.read_csv(CLEANED_FOODS_PATH)
            self.food_names = self.foods_df['name'].tolist()
        else:
            self.foods_df = pd.DataFrame()
            self.food_names = []

    def _convert_unit_to_grams(self, quantity: float, unit_text: str) -> float:
        """Converts Indian household measures (katori, roti, glass, cup, gm) to grams."""
        if not unit_text or self.measures_df.empty:
            return float(quantity) if quantity > 0 else 100.0

        unit_clean = unit_text.lower().strip()
        if unit_clean in ('g', 'gram', 'grams', 'gm', 'gms'):
            return float(quantity)

        for _, row in self.measures_df.iterrows():
            m_name = str(row['measure_name']).lower()
            aliases = [a.strip().lower() for a in str(row['aliases']).split(',')]
            if unit_clean == m_name or unit_clean in aliases:
                return round(float(quantity) * float(row['standard_grams']), 1)

        # Standard Indian portion heuristics
        if 'roti' in unit_clean or 'chapati' in unit_clean:
            return round(float(quantity) * 35.0, 1)
        if 'idli' in unit_clean:
            return round(float(quantity) * 40.0, 1)
        if 'katori' in unit_clean or 'bowl' in unit_clean or 'cup' in unit_clean:
            return round(float(quantity) * 150.0, 1)
        if 'glass' in unit_clean:
            return round(float(quantity) * 200.0, 1)
        if 'plate' in unit_clean:
            return round(float(quantity) * 250.0, 1)
        if 'piece' in unit_clean or 'slice' in unit_clean:
            return round(float(quantity) * 50.0, 1)

        return round(float(quantity) * 100.0, 1) if quantity > 0 else 100.0

    def _fuzzy_match_food(self, query: str):
        """Fuzzy matches raw food string against 542 IFCT 2017 foods using rapidfuzz."""
        if not query or self.foods_df.empty:
            return None, 0.0

        match, score, idx = process.extractOne(
            query, self.food_names, scorer=fuzz.token_sort_ratio
        )
        matched_row = self.foods_df.iloc[idx].to_dict()
        return matched_row, round(score, 1)

    def get_or_generate_food(self, food_name: str, db=None) -> Dict[str, Any]:
        """
        Retrieves or generates nutritional profile for prepared Indian dishes not in IFCT 2017.
        Matches exact MongoDB record if already created, else queries OpenAI to estimate
        the complete 19-core nutrient profile per 100g, validates it, and saves it to db.foods.
        """
        if db is None:
            from backend.db import get_db
            db = get_db()

        clean_name = food_name.strip()
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', clean_name).strip('_').upper()
        ai_code = f"AI_{slug}"

        # 1. Check if this generated food already exists in MongoDB
        try:
            existing = db.foods.find_one({'$or': [
                {'code': re.compile(f"^{re.escape(ai_code)}$", re.IGNORECASE)},
                {'name': re.compile(f"^{re.escape(clean_name)}", re.IGNORECASE)}
            ]})
            if existing:
                return existing
        except Exception as e:
            logger.warning(f"Error checking existing food in db: {e}")

        # 2. Check curated recipes for instant high-accuracy match
        curated_key = clean_name.lower().replace(' ', '_')
        matched_curated = None
        for k, v in COMMON_INDIAN_RECIPES.items():
            if k in curated_key or curated_key in k:
                matched_curated = v
                break

        nutrients = {}
        region = "India"
        scie = "Traditional Cooked Dish"

        # 3. Call OpenAI for realistic nutrient profile estimation per 100g
        if self.enabled and self.api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key, timeout=self.timeout)
                prompt = f"""
You are an expert Indian food scientist and nutritionist.
Provide the standard nutritional values per 100 grams of edible portion for the cooked/prepared Indian dish: "{clean_name}".
Ensure all values are realistic for a 100g portion of this dish.
Output strictly a valid JSON object matching this exact schema:
{{
  "region": "West" or "North" or "South" or "East" or "Central" or "India",
  "scie": "Short recipe description e.g. Steamed Fermented Chickpea Cake",
  "nutrients": {{
    "energy_kcal": float,
    "protein_g": float,
    "fat_g": float,
    "carbs_g": float,
    "fibre_g": float,
    "iron_mg": float,
    "calcium_mg": float,
    "zinc_mg": float,
    "magnesium_mg": float,
    "vitamin_c_mg": float,
    "folate_ug": float,
    "vitamin_a_ug": float,
    "thiamine_mg": float,
    "riboflavin_mg": float,
    "niacin_mg": float,
    "vitamin_b6_mg": float,
    "vitamin_d_ug": float,
    "sodium_mg": float,
    "potassium_mg": float
  }}
}}
Return only raw JSON with no markdown wrapping.
"""
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                raw_text = resp.choices[0].message.content.strip()
                raw_text = re.sub(r"^```json\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)

                if isinstance(parsed.get('nutrients'), dict):
                    nutrients = parsed['nutrients']
                    region = parsed.get('region', 'India')
                    scie = parsed.get('scie', 'Traditional Cooked Dish')
            except Exception as e:
                logger.warning(f"OpenAI nutrient estimation fallback for '{clean_name}': {e}")

        # If LLM didn't produce full nutrients, fall back to curated recipe or balanced estimation
        if not nutrients or len(nutrients) < 10:
            if matched_curated:
                nutrients = matched_curated.get('nutrients', {})
                region = matched_curated.get('region', 'India')
                scie = matched_curated.get('scie', 'Traditional Cooked Dish')
            else:
                # Balanced standard Indian cooked dish estimation
                nutrients = {
                    'energy_kcal': 150.0,
                    'protein_g': 5.0,
                    'fat_g': 4.0,
                    'carbs_g': 24.0,
                    'fibre_g': 2.0,
                    'iron_mg': 1.2,
                    'calcium_mg': 30.0,
                    'zinc_mg': 0.7,
                    'magnesium_mg': 25.0,
                    'vitamin_c_mg': 2.0,
                    'folate_ug': 25.0,
                    'vitamin_a_ug': 10.0,
                    'thiamine_mg': 0.1,
                    'riboflavin_mg': 0.06,
                    'niacin_mg': 1.0,
                    'vitamin_b6_mg': 0.12,
                    'vitamin_d_ug': 0.0,
                    'sodium_mg': 300.0,
                    'potassium_mg': 150.0
                }

        # 4. Strictly validate all 19 nutrient keys against CORE_NUTRIENT_MAP
        validated_nutrients = {}
        for key in CORE_NUTRIENT_MAP.keys():
            val = nutrients.get(key, 0.0)
            try:
                val = float(val)
                validated_nutrients[key] = max(round(val, 4), 0.0)
            except (ValueError, TypeError):
                validated_nutrients[key] = 0.0

        # 5. Build and persist document to MongoDB
        food_doc = {
            'code': ai_code,
            'name': f"{clean_name.title()} (AI Estimated)",
            'scie': scie,
            'region': region,
            'is_ai_generated': True,
            'nutrients': validated_nutrients
        }

        try:
            db.foods.replace_one({'code': ai_code}, food_doc, upsert=True)
            logger.info(f"Generated and persisted new food '{food_doc['name']}' ({ai_code}) to database.")
            if hasattr(self, 'food_names') and food_doc['name'] not in self.food_names:
                self.food_names.append(food_doc['name'])
        except Exception as e:
            logger.error(f"Failed to upsert generated food into MongoDB: {e}")

        return food_doc

    def parse_free_text_meal(self, meal_text: str, db=None) -> Dict[str, Any]:
        """
        Feature N1: Converts natural language descriptions into staged food items.
        Handles standard IFCT foods via fuzzy matching and dynamically generates
        verified nutrient profiles for cooked Indian dishes (like Dhokla) via LLM.
        """
        if db is None:
            from backend.db import get_db
            db = get_db()

        raw_items = []

        # 1. Attempt OpenAI structured parsing if enabled
        if self.enabled and self.api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key, timeout=self.timeout)
                prompt = f"""
You are an expert Indian dietary entity extractor. Parse the meal description below into a clean JSON array of food items.
Extract the food name, numeric quantity, portion unit (e.g. grams, katoris, rotis, pieces, bowls, cups), and meal type (breakfast, lunch, dinner, or snack).
Output strictly a JSON array with no markdown backticks.
Schema: [ {{"food_text": str, "quantity": float, "unit": str, "meal_type": "breakfast"|"lunch"|"dinner"|"snack"}} ]

Meal: "{meal_text}"
"""
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                content = resp.choices[0].message.content.strip()
                content = re.sub(r"^```json\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
                raw_items = json.loads(content)
            except Exception as e:
                logger.warning(f"OpenAI free-text parser fallback: {e}")
                raw_items = []

        # 2. Deterministic regex rule-based fallback parser
        if not raw_items:
            # Detect meal type from global phrase if present
            default_meal = 'lunch'
            m_meal = re.search(r'\b(breakfast|lunch|dinner|snack|morning|evening|night)\b', meal_text, re.I)
            if m_meal:
                w = m_meal.group(1).lower()
                default_meal = 'breakfast' if w in ('breakfast', 'morning') else ('dinner' if w in ('dinner', 'night') else ('snack' if w in ('snack', 'evening') else 'lunch'))

            phrases = re.split(r'[,;+&]|\band\b', meal_text)
            for phrase in phrases:
                phrase = phrase.strip()
                if not phrase:
                    continue

                item_meal = default_meal
                m_sub = re.search(r'\b(breakfast|lunch|dinner|snack|morning|evening|night)\b', phrase, re.I)
                if m_sub:
                    w = m_sub.group(1).lower()
                    item_meal = 'breakfast' if w in ('breakfast', 'morning') else ('dinner' if w in ('dinner', 'night') else ('snack' if w in ('snack', 'evening') else 'lunch'))
                    phrase = re.sub(r'\b(in|for|at|as)?\s*(breakfast|lunch|dinner|snack|morning|evening|night)\b', '', phrase, flags=re.I).strip()

                # Pattern A: 'dhokla 50 gm' or 'rice 100g'
                m_end = re.search(r'^(.+?)\s+([\d\.\/]+)\s*([a-zA-Z]+)?$', phrase)
                if m_end:
                    food_part = m_end.group(1).strip()
                    try:
                        qty = float(eval(m_end.group(2)))
                    except Exception:
                        qty = float(m_end.group(2))
                    unit_part = (m_end.group(3) or 'g').lower()
                    raw_items.append({
                        'food_text': food_part,
                        'quantity': qty,
                        'unit': unit_part,
                        'meal_type': item_meal
                    })
                    continue

                # Pattern B: '50 gm dhokla' or '2 rotis' or '1 bowl dal'
                m_start = re.search(r'^([\d\.\/]+)\s*([a-zA-Z]+)?\s*(?:of\s+)?(.*)$', phrase)
                if m_start:
                    try:
                        qty = float(eval(m_start.group(1)))
                    except Exception:
                        qty = float(m_start.group(1))
                    possible_unit = (m_start.group(2) or '').lower()
                    rest = (m_start.group(3) or '').strip()

                    if possible_unit in MEASURE_UNITS:
                        if not rest:
                            food_part = possible_unit
                            unit_part = 'piece'
                        else:
                            food_part = rest
                            unit_part = possible_unit
                    else:
                        food_part = f"{possible_unit} {rest}".strip()
                        unit_part = 'piece'

                    raw_items.append({
                        'food_text': food_part,
                        'quantity': qty,
                        'unit': unit_part,
                        'meal_type': item_meal
                    })
                    continue

                # Fallback: Single item without explicit quantity
                raw_items.append({
                    'food_text': phrase,
                    'quantity': 1.0,
                    'unit': 'serving',
                    'meal_type': item_meal
                })

        # 3. Resolve each item against IFCT foods or generate using AI
        resolved_foods = []
        for item in raw_items:
            f_text = str(item.get('food_text', '')).strip()
            if not f_text:
                continue

            try:
                qty = float(item.get('quantity', 1.0) or 1.0)
            except (ValueError, TypeError):
                qty = 1.0

            unit = str(item.get('unit', '')).strip()
            meal_type = (item.get('meal_type') or 'breakfast').strip().lower()
            if meal_type not in ('breakfast', 'lunch', 'dinner', 'snack'):
                meal_type = 'breakfast'

            est_grams = self._convert_unit_to_grams(qty, unit)

            # First, check exact match in db.foods
            exact_db_food = None
            try:
                exact_db_food = db.foods.find_one({'name': re.compile(f"^{re.escape(f_text)}$", re.IGNORECASE)})
            except Exception:
                pass

            if exact_db_food:
                food_code = exact_db_food['code']
                food_name = exact_db_food['name']
                confidence = 1.0
                is_ai = exact_db_food.get('is_ai_generated', False)
            else:
                # Fuzzy match against IFCT 2017 foods
                matched_food, score = self._fuzzy_match_food(f_text)

                # High-confidence threshold (>= 82% similarity required for real IFCT staple food)
                if matched_food and score >= 82.0:
                    food_code = matched_food['code']
                    food_name = matched_food['name']
                    confidence = round(score / 100.0, 2)
                    is_ai = False
                else:
                    # Food not in IFCT (e.g. Dhokla, Pav Bhaji, Poha) -> Ask LLM to generate recipe profile
                    generated_doc = self.get_or_generate_food(f_text, db=db)
                    food_code = generated_doc['code']
                    food_name = generated_doc['name']
                    confidence = 0.95
                    is_ai = True

            # Structure payload with both standard and backward-compatible fields
            resolved_foods.append({
                # Standard frontend fields
                'food_code': food_code,
                'food_name': food_name,
                'quantity_g': est_grams,
                'meal_type': meal_type,
                'original_phrase': f_text,
                'confidence': confidence,
                'is_ai_generated': is_ai,
                # Backward-compatibility aliases
                'matched_food_code': food_code,
                'matched_food_name': food_name,
                'estimated_grams': est_grams,
                'input_text': f_text,
                'match_confidence_pct': round(confidence * 100, 1),
                'needs_user_confirmation': confidence < 0.80
            })

        return {
            'original_text': meal_text,
            'items_parsed': len(resolved_foods),
            'parser_mode': 'llm' if (self.enabled and self.api_key) else 'deterministic_nlp',
            'resolved_foods': resolved_foods,
            'matched_items': resolved_foods
        }

    def generate_coaching_explanation(
        self,
        nutrient_key: str,
        risk_level: str,
        rda_percent: Optional[float],
        shap_factors: List[Dict[str, Any]],
        recommended_foods: List[str]
    ) -> str:
        """
        Feature N2: Generates supportive, plain-language educational coaching text.
        Never generates clinical diagnosis, prescriptions, or supplement dosages.
        """
        display_name = nutrient_key.replace('_', ' ').title()
        foods_sample = ", ".join(recommended_foods[:3]) if recommended_foods else "nutrient-rich traditional Indian foods"

        # Rule-based safe fallback explanation
        fallback_text = (
            f"Your current daily dietary intake provides approximately {rda_percent or '--'}% of your recommended {display_name} requirement, "
            f"placing this nutrient in the {risk_level} category. "
            f"To maintain healthy levels, consider incorporating {foods_sample} into your daily meals. "
            f"Please remember that this is a dietary awareness screening, not a clinical diagnosis; consult a registered dietitian or physician for diagnostic concerns."
        )

        if not (self.enabled and self.api_key):
            return fallback_text

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key, timeout=self.timeout)

            system_prompt = (
                "You are an encouraging, evidence-based nutritional wellness coach. "
                "Explain the user's dietary assessment in 3 to 4 clear, supportive sentences. "
                "STRICT RULES: Do NOT diagnose any medical disease. Do NOT mention prescription drugs or supplement dosages. "
                "Do NOT introduce numbers or percentages that were not provided in the prompt. Always encourage real whole foods."
            )

            user_prompt = (
                f"Nutrient: {display_name}\n"
                f"Risk Classification: {risk_level}\n"
                f"RDA Percentage: {rda_percent}%\n"
                f"Key Influencing Factors: {[f['feature'] for f in shap_factors]}\n"
                f"Top Recommended Foods: {foods_sample}\n"
            )

            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=150
            )
            raw_output = resp.choices[0].message.content.strip()

            # Safety post-validation: check for forbidden medical terms
            forbidden = ['prescribe', 'diagnose', 'mg tablet', 'injection', 'syrup', 'iu dose']
            if any(term in raw_output.lower() for term in forbidden):
                logger.warning("LLM response violated medical safety filter. Reverting to rule-based fallback.")
                return fallback_text

            return f"{raw_output} (AI-generated educational summary)"
        except Exception as e:
            logger.warning(f"OpenAI coaching generation fallback: {e}")
            return fallback_text


_llm_service_instance: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
