"""
Input Validation and Anthropometric Calculation Schemas for NutriScan
"""

import re
from typing import Tuple, Optional, Dict, Any

EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")

ALLOWED_GENDERS = {'male', 'female'}
ALLOWED_ACTIVITY_LEVELS = {'sedentary', 'light', 'moderate', 'active'}
ALLOWED_DIET_PREFERENCES = {'veg', 'non-veg', 'eggetarian', 'vegan'}
ALLOWED_SPECIAL_CONDITIONS = {'none', 'pregnant', 'lactating_0_6m', 'lactating_7_12m'}
ALLOWED_MEAL_TYPES = {'breakfast', 'lunch', 'dinner', 'snack'}


def validate_registration(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or len(name) < 2:
        return False, "Full name must be at least 2 characters long."
    if not email or not EMAIL_REGEX.match(email):
        return False, "Please provide a valid email address."
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."

    return True, None


def calculate_bmi(height_cm: float, weight_kg: float) -> Tuple[float, str]:
    """Calculates BMI and returns (bmi_value, category)."""
    height_m = height_cm / 100.0
    if height_m <= 0:
        return 0.0, "Unknown"
    bmi = round(weight_kg / (height_m ** 2), 2)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25.0:
        category = "Normal weight"
    elif bmi < 30.0:
        category = "Overweight"
    else:
        category = "Obese"

    return bmi, category


def validate_profile(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    try:
        age = int(data.get('age', 0))
    except (ValueError, TypeError):
        return False, "Age must be an integer.", None

    if not (1 <= age <= 120):
        return False, "Age must be between 1 and 120 years.", None

    gender = (data.get('gender') or '').strip().lower()
    if gender not in ALLOWED_GENDERS:
        return False, f"Gender must be one of: {', '.join(sorted(ALLOWED_GENDERS))}.", None

    try:
        height_cm = float(data.get('height_cm', 0.0))
        weight_kg = float(data.get('weight_kg', 0.0))
    except (ValueError, TypeError):
        return False, "Height and weight must be numeric values.", None

    if not (50.0 <= height_cm <= 250.0):
        return False, "Height must be between 50 and 250 cm.", None
    if not (10.0 <= weight_kg <= 300.0):
        return False, "Weight must be between 10 and 300 kg.", None

    activity_level = (data.get('activity_level') or 'sedentary').strip().lower()
    if activity_level not in ALLOWED_ACTIVITY_LEVELS:
        return False, f"Activity level must be one of: {', '.join(sorted(ALLOWED_ACTIVITY_LEVELS))}.", None

    diet_preference = (data.get('diet_preference') or 'veg').strip().lower()
    if diet_preference not in ALLOWED_DIET_PREFERENCES:
        return False, f"Diet preference must be one of: {', '.join(sorted(ALLOWED_DIET_PREFERENCES))}.", None

    special_condition = (data.get('special_condition') or 'none').strip().lower()
    if special_condition not in ALLOWED_SPECIAL_CONDITIONS:
        special_condition = 'none'

    bmi, bmi_category = calculate_bmi(height_cm, weight_kg)

    cleaned_profile = {
        'age': age,
        'gender': gender,
        'height_cm': height_cm,
        'weight_kg': weight_kg,
        'bmi': bmi,
        'bmi_category': bmi_category,
        'activity_level': activity_level,
        'diet_preference': diet_preference,
        'special_condition': special_condition,
        'ai_consent': bool(data.get('ai_consent', False))
    }
    return True, None, cleaned_profile
