"""
NHANES (National Health and Nutrition Examination Survey) Data Loader & Pipeline
Merges demographic, dietary intake, and clinical laboratory files on respondent sequence key 'SEQN'.
Applies evidence-based WHO / NIH clinical biomarker cutoffs to create ground-truth risk labels.
If raw XPT files are placed in ml/data/nhanes/, they are parsed directly;
otherwise, a high-fidelity distribution-matching cohort is synthesized to validate Variant A training.
"""

import os
import sys
import glob
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import NHANES_DIR, NHANES_PROCESSED_PATH, LAB_THRESHOLDS, RANDOM_STATE


def inspect_and_load_nhanes_files(nhanes_dir=NHANES_DIR):
    """
    Scans ml/data/nhanes/ for NHANES cycle XPT or CSV files.
    Returns merged DataFrame on SEQN or None if no files are found.
    """
    xpt_files = glob.glob(os.path.join(nhanes_dir, '**', '*.XPT'), recursive=True) + \
                glob.glob(os.path.join(nhanes_dir, '**', '*.xpt'), recursive=True)
    csv_files = glob.glob(os.path.join(nhanes_dir, '**', '*.csv'), recursive=True)

    if not xpt_files and not csv_files:
        return None

    print(f"[NHANES Loader] Found {len(xpt_files)} XPT files and {len(csv_files)} CSV files in {nhanes_dir}")
    dfs = []
    for f in (xpt_files + csv_files):
        try:
            if f.lower().endswith('.xpt'):
                sub_df = pd.read_sas(f, format='xport')
            else:
                sub_df = pd.read_csv(f)
            # Normalize column names to uppercase
            sub_df.columns = [c.upper() for c in sub_df.columns]
            if 'SEQN' in sub_df.columns:
                dfs.append(sub_df)
                print(f"  Loaded {os.path.basename(f)}: {sub_df.shape[0]} rows, cols: {list(sub_df.columns[:8])}")
        except Exception as e:
            print(f"  Error loading {f}: {e}")

    if not dfs:
        return None

    # Merge sequentially on SEQN
    merged = dfs[0]
    for other in dfs[1:]:
        merged = pd.merge(merged, other, on='SEQN', how='inner')
    print(f"[NHANES Loader] Successfully merged real NHANES files: {merged.shape}")
    return merged


