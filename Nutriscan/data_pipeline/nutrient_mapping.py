"""
Nutrient Mapping Module for NutriScan
Defines mapping between raw IFCT 2017 column names and friendly project keys,
display names, units, and nutrient groups used across the Backend, Services, and ML.
"""

# Core nutrient mapping dictionary
# Keys: friendly_key
# Values: dict containing ifct_column, display_name, unit, group, notes, derivation
CORE_NUTRIENT_MAP = {
    'energy_kcal': {
        'ifct_col': 'enerc',
        'display_name': 'Energy',
        'unit': 'kcal',
        'group': 'Macronutrients',
        'notes': 'Converted from raw IFCT enerc (kJ) by dividing by 4.184',
        'derivation': 'divide_4_184'
    },
    'protein_g': {
        'ifct_col': 'protcnt',
        'display_name': 'Protein',
        'unit': 'g',
        'group': 'Macronutrients',
        'notes': 'Total protein content per 100g edible portion',
        'derivation': 'direct'
    },
    'fat_g': {
        'ifct_col': 'fatce',
        'display_name': 'Total Fat',
        'unit': 'g',
        'group': 'Macronutrients',
        'notes': 'Crude ether extract / total fat per 100g edible portion',
        'derivation': 'direct'
    },
    'carbs_g': {
        'ifct_col': 'choavldf',
        'display_name': 'Available Carbohydrates',
        'unit': 'g',
        'group': 'Macronutrients',
        'notes': 'Available carbohydrates by difference per 100g edible portion',
        'derivation': 'direct'
    },
    'fibre_g': {
        'ifct_col': 'fibtg',
        'display_name': 'Dietary Fibre',
        'unit': 'g',
        'group': 'Macronutrients',
        'notes': 'Total dietary fibre per 100g edible portion',
        'derivation': 'direct'
    },
    'iron_mg': {
        'ifct_col': 'fe',
        'display_name': 'Iron',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total iron per 100g edible portion',
        'derivation': 'direct'
    },
    'calcium_mg': {
        'ifct_col': 'ca',
        'display_name': 'Calcium',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total calcium per 100g edible portion',
        'derivation': 'direct'
    },
    'zinc_mg': {
        'ifct_col': 'zn',
        'display_name': 'Zinc',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total zinc per 100g edible portion',
        'derivation': 'direct'
    },
    'magnesium_mg': {
        'ifct_col': 'mg',
        'display_name': 'Magnesium',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total magnesium per 100g edible portion',
        'derivation': 'direct'
    },
    'vitamin_c_mg': {
        'ifct_col': 'vitc',
        'display_name': 'Vitamin C (Ascorbic Acid)',
        'unit': 'mg',
        'group': 'Vitamins',
        'notes': 'Total vitamin C per 100g edible portion',
        'derivation': 'direct'
    },
    'folate_ug': {
        'ifct_col': 'folsum',
        'display_name': 'Total Folate',
        'unit': 'µg',
        'group': 'Vitamins',
        'notes': 'Sum of dietary folates per 100g edible portion',
        'derivation': 'direct'
    },
    'vitamin_a_ug': {
        'ifct_col': 'retol',
        'display_name': 'Vitamin A (Retinol)',
        'unit': 'µg',
        'group': 'Vitamins',
        'notes': 'Preformed retinol in µg. Carotenoids (e.g. beta-carotene cartb) are cataloged separately in IFCT.',
        'derivation': 'direct'
    },
    'thiamine_mg': {
        'ifct_col': 'thia',
        'display_name': 'Thiamine (Vitamin B1)',
        'unit': 'mg',
        'group': 'Vitamins',
        'notes': 'Thiamine per 100g edible portion',
        'derivation': 'direct'
    },
    'riboflavin_mg': {
        'ifct_col': 'ribf',
        'display_name': 'Riboflavin (Vitamin B2)',
        'unit': 'mg',
        'group': 'Vitamins',
        'notes': 'Riboflavin per 100g edible portion',
        'derivation': 'direct'
    },
    'niacin_mg': {
        'ifct_col': 'nia',
        'display_name': 'Niacin (Vitamin B3)',
        'unit': 'mg',
        'group': 'Vitamins',
        'notes': 'Niacin per 100g edible portion',
        'derivation': 'direct'
    },
    'vitamin_b6_mg': {
        'ifct_col': 'vitb6c',
        'display_name': 'Vitamin B6',
        'unit': 'mg',
        'group': 'Vitamins',
        'notes': 'Total vitamin B6 per 100g edible portion',
        'derivation': 'direct'
    },
    'vitamin_d_ug': {
        'ifct_col': ['ergcal', 'chocal'],
        'display_name': 'Vitamin D',
        'unit': 'µg',
        'group': 'Vitamins',
        'notes': 'Approximation calculated as sum of ergocalciferol (ergcal) and cholecalciferol (chocal)',
        'derivation': 'sum_ergcal_chocal'
    },
    'sodium_mg': {
        'ifct_col': 'na',
        'display_name': 'Sodium',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total sodium per 100g edible portion',
        'derivation': 'direct'
    },
    'potassium_mg': {
        'ifct_col': 'k',
        'display_name': 'Potassium',
        'unit': 'mg',
        'group': 'Minerals',
        'notes': 'Total potassium per 100g edible portion',
        'derivation': 'direct'
    }
}

# Explicitly documented missing nutrients in IFCT 2017
UNAVAILABLE_NUTRIENTS = {
    'vitamin_b12_ug': {
        'display_name': 'Vitamin B12 (Cobalamin)',
        'unit': 'µg',
        'status': 'Not available in IFCT 2017 tables. Must not be fabricated.'
    }
}

REGION_MAP = {
    1: 'North',
    2: 'East',
    3: 'South',
    4: 'West',
    5: 'Central',
    6: 'Pooled/Multi-region',
    10: 'Other'
}

def extract_core_nutrients(row_dict):
    """
    Given a dictionary of a food item with raw IFCT columns (or series),
    computes and returns a dictionary of friendly nutrient keys and values (per 100g).
    """
    result = {}
    for key, meta in CORE_NUTRIENT_MAP.items():
        derivation = meta['derivation']
        if derivation == 'direct':
            col = meta['ifct_col']
            val = float(row_dict.get(col, 0.0) or 0.0)
            result[key] = round(val, 4)
        elif derivation == 'divide_4_184':
            col = meta['ifct_col']
            val = float(row_dict.get(col, 0.0) or 0.0)
            result[key] = round(val / 4.184, 4)
        elif derivation == 'sum_ergcal_chocal':
            erg = float(row_dict.get('ergcal', 0.0) or 0.0)
            cho = float(row_dict.get('chocal', 0.0) or 0.0)
            result[key] = round(erg + cho, 4)
    return result
