"""
Data Cleaning & Preprocessing Pipeline for NutriScan (Phase A Deliverable)
Loads raw IFCT 2017 composition table, cleans, transforms, converts energy,
flags near-zero-variance features, and exports processed datasets with validation reports.
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.feature_selection import VarianceThreshold

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from data_pipeline.nutrient_mapping import REGION_MAP, CORE_NUTRIENT_MAP, extract_core_nutrients

RAW_DATA_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'ifct2017_compositions.csv')
CLEANED_FULL_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'ifct2017_cleaned_full.csv')
SLIM_FOODS_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'foods_for_db.csv')


def clean_ifct_dataset(raw_path=RAW_DATA_PATH):
    print("=" * 70)
    print("NutriScan Data Pipeline: Loading and Cleaning IFCT 2017 Dataset")
    print("=" * 70)

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw data file not found at: {raw_path}")

    # 1. Load CSV with utf-8-sig encoding to handle BOM correctly
    raw = pd.read_csv(raw_path, encoding='utf-8-sig')
    print(f"Loaded raw dataset: {raw.shape[0]} rows, {raw.shape[1]} columns")

    # 2. Identify and separate column groups
    id_cols = ['code', 'name', 'scie', 'regn']
    error_cols = [c for c in raw.columns if c.endswith('_e')]
    base_nutrient_cols = [c for c in raw.columns if c not in id_cols and not c.endswith('_e')]

    print(f"Columns breakdown: {len(id_cols)} ID cols, {len(base_nutrient_cols)} base nutrients, {len(error_cols)} error (_e) cols")
    print(f"Dropping all {len(error_cols)} measurement error (_e) columns...")
    df = raw[id_cols + base_nutrient_cols].copy()

    # 3. Map region codes to descriptive labels
    df['region'] = df['regn'].map(REGION_MAP).fillna('Other')
    print("Mapped region codes to descriptive labels:")
    print(df['region'].value_counts().to_string())

    # 4. Check duplicates
    dup_codes = df['code'].duplicated().sum()
    dup_names = df['name'].str.lower().duplicated().sum()
    print(f"\nDuplicates Check: duplicate codes = {dup_codes}, duplicate names = {dup_names}")

    # 5. Check and handle missing values
    missing_before = df.isna().sum()
    missing_cols_before = missing_before[missing_before > 0]
    print("\nMissing values before imputation:")
    for col, count in missing_cols_before.items():
        print(f"  - {col}: {count} missing ({count / len(df) * 100:.2f}%)")

    # Fill missing scientific name with "Unknown"
    df['scie'] = df['scie'].fillna('Unknown')

    # Impute numeric gaps with column median (e.g. biot has 8 missing cells)
    for col in base_nutrient_cols:
        if df[col].isna().sum() > 0:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            print(f"  Imputed missing values in '{col}' with median = {median_val:.4f}")

    missing_after = df.isna().sum().sum()
    print(f"Total missing values after cleaning: {missing_after}")

    # 6. Check negative values
    numeric_df = df[base_nutrient_cols]
    negative_counts = (numeric_df < 0).sum()
    neg_total = negative_counts.sum()
    print(f"Negative values across numeric nutrient columns: {neg_total}")
    if neg_total > 0:
        # Clip any spurious negative values to 0
        df[base_nutrient_cols] = df[base_nutrient_cols].clip(lower=0.0)
        print("Clipped negative values to 0.0")

    # 7. Energy conversion (enerc is in kJ -> convert to energy_kcal)
    if 'enerc' in df.columns:
        df['enerc_kj'] = df['enerc']
        df['energy_kcal'] = (df['enerc'] / 4.184).round(2)
        print(f"Energy converted: 'enerc' (kJ) -> 'energy_kcal' (kcal). Mean energy: {df['energy_kcal'].mean():.1f} kcal/100g")

    # 8. Detect near-zero-variance columns (variance threshold < 0.01)
    # They are flagged and documented but KEPT in the cleaned full dataset
    vt = VarianceThreshold(threshold=0.01)
    vt.fit(df[base_nutrient_cols])
    low_var_cols = [c for c, keep in zip(base_nutrient_cols, vt.get_support()) if not keep]
    print(f"\nIdentified {len(low_var_cols)} near-zero-variance columns (variance < 0.01):")
    print(f"  {', '.join(low_var_cols)}")
    print("  Note: Keeping all columns in ifct2017_cleaned_full.csv as required by specification.")

    # 9. Outlier analysis by IQR for key nutrients
    key_nutrients = ['protcnt', 'fatce', 'fe', 'ca', 'zn', 'vitc']
    print("\nOutlier Detection (1.5 * IQR rule) for Key Nutrients:")
    for nut in key_nutrients:
        if nut in df.columns:
            q25 = df[nut].quantile(0.25)
            q75 = df[nut].quantile(0.75)
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            outliers = df[(df[nut] < lower_bound) | (df[nut] > upper_bound)]
            max_item = df.loc[df[nut].idxmax()]
            print(f"  - {nut:8s}: Q1={q25:6.2f}, Q3={q75:6.2f}, IQR={iqr:6.2f} | Outliers: {len(outliers):3d} | Max: {max_item['name']} ({max_item[nut]:.2f})")

    # 10. Save cleaned full dataset
    os.makedirs(os.path.dirname(CLEANED_FULL_PATH), exist_ok=True)
    df.to_csv(CLEANED_FULL_PATH, index=False, encoding='utf-8')
    print(f"\nSaved cleaned full dataset -> {CLEANED_FULL_PATH} (Shape: {df.shape})")

    # 11. Generate and save slim table for application DB (foods_for_db.csv)
    slim_rows = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        nutrients = extract_core_nutrients(row_dict)
        item = {
            'code': row['code'],
            'name': row['name'],
            'scie': row['scie'],
            'region': row['region']
        }
        item.update(nutrients)
        slim_rows.append(item)

    slim_df = pd.DataFrame(slim_rows)
    slim_df.to_csv(SLIM_FOODS_PATH, index=False, encoding='utf-8')
    print(f"Saved application slim dataset -> {SLIM_FOODS_PATH} (Shape: {slim_df.shape})")

    print("=" * 70)
    print("Data Cleaning & Validation Pipeline Finished Successfully!")
    print("=" * 70)
    return df, slim_df


if __name__ == '__main__':
    clean_ifct_dataset()
