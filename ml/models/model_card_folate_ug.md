# Model Card: FOLATE_UG Deficiency Screening (NutriScan)

## 1. Model Details
- **Architecture**: XGBoost
- **Variant**: Variant A (Dietary Recall Totals + Anthropometric Covariates)
- **Input Features**: age, gender_code, bmi, intake_energy_kcal, intake_protein_g, intake_fat_g, intake_carbs_g, intake_fibre_g, intake_iron_mg, intake_calcium_mg, intake_zinc_mg, intake_magnesium_mg, intake_vitamin_c_mg, intake_vitamin_a_ug, intake_thiamine_mg, intake_riboflavin_mg, intake_niacin_mg, intake_vitamin_b6_mg, intake_vitamin_d_ug, intake_sodium_mg, intake_potassium_mg
- **Output Classes**: `0: High Risk`, `1: Moderate Risk`, `2: Low Risk (Adequate)`

## 2. Training Data & Clinical Ground Truth
- **Dataset**: NHANES 2021-2023 Survey Cycle (Demographics, Body Measures, Dietary Recall DR1TOT)
- **Biomarker Standard**: Clinical reference guidelines
- **Leakage Prevention**: The target nutrient intake itself and laboratory values are strictly omitted from the feature matrix.

## 3. Evaluation Metrics
- **Test Accuracy**: 93.75%
- **Macro-F1 Score**: 32.26%
- **Macro-Recall**: 33.33%
- **ROC-AUC (One-vs-Rest)**: 0.4949

## 4. Limitations & Safe Usage
- **Screening Tool Only**: Provides preliminary nutritional awareness, not clinical diagnostic confirmation.
- **Geographic Representation**: Built on NHANES dietary distribution signals; requires local validation against Indian clinical cohorts.
