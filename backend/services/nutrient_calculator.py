"""
Nutrient Calculator Service for NutriScan
Calculates absolute nutrient intake totals from food quantities,
converts weekly frequencies to daily intake equivalents,
and benchmarks nutrient totals against ICMR-NIN 2020 RDA recommendations.
"""

from typing import List, Dict, Any, Optional
from data_pipeline.nutrient_mapping import CORE_NUTRIENT_MAP
from backend.services.rda_service import get_rda_service


def calculate_intake_summary(
    entries: List[Dict[str, Any]],
    user_gender: Optional[str] = None,
    user_age: Optional[int] = None,
    special_condition: str = 'none'
) -> Dict[str, Any]:
    """
    Computes total nutrient consumption across multiple food entries.
    
    Each entry:
    {
        'food_code': str,
        'food_name': str,
        'quantity_g': float,
        'nutrients': dict (per 100g),
        'frequency_per_week': Optional[float] (default: 7 = daily)
    }
    
    Returns:
    {
        'item_count': int,
        'total_grams_daily': float,
        'nutrients': {
            nutrient_key: {
                'display_name': str,
                'unit': str,
                'total_amount': float,
                'rda_value': Optional[float],
                'rda_percent': Optional[float],
                'status_note': Optional[str]
            }
        }
    }
    """
    rda_service = get_rda_service()
    user_rda = {}
    if user_gender and user_age is not None:
        user_rda = rda_service.get_rda_for_profile(user_gender, user_age, special_condition)

    # Initialize totals for all core nutrients
    totals: Dict[str, float] = {k: 0.0 for k in CORE_NUTRIENT_MAP.keys()}
    total_grams_daily = 0.0

    for item in entries:
        quantity_g = float(item.get('quantity_g', 0.0))
        freq = item.get('frequency_per_week')
        if freq is not None and freq > 0:
            daily_g = quantity_g * float(freq) / 7.0
        else:
            daily_g = quantity_g

        total_grams_daily += daily_g
        factor = daily_g / 100.0

        item_nutrients = item.get('nutrients', {})
        for nut_key in totals.keys():
            val_100g = float(item_nutrients.get(nut_key, 0.0) or 0.0)
            totals[nut_key] += val_100g * factor

    # Benchmark against RDA
    nutrients_summary = {}
    for key, meta in CORE_NUTRIENT_MAP.items():
        total_val = round(totals[key], 2)
        rda_info = user_rda.get(key)

        if rda_info:
            rda_val = rda_info['rda_value']
            rda_percent = round((total_val / rda_val) * 100.0, 1) if rda_val > 0 else 0.0
            status_note = "Target met" if rda_percent >= 100.0 else f"{rda_percent}% of daily requirement"
        else:
            rda_val = None
            rda_percent = None
            status_note = "RDA pending in ICMR-NIN 2020 reference table for this cohort"

        nutrients_summary[key] = {
            'display_name': meta['display_name'],
            'unit': meta['unit'],
            'group': meta['group'],
            'total_amount': total_val,
            'rda_value': rda_val,
            'rda_percent': rda_percent,
            'status_note': status_note
        }

    return {
        'item_count': len(entries),
        'total_grams_daily': round(total_grams_daily, 2),
        'nutrients': nutrients_summary
    }