def generate_nhanes_cohort_dataset(num_records=4000, random_seed=RANDOM_STATE):
    """
    Generates a realistic clinical cohort matching NHANES demographic,
    dietary recall (DR1TOT), and laboratory biomarker distributions.
    """
    np.random.seed(random_seed)
    print(f"[NHANES Loader] Generating NHANES clinical cohort ({num_records} respondents)...")

    seqn = np.arange(100001, 100001 + num_records)
    gender = np.random.choice([1, 2], size=num_records, p=[0.49, 0.51])  # 1: Male, 2: Female
    age = np.random.randint(19, 75, size=num_records)
    
    # Anthropometrics
    bmi = np.random.normal(loc=26.5, scale=5.2, size=num_records).clip(16.0, 48.0).round(1)

    # Dietary Recall (DR1TOT variables)
    loc_energy = np.where(gender == 1, 2100.0, 1650.0)
    energy_kcal = np.random.normal(loc=loc_energy, scale=450, size=num_records).clip(600, 4200)
    protein_g = np.random.normal(loc=78.0, scale=24.0, size=num_records).clip(15.0, 180.0)
    fat_g = np.random.normal(loc=72.0, scale=25.0, size=num_records).clip(10.0, 160.0)
    carbs_g = np.random.normal(loc=240.0, scale=75.0, size=num_records).clip(40.0, 550.0)
    fibre_g = np.random.normal(loc=16.0, scale=7.0, size=num_records).clip(2.0, 50.0)

    iron_mg = np.random.normal(loc=14.5, scale=5.5, size=num_records).clip(2.0, 45.0)
    calcium_mg = np.random.normal(loc=820.0, scale=320.0, size=num_records).clip(100.0, 2400.0)
    zinc_mg = np.random.normal(loc=11.0, scale=4.2, size=num_records).clip(1.5, 30.0)
    magnesium_mg = np.random.normal(loc=280.0, scale=95.0, size=num_records).clip(50.0, 700.0)
    vitamin_c_mg = np.random.exponential(scale=65.0, size=num_records).clip(2.0, 350.0)
    folate_ug = np.random.normal(loc=380.0, scale=140.0, size=num_records).clip(40.0, 1000.0)
    vitamin_a_ug = np.random.normal(loc=600.0, scale=280.0, size=num_records).clip(20.0, 2200.0)

    thiamine_mg = np.random.normal(loc=1.5, scale=0.5, size=num_records).clip(0.2, 4.0)
    riboflavin_mg = np.random.normal(loc=2.0, scale=0.7, size=num_records).clip(0.3, 5.0)
    niacin_mg = np.random.normal(loc=24.0, scale=8.0, size=num_records).clip(3.0, 60.0)
    vitamin_b6_mg = np.random.normal(loc=1.9, scale=0.7, size=num_records).clip(0.3, 5.0)
    vitamin_d_ug = np.random.exponential(scale=5.0, size=num_records).clip(0.1, 35.0)
    sodium_mg = np.random.normal(loc=3200.0, scale=900.0, size=num_records).clip(800.0, 7000.0)
    potassium_mg = np.random.normal(loc=2400.0, scale=700.0, size=num_records).clip(600.0, 5500.0)

    # -------------------------------------------------------------
    # Clinical Laboratory Biomarkers correlated with intake + biological variance
    # -------------------------------------------------------------
    # Serum Ferritin (µg/L): correlated with dietary iron and gender (females lower)
    gender_ferritin_penalty = np.where(gender == 2, 25.0, 0.0)
    ferritin = (iron_mg * 3.8 - gender_ferritin_penalty + np.random.normal(30, 20, num_records)).clip(4.0, 400.0)

    # Serum 25(OH)D (nmol/L): correlated with Vitamin D intake + sun variance
    vit_d_serum = (vitamin_d_ug * 2.8 + np.random.normal(45, 18, num_records)).clip(12.0, 140.0)

    # Serum Folate (nmol/L): correlated with folate intake
    folate_serum = (folate_ug * 0.042 + np.random.normal(12, 6, num_records)).clip(3.0, 55.0)

    # Serum Zinc (µmol/L): correlated with zinc intake
    zinc_serum = (zinc_mg * 0.45 + np.random.normal(9.0, 2.2, num_records)).clip(6.0, 22.0)

    # Build DataFrame
    df = pd.DataFrame({
        'SEQN': seqn,
        'RIAGENDR': gender,
        'RIDAGEYR': age,
        'BMXBMI': bmi,
        'DR1TKCAL': energy_kcal.round(1),
        'DR1TPROT': protein_g.round(2),
        'DR1TTFAT': fat_g.round(2),
        'DR1TCARB': carbs_g.round(2),
        'DR1TFIBE': fibre_g.round(2),
        'DR1TFE': iron_mg.round(2),
        'DR1TCALC': calcium_mg.round(2),
        'DR1TZINC': zinc_mg.round(2),
        'DR1TMAGN': magnesium_mg.round(2),
        'DR1TVC': vitamin_c_mg.round(2),
        'DR1TFDN': folate_ug.round(2),
        'DR1TVARA': vitamin_a_ug.round(2),
        'DR1TVB1': thiamine_mg.round(2),
        'DR1TVB2': riboflavin_mg.round(2),
        'DR1TNIAC': niacin_mg.round(2),
        'DR1TVB6': vitamin_b6_mg.round(2),
        'DR1TVD': vitamin_d_ug.round(2),
        'DR1TSODI': sodium_mg.round(1),
        'DR1TPOTA': potassium_mg.round(1),
        # Laboratory Biomarkers
        'LBDFER': ferritin.round(1),
        'LBXVIDMS': vit_d_serum.round(1),
        'LBDFOT': folate_serum.round(1),
        'LBXZNC': zinc_serum.round(1)
    })

    return df


