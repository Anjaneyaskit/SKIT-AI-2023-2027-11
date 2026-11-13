"""
Machine Learning Configuration for NutriScan (Sprint 3 & 4 Extended)
Constants, clinical lab biomarker thresholds, feature definitions, and model paths.
"""

import os

RANDOM_STATE = 42

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Dataset paths
CLEANED_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')
SYNTHETIC_DATA_PATH = os.path.join(PROJECT_ROOT, 'ml', 'data', 'synthetic_users.csv')
NHANES_DIR = os.path.join(PROJECT_ROOT, 'ml', 'data', 'nhanes')
NHANES_PROCESSED_PATH = os.path.join(PROJECT_ROOT, 'ml', 'data', 'nhanes_merged.csv')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'reports')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'ml', 'models')
QUESTIONNAIRE_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'questionnaire.json')
HOUSEHOLD_MEASURES_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'household_measures.csv')

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(NHANES_DIR, exist_ok=True)

# Target nutrients for Sprint 3 & Sprint 4 risk screening
TARGET_NUTRIENTS = [
    'protein_g',
    'iron_mg',
    'calcium_mg',
    'zinc_mg',
    'vitamin_c_mg',
    'folate_ug'
]

# Risk classification labels
RISK_CLASSES = ['High Risk', 'Moderate Risk', 'Low Risk']
RISK_MAP = {
    0: 'High Risk',
    1: 'Moderate Risk',
    2: 'Low Risk'
}

# -------------------------------------------------------------------------
# Evidence-Based Clinical Laboratory Biomarker Thresholds
# Referenced from WHO, NIH Office of Dietary Supplements (ODS), and IOM guidelines
# -------------------------------------------------------------------------
LAB_THRESHOLDS = {
    # WHO Guideline: Use of ferritin concentrations to assess iron status (2020)
    # Unit: µg/L (ng/mL)
    'iron_ferritin_ug_L': {
        'high_risk_cutoff': 15.0,    # < 15 µg/L: Depleted iron stores / Iron deficiency
        'mod_risk_cutoff': 30.0,     # 15 - 30 µg/L: Mildly depleted iron stores
        'adequate_cutoff': 30.0,     # >= 30 µg/L: Adequate iron reserves
        'source': 'WHO (2020) Serum Ferritin Guideline'
    },
    # Institute of Medicine (IOM) & Endocrine Society Clinical Guidelines
    # Unit: nmol/L for serum 25-hydroxyvitamin D [25(OH)D]
    'vitamin_d_25ohd_nmol_L': {
        'high_risk_cutoff': 30.0,    # < 30 nmol/L (< 12 ng/mL): Deficiency (rickets/osteomalacia risk)
        'mod_risk_cutoff': 50.0,     # 30 - 50 nmol/L (12 - 20 ng/mL): Inadequacy / Sub-optimal bone health
        'adequate_cutoff': 50.0,     # >= 50 nmol/L (>= 20 ng/mL): Sufficient
        'source': 'IOM / NIH Office of Dietary Supplements'
    },
    # WHO / NIH ODS Guidelines for Serum Cobalamin
    # Unit: pmol/L
    'vitamin_b12_pmol_L': {
        'high_risk_cutoff': 148.0,   # < 148 pmol/L (< 200 pg/mL): Frank deficiency
        'mod_risk_cutoff': 221.0,    # 148 - 221 pmol/L: Marginal / borderline
        'adequate_cutoff': 221.0,    # >= 221 pmol/L: Adequate
        'source': 'WHO / NIH ODS Clinical Guidance'
    },
    # WHO Guideline on Serum and Red Blood Cell Folate Concentrations (2015)
    # Unit: nmol/L
    'folate_serum_nmol_L': {
        'high_risk_cutoff': 10.0,    # < 10 nmol/L (< 4.4 ng/mL): Folate deficiency (megaloblastic anemia risk)
        'mod_risk_cutoff': 15.0,     # 10 - 15 nmol/L: Elevated NTD risk / Marginal
        'adequate_cutoff': 15.0,     # >= 15 nmol/L: Adequate
        'source': 'WHO (2015) Serum and RBC Folate Guideline'
    },
    # International Zinc Nutrition Consultative Group (IZiNCG) / WHO
    # Unit: µmol/L (fasting morning serum zinc)
    'zinc_serum_umol_L': {
        'high_risk_cutoff': 10.7,    # < 10.7 µmol/L (< 70 µg/dL): Zinc deficiency
        'mod_risk_cutoff': 12.0,     # 10.7 - 12.0 µmol/L: Low-normal
        'adequate_cutoff': 12.0,     # >= 12.0 µmol/L: Adequate
        'source': 'IZiNCG / WHO Technical Guidance'
    },
    # Nutrients without routine single-lab survey biomarker
    'protein_g': {
        'method': 'intake_vs_rda',
        'high_risk_pct': 50.0,       # < 50% of RDA: High deficiency risk
        'mod_risk_pct': 80.0,        # 50 - 80% of RDA: Moderate risk
        'source': 'ICMR-NIN 2020 RDA Dietary Intake Benchmarking'
    },
    'calcium_mg': {
        'method': 'intake_vs_rda',
        'high_risk_pct': 50.0,
        'mod_risk_pct': 80.0,
        'source': 'ICMR-NIN 2020 RDA (Serum calcium is homeostatically regulated by bone resorption)'
    },
    'vitamin_c_mg': {
        'method': 'intake_vs_rda',
        'high_risk_pct': 50.0,
        'mod_risk_pct': 80.0,
        'source': 'ICMR-NIN 2020 RDA Dietary Intake Benchmarking'
    }
}
