"""
Baseline Machine Learning Model Training (Phase G Deliverable)
Trains Logistic Regression, Random Forest, and XGBoost classifiers for each target nutrient:
  - protein_g
  - iron_mg
  - calcium_mg
  - zinc_mg
  - vitamin_c_mg
  - folate_ug

DATA LEAKAGE PREVENTION PROTOCOL:
For each target nutrient:
  1. The target nutrient's own intake and its exact RDA % column are strictly REMOVED from the feature set.
  2. Features provided: User age, gender (binary), BMI, activity level (ordinal), symptom severity scores,
     and the cross-intake pattern of other nutrients.
  3. Stratified 80/20 train/test split with 5-fold cross-validation.
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import RANDOM_STATE, SYNTHETIC_DATA_PATH, TARGET_NUTRIENTS, MODELS_DIR, REPORTS_DIR
from ml.make_training_data import generate_synthetic_dataset


def prepare_features_for_target(df, target_nutrient):
    """
    Constructs non-leaking feature matrix X and target vector y.
    """
    df = df.copy()

    # Encode categoricals
    df['gender_code'] = (df['gender'] == 'male').astype(int)
    activity_map = {'sedentary': 0, 'light': 1, 'moderate': 2, 'active': 3}
    df['activity_code'] = df['activity_level'].map(activity_map).fillna(0)

    # Symptom scores
    symptom_cols = [
        'symptom_fatigue',
        'symptom_pale_skin',
        'symptom_muscle_cramps',
        'symptom_hair_fall',
        'symptom_slow_healing'
    ]

    # Other nutrient intakes (excluding target_nutrient and its RDA %)
    other_nutrient_intakes = [
        c for c in df.columns
        if c.startswith('intake_') and c != f"intake_{target_nutrient}"
    ]

    feature_cols = ['age', 'gender_code', 'bmi', 'activity_code'] + symptom_cols + other_nutrient_intakes
    X = df[feature_cols].copy()
    y = df[f"target_{target_nutrient}_code"].values

    return X, y, feature_cols


def train_baseline_models():
    print("=" * 80)
    print("NutriScan Sprint 2: Baseline Model Training across Target Nutrients")
    print("=" * 80)

    if not os.path.exists(SYNTHETIC_DATA_PATH):
        print("Synthetic dataset not found. Generating now...")
        df = generate_synthetic_dataset()
    else:
        df = pd.read_csv(SYNTHETIC_DATA_PATH)

    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    summary_results = {}

    for nutrient in TARGET_NUTRIENTS:
        print(f"\n>>> Training Baselines for: {nutrient.upper()}")
        X, y, feature_cols = prepare_features_for_target(df, nutrient)

        # 80/20 Stratified train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        models = {
            'Logistic Regression': LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            'Random Forest': RandomForestClassifier(n_estimators=150, max_depth=12, random_state=RANDOM_STATE),
            'XGBoost': XGBClassifier(
                n_estimators=150,
                max_depth=5,
                learning_rate=0.1,
                random_state=RANDOM_STATE,
                eval_metric='mlogloss'
            )
        }

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
        nutrient_model_metrics = {}
        best_model_name = None
        best_f1 = -1.0
        best_model_obj = None

        print(f"    {'Model':<22} | {'5-Fold CV Acc':<14} | {'Test Acc':<10} | {'Macro F1':<10}")
        print("    " + "-" * 62)

        for name, clf in models.items():
            # 5-fold CV on train set
            cv_scores = cross_val_score(clf, X_train_scaled, y_train, cv=cv, scoring='accuracy')
            mean_cv = cv_scores.mean()

            # Train on full train set and evaluate on test set
            clf.fit(X_train_scaled, y_train)
            y_pred = clf.predict(X_test_scaled)

            acc = accuracy_score(y_test, y_pred)
            prec = precision_score(y_test, y_pred, average='macro', zero_division=0)
            rec = recall_score(y_test, y_pred, average='macro', zero_division=0)
            f1 = f1_score(y_test, y_pred, average='macro', zero_division=0)

            nutrient_model_metrics[name] = {
                'cv_accuracy': round(mean_cv, 4),
                'test_accuracy': round(acc, 4),
                'macro_precision': round(prec, 4),
                'macro_recall': round(rec, 4),
                'macro_f1': round(f1, 4)
            }

            print(f"    {name:<22} | {mean_cv * 100:6.2f}%       | {acc * 100:6.2f}%   | {f1 * 100:6.2f}%")

            if f1 > best_f1:
                best_f1 = f1
                best_model_name = name
                best_model_obj = clf

        # Save best model bundle (model + scaler + feature_cols list)
        model_save_path = os.path.join(MODELS_DIR, f"{nutrient}_baseline_model.joblib")
        bundle = {
            'nutrient': nutrient,
            'model_name': best_model_name,
            'model': best_model_obj,
            'scaler': scaler,
            'feature_cols': feature_cols,
            'metrics': nutrient_model_metrics[best_model_name]
        }
        joblib.dump(bundle, model_save_path)
        print(f"    -> Saved best model ({best_model_name}) to: {model_save_path}")

        summary_results[nutrient] = {
            'best_model': best_model_name,
            'models': nutrient_model_metrics
        }

    # Save summary report JSON
    report_json_path = os.path.join(REPORTS_DIR, 'baseline_metrics.json')
    with open(report_json_path, 'w', encoding='utf-8') as f:
        json.dump(summary_results, f, indent=2)
    print(f"\nBaseline metrics summary saved to {report_json_path}")

    # Generate summary CSV
    rows = []
    for nut, data in summary_results.items():
        for m_name, m_metrics in data['models'].items():
            r = {'nutrient': nut, 'model': m_name, 'is_best': (m_name == data['best_model'])}
            r.update(m_metrics)
            rows.append(r)

    csv_path = os.path.join(REPORTS_DIR, 'baseline_metrics.csv')
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    print(f"Baseline metrics table saved to {csv_path}")

    print("=" * 80)
    return summary_results


if __name__ == '__main__':
    train_baseline_models()