def assign_clinical_ground_truth_labels(df):
    """
    Applies evidence-based WHO and NIH clinical cutoffs from ml/config.py:
      - 0: High Risk
      - 1: Moderate Risk
      - 2: Low Risk (Adequate)
    """
    data = df.copy()

    # 1. Iron Status via Serum Ferritin (WHO 2020)
    ferritin = data['LBDFER']
    iron_risk = np.where(ferritin < LAB_THRESHOLDS['iron_ferritin_ug_L']['high_risk_cutoff'], 0,
                np.where(ferritin < LAB_THRESHOLDS['iron_ferritin_ug_L']['mod_risk_cutoff'], 1, 2))
    data['label_iron_mg'] = iron_risk

    # 2. Vitamin D Status via 25(OH)D (IOM / Endocrine Society)
    vit_d = data['LBXVIDMS']
    vit_d_risk = np.where(vit_d < LAB_THRESHOLDS['vitamin_d_25ohd_nmol_L']['high_risk_cutoff'], 0,
                 np.where(vit_d < LAB_THRESHOLDS['vitamin_d_25ohd_nmol_L']['mod_risk_cutoff'], 1, 2))
    data['label_vitamin_d_ug'] = vit_d_risk

    # 3. Folate Status via Serum Folate (WHO 2015)
    folate = data['LBDFOT']
    folate_risk = np.where(folate < LAB_THRESHOLDS['folate_serum_nmol_L']['high_risk_cutoff'], 0,
                  np.where(folate < LAB_THRESHOLDS['folate_serum_nmol_L']['mod_risk_cutoff'], 1, 2))
    data['label_folate_ug'] = folate_risk

    # 4. Zinc Status via Serum Zinc (IZiNCG / WHO)
    zinc = data['LBXZNC']
    zinc_risk = np.where(zinc < LAB_THRESHOLDS['zinc_serum_umol_L']['high_risk_cutoff'], 0,
                np.where(zinc < LAB_THRESHOLDS['zinc_serum_umol_L']['mod_risk_cutoff'], 1, 2))
    data['label_zinc_mg'] = zinc_risk

    # 5. Protein Status: Intake vs RDA (ICMR-NIN 2020 benchmark: 54g male, 46g female)
    ref_protein = np.where(data['RIAGENDR'] == 1, 54.0, 46.0)
    prot_pct = (data['DR1TPROT'] / ref_protein) * 100.0
    prot_risk = np.where(prot_pct < 50.0, 0, np.where(prot_pct < 80.0, 1, 2))
    data['label_protein_g'] = prot_risk

    # 6. Calcium Status: Intake vs RDA (1000mg)
    ca_pct = (data['DR1TCALC'] / 1000.0) * 100.0
    ca_risk = np.where(ca_pct < 50.0, 0, np.where(ca_pct < 80.0, 1, 2))
    data['label_calcium_mg'] = ca_risk

    # 7. Vitamin C Status: Intake vs RDA (80mg male, 65mg female)
    ref_vitc = np.where(data['RIAGENDR'] == 1, 80.0, 65.0)
    vitc_pct = (data['DR1TVC'] / ref_vitc) * 100.0
    vitc_risk = np.where(vitc_pct < 50.0, 0, np.where(vitc_pct < 80.0, 1, 2))
    data['label_vitamin_c_mg'] = vitc_risk

    return data


def load_or_create_nhanes_dataset():
    """Main pipeline execution for NHANES loader."""
    print("=" * 75)
    print("NutriScan NHANES Data Pipeline (Phase I Deliverable)")
    print("=" * 75)

    real_data = inspect_and_load_nhanes_files(NHANES_DIR)
    if real_data is not None and not real_data.empty:
        print("[NHANES Loader] Using real NHANES survey data from directory.")
        df = real_data
    else:
        print("[NHANES Loader] No raw XPT/CSV files placed in ml/data/nhanes/. Generating distribution-matched cohort...")
        df = generate_nhanes_cohort_dataset(num_records=4000)

    labeled_df = assign_clinical_ground_truth_labels(df)
    os.makedirs(os.path.dirname(NHANES_PROCESSED_PATH), exist_ok=True)
    labeled_df.to_csv(NHANES_PROCESSED_PATH, index=False)
    print(f"[NHANES Loader] Saved merged and clinically labeled dataset -> {NHANES_PROCESSED_PATH} (Shape: {labeled_df.shape})")

    print("\nClinical Ground Truth Class Distributions:")
    for nut in ['protein_g', 'iron_mg', 'calcium_mg', 'zinc_mg', 'vitamin_c_mg', 'folate_ug']:
        col = f"label_{nut}"
        counts = labeled_df[col].value_counts().to_dict()
        print(f"  {nut:<16}: High (0)={counts.get(0,0)}, Moderate (1)={counts.get(1,0)}, Low (2)={counts.get(2,0)}")

    print("=" * 75)
    return labeled_df


if __name__ == '__main__':
    load_or_create_nhanes_dataset()
