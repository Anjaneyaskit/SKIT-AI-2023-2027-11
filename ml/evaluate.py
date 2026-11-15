"""
Model Evaluation and Diagnostic Reporting (Phase G Deliverable)
Generates:
  - Confusion matrix heatmaps for each target nutrient model
  - Model comparison bar chart across metrics (Accuracy, Macro-F1)
  - Detailed evaluation table
"""

import os
import sys
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.config import RANDOM_STATE, SYNTHETIC_DATA_PATH, TARGET_NUTRIENTS, MODELS_DIR, REPORTS_DIR, RISK_CLASSES
from ml.train_baseline import prepare_features_for_target


def evaluate_all_models():
    print("=" * 80)
    print("NutriScan Sprint 2: Comprehensive ML Evaluation & Diagnostics")
    print("=" * 80)

    if not os.path.exists(SYNTHETIC_DATA_PATH):
        raise FileNotFoundError(f"Synthetic dataset not found at {SYNTHETIC_DATA_PATH}")

    df = pd.read_csv(SYNTHETIC_DATA_PATH)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    eval_records = []

    for nutrient in TARGET_NUTRIENTS:
        model_path = os.path.join(MODELS_DIR, f"{nutrient}_baseline_model.joblib")
        if not os.path.exists(model_path):
            print(f"Warning: Model bundle for {nutrient} not found at {model_path}. Skipping.")
            continue

        bundle = joblib.load(model_path)
        model = bundle['model']
        scaler = bundle['scaler']
        feature_cols = bundle['feature_cols']
        model_name = bundle['model_name']

        X, y, _ = prepare_features_for_target(df, nutrient)
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
        )

        X_test_scaled = scaler.transform(X_test[feature_cols])
        y_pred = model.predict(X_test_scaled)

        # Compute Confusion Matrix
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

        # Plot Confusion Matrix
        plt.figure(figsize=(6, 5))
        sns.heatmap(
            cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=RISK_CLASSES,
            yticklabels=RISK_CLASSES
        )
        plt.title(f"Confusion Matrix: {nutrient.upper()}\n({model_name})")
        plt.xlabel("Predicted Risk Class")
        plt.ylabel("Ground Truth Risk Class")
        plt.tight_layout()

        cm_png_path = os.path.join(REPORTS_DIR, f"cm_{nutrient}.png")
        plt.savefig(cm_png_path, dpi=150)
        plt.close()
        print(f"Saved confusion matrix plot -> {cm_png_path}")

        report_dict = classification_report(y_test, y_pred, target_names=RISK_CLASSES, output_dict=True, zero_division=0)
        eval_records.append({
            'nutrient': nutrient,
            'model_name': model_name,
            'accuracy': round(report_dict['accuracy'], 4),
            'macro_f1': round(report_dict['macro avg']['f1-score'], 4),
            'high_risk_recall': round(report_dict['High Risk']['recall'], 4),
            'low_risk_recall': round(report_dict['Low Risk']['recall'], 4)
        })

    eval_df = pd.DataFrame(eval_records)
    print("\nModel Evaluation Summary on Hold-Out Test Sets:")
    print(eval_df.to_string(index=False))

    # Comparative Bar Chart
    plt.figure(figsize=(10, 5))
    bar_width = 0.35
    indices = np.arange(len(eval_df))

    plt.bar(indices - bar_width/2, eval_df['accuracy'] * 100, bar_width, label='Test Accuracy (%)', color='#0284c7', alpha=0.85)
    plt.bar(indices + bar_width/2, eval_df['macro_f1'] * 100, bar_width, label='Macro F1-Score (%)', color='#10b981', alpha=0.85)

    plt.xlabel('Target Nutrients')
    plt.ylabel('Score (%)')
    plt.title('Baseline ML Model Performance Across Target Nutrients (NutriScan Sprint 2)')
    plt.xticks(indices, [n.replace('_', ' ').title() for n in eval_df['nutrient']], rotation=15)
    plt.ylim(0, 110)
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    comp_plot_path = os.path.join(REPORTS_DIR, 'model_comparison_bar.png')
    plt.savefig(comp_plot_path, dpi=150)
    plt.close()
    print(f"\nSaved model comparison bar chart -> {comp_plot_path}")

    print("=" * 80)
    return eval_df


if __name__ == '__main__':
    evaluate_all_models()
