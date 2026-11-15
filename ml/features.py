"""
Feature Engineering Utilities for NutriScan ML Pipeline
Provides reusable functions to load cleaned data, construct feature matrices,
build targets, and apply standard / robust scalers.
"""

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from ml.config import CLEANED_DATA_PATH, RANDOM_STATE


def load_cleaned_food_data(filepath=CLEANED_DATA_PATH):
    """Loads cleaned IFCT 2017 dataset."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cleaned dataset not found at: {filepath}")
    return pd.read_csv(filepath)


def get_base_nutrient_columns(df):
    """Extracts all base nutrient feature columns, excluding non-numeric / ID metadata."""
    exclude = {'code', 'name', 'scie', 'regn', 'region', 'enerc_kj', 'protein_level'}
    return [c for c in df.columns if c not in exclude and not c.endswith('_e')]


def create_protein_tertile_target(df, col='protcnt'):
    """
    Creates a 3-class target 'protein_level' for food-level classification:
    Tertile splits: 0: Low, 1: Moderate, 2: High
    """
    labels = ['Low', 'Moderate', 'High']
    return pd.qcut(df[col], q=3, labels=labels)


def prepare_features(df, feature_cols, scaler_type='standard'):
    """
    Prepares scaled feature matrix X using StandardScaler or RobustScaler.
    """
    X = df[feature_cols].copy()
    if scaler_type == 'robust':
        scaler = RobustScaler()
    else:
        scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)
    return X_scaled, scaler
