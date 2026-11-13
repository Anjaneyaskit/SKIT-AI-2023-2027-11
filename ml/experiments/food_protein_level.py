"""
Food Protein Level Classification Experiment (Sprint 1 Pipeline Demo)
Demonstrates multi-class classification (Low, Moderate, High protein) on individual FOOD items
using the top-15 selected features.

IMPORTANT ARCHITECTURAL NOTE:
This experiment classifies FOOD ITEMS using nutrient composition profiles.
The user-level deficiency risk classification model (Sprint 3 FR-004) will classify
USER PROFILES using longitudinal dietary intake and symptom indicators.
"""

import os
import sys
import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import RANDOM_STATE, CLEANED_DATA_PATH
from ml.features import load_cleaned_food_data, create_protein_tertile_target, prepare_features
from ml.feature_selection import run_feature_selection


def run_experiment():
    print("=" * 75)
    print("NutriScan ML Experiment: Food Protein Level Classification")
    print("=" * 75)

    df = load_cleaned_food_data(CLEANED_DATA_PATH)
    df['protein_level'] = create_protein_tertile_target(df, 'protcnt')
    y = df['protein_level']

    # Run feature selection or load top 15 features
    _, top_features = run_feature_selection()
    print(f"\nTraining on top {len(top_features)} features: {top_features}")

    X_scaled, _ = prepare_features(df, top_features, scaler_type='standard')

    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'SVC (Linear)': SVC(kernel='linear', random_state=RANDOM_STATE),
        'Random Forest': RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE),
        'Gradient Boosting': GradientBoostingClassifier(random_state=RANDOM_STATE)
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    results = []

    print("\n5-Fold Stratified Cross-Validation Results:")
    print(f"{'Model':<24} | {'Mean CV Accuracy':<18} | {'Std Dev':<10}")
    print("-" * 58)

    for name, model in models.items():
        scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='accuracy')
        mean_acc = scores.mean()
        std_acc = scores.std()
        results.append({'model': name, 'mean_accuracy': mean_acc, 'std': std_acc})
        print(f"{name:<24} | {mean_acc * 100:6.2f}%            | ±{std_acc * 100:4.2f}%")

    # Train best model (Random Forest) and print report
    best_rf = models['Random Forest']
    best_rf.fit(X_scaled, y)
    y_pred = best_rf.predict(X_scaled)
    print("\nRandom Forest In-Sample Classification Report:")
    print(classification_report(y, y_pred))

    print("=" * 75)
    return results


if __name__ == '__main__':
    run_experiment()
