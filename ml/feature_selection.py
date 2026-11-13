"""
Feature Selection Pipeline for NutriScan (Phase C Deliverable)
Ports the comprehensive multi-stage feature selection funnel from the exploratory notebook:
  Stage 1: Variance Threshold Filtering (threshold = 0.01)
  Stage 2: Correlation Redundancy Pruning (|r| > 0.95)
  Stage 3: Statistical Filter Ranking (ANOVA F-statistic & Mutual Information)
  Stage 4: Embedded Random Forest Importance Ranking
  Stage 5: Combined Ensemble Ranking -> Top 15 Features Selection
Saves:
  - ml/reports/feature_ranking.csv
  - ml/reports/feature_ranking_top15.png
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from sklearn.feature_selection import VarianceThreshold, f_classif, mutual_info_classif
from sklearn.ensemble import RandomForestClassifier

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import RANDOM_STATE, CLEANED_DATA_PATH, REPORTS_DIR
from ml.features import load_cleaned_food_data, get_base_nutrient_columns, create_protein_tertile_target


def run_feature_selection():
    print("=" * 75)
    print("NutriScan Feature Selection Funnel (Notebook Port)")
    print("=" * 75)

    df = load_cleaned_food_data(CLEANED_DATA_PATH)
    base_cols = get_base_nutrient_columns(df)
    print(f"Initial numeric nutrient features: {len(base_cols)}")

    # Target: Protein Tertile Level
    df['protein_level'] = create_protein_tertile_target(df, 'protcnt')
    y = df['protein_level']

    # Candidate features exclude the target column itself
    candidate_features = [c for c in base_cols if c not in ('protcnt', 'energy_kcal')]

    # Stage 1: Variance Filtering
    vt = VarianceThreshold(threshold=0.01)
    vt.fit(df[candidate_features])
    kept_var = [c for c, keep in zip(candidate_features, vt.get_support()) if keep]
    dropped_var = set(candidate_features) - set(kept_var)
    print(f"Stage 1 [Variance Filter]: Kept {len(kept_var)} features (dropped {len(dropped_var)} near-zero-variance features)")

    # Stage 2: Correlation Pruning (|r| > 0.95)
    corr_matrix = df[kept_var].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop_corr = [col for col in upper.columns if any(upper[col] > 0.95)]
    candidate_features = [c for c in kept_var if c not in to_drop_corr]
    print(f"Stage 2 [Correlation Pruning]: Dropped {len(to_drop_corr)} redundant cols (|r| > 0.95) -> {len(candidate_features)} features remain")

    X_candidates = df[candidate_features]

    # Stage 3: Statistical Filter (ANOVA F + Mutual Information)
    print("Stage 3 [Statistical Scoring]: Computing ANOVA F-scores and Mutual Information...")
    f_scores = pd.Series(f_classif(X_candidates, y)[0], index=candidate_features).fillna(0)
    mi_scores = pd.Series(mutual_info_classif(X_candidates, y, random_state=RANDOM_STATE), index=candidate_features).fillna(0)

    # Stage 4: Embedded Random Forest Importance
    print("Stage 4 [Embedded Random Forest]: Fitting RandomForest (n_estimators=400)...")
    rf = RandomForestClassifier(n_estimators=400, random_state=RANDOM_STATE)
    rf.fit(X_candidates, y)
    rf_importance = pd.Series(rf.feature_importances_, index=candidate_features)

    # Stage 5: Combined Ranking
    ranking_df = pd.DataFrame({
        'feature': candidate_features,
        'ANOVA_F': f_scores.values,
        'Mutual_Info': mi_scores.values,
        'RF_Importance': rf_importance.values
    })

    ranking_df['F_rank'] = ranking_df['ANOVA_F'].rank(ascending=False)
    ranking_df['MI_rank'] = ranking_df['Mutual_Info'].rank(ascending=False)
    ranking_df['Filter_avg_rank'] = ranking_df[['F_rank', 'MI_rank']].mean(axis=1)
    ranking_df['RF_rank'] = ranking_df['RF_Importance'].rank(ascending=False)
    ranking_df['Final_rank'] = ranking_df[['Filter_avg_rank', 'RF_rank']].mean(axis=1)

    ranking_df = ranking_df.sort_values('Final_rank').reset_index(drop=True)

    # Save ranking CSV
    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_out = os.path.join(REPORTS_DIR, 'feature_ranking.csv')
    ranking_df.to_csv(csv_out, index=False)
    print(f"\nSaved feature rankings -> {csv_out}")

    # Top 15 features plot
    top15 = ranking_df.head(15).copy()
    plt.figure(figsize=(10, 6))
    plt.barh(top15['feature'][::-1], top15['RF_Importance'][::-1], color='#2980b9', edgecolor='black', alpha=0.85)
    plt.xlabel('Random Forest Feature Importance')
    plt.title('Top 15 Features Selected via Multi-Stage Funnel (NutriScan)')
    plt.tight_layout()

    plot_out = os.path.join(REPORTS_DIR, 'feature_ranking_top15.png')
    plt.savefig(plot_out, dpi=150)
    plt.close()
    print(f"Saved feature importance chart -> {plot_out}")

    print("\nTop 15 Selected Features:")
    for idx, row in top15.iterrows():
        print(f"  {idx+1:2d}. {row['feature']:<15} | RF Importance: {row['RF_Importance']:.4f} | Final Rank: {row['Final_rank']:.1f}")

    print("=" * 75)
    return ranking_df, top15['feature'].tolist()


if __name__ == '__main__':
    run_feature_selection()
