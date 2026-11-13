# CDC NHANES 2021-2023 Survey Cycle Variable Mapping

This document provides the variable and column mapping for integrating the **National Health and Nutrition Examination Survey (NHANES)** dataset cycles into the NutriScan ML validation pipeline.

- **Survey Respondent Key**: `SEQN` (Respondent Sequence Number), used as the primary key across all dietary, demographic, examination, and laboratory files.

---

## 1. Demographic & Anthropometric Files

### File: `DEMO` (Demographics File)
| NHANES Variable | NutriScan Feature Key | Description | Unit / Encoding |
|---|---|---|---|
| `SEQN` | `seqn` | Respondent sequence number | Unique Identifier |
| `RIAGENDR` | `gender` | Gender | `1 = Male`, `2 = Female` |
| `RIDAGEYR` | `age` | Age at screening | Years (1-80+, 80 topcoded) |
| `RIDRETH1` | `ethnicity` | Race/Hispanic origin | Categorical (1-5) |

### File: `BMX` (Body Measures Examination)
| NHANES Variable | NutriScan Feature Key | Description | Unit |
|---|---|---|---|
| `BMXWT` | `weight_kg` | Measured weight | Kilograms (kg) |
| `BMXHT` | `height_cm` | Measured standing height | Centimeters (cm) |
| `BMXBMI` | `bmi` | Body Mass Index | $\text{kg/m}^2$ |

---

## 2. Dietary Recall Nutrient Intake Files

### File: `DR1TOT` (Dietary Interview - Total Nutrient Intakes, First Day)
| NHANES Variable | NutriScan Friendly Key | Description | Unit in NHANES | Unit in NutriScan | Conversion Factor |
|---|---|---|---|---|---|
| `DR1TKCAL` | `energy_kcal` | Energy | kcal | kcal | 1.0 |
| `DR1TPROT` | `protein_g` | Total Protein | gm | g | 1.0 |
| `DR1TTFAT` | `fat_g` | Total Fat | gm | g | 1.0 |
| `DR1TCARB` | `carbs_g` | Carbohydrate | gm | g | 1.0 |
| `DR1TFIBE` | `fibre_g` | Dietary fiber | gm | g | 1.0 |
| `DR1TFE` | `iron_mg` | Iron | mg | mg | 1.0 |
| `DR1TCALC` | `calcium_mg` | Calcium | mg | mg | 1.0 |
| `DR1TZINC` | `zinc_mg` | Zinc | mg | mg | 1.0 |
| `DR1TMAGN` | `magnesium_mg` | Magnesium | mg | mg | 1.0 |
| `DR1TVC` | `vitamin_c_mg` | Vitamin C | mg | mg | 1.0 |
| `DR1TFDN` | `folate_ug` | Total Folate | mcg | µg | 1.0 |
| `DR1TVARA` | `vitamin_a_ug` | Vitamin A (RAE) | mcg RAE | µg | 1.0 |
| `DR1TVB1` | `thiamine_mg` | Thiamin (Vitamin B1) | mg | mg | 1.0 |
| `DR1TVB2` | `riboflavin_mg` | Riboflavin (Vitamin B2) | mg | mg | 1.0 |
| `DR1TNIAC` | `niacin_mg` | Niacin | mg | mg | 1.0 |
| `DR1TVB6` | `vitamin_b6_mg` | Vitamin B6 | mg | mg | 1.0 |
| `DR1TVD` | `vitamin_d_ug` | Vitamin D (D2 + D3) | mcg | µg | 1.0 |
| `DR1TSODI` | `sodium_mg` | Sodium | mg | mg | 1.0 |
| `DR1TPOTA` | `potassium_mg` | Potassium | mg | mg | 1.0 |

---

## 3. Laboratory Biomarker Files (Ground Truth Clinical Risk Labels)

### File: `FERTIN` / `P_FERTIN` (Ferritin Lab File)
| NHANES Variable | Target Nutrient | Clinical Meaning | Clinical Cutoffs |
|---|---|---|---|
| `LBDFER` / `LBXFER` | `iron_mg` | Serum Ferritin ($\mu\text{g/L}$) | `< 15.0`: High Risk (Deficiency)<br>`15.0 - 30.0`: Moderate Risk (Depleted)<br>`>= 30.0`: Low Risk (Adequate) |

### File: `VID_L` / `P_VID_L` (Vitamin D Lab File)
| NHANES Variable | Target Nutrient | Clinical Meaning | Clinical Cutoffs |
|---|---|---|---|
| `LBXVD2MS` + `LBXVD3MS` or `LBXVIDMS` | `vitamin_d_ug` | 25-hydroxyvitamin D ($\text{nmol/L}$) | `< 30.0`: High Risk (Deficiency)<br>`30.0 - 50.0`: Moderate Risk (Inadequate)<br>`>= 50.0`: Low Risk (Sufficient) |

### File: `FOLFMS` / `P_FOLFMS` (Folate Lab File)
| NHANES Variable | Target Nutrient | Clinical Meaning | Clinical Cutoffs |
|---|---|---|---|
| `LBDFOT` / `LBXFOT` | `folate_ug` | Serum Total Folate ($\text{nmol/L}$) | `< 10.0`: High Risk<br>`10.0 - 15.0`: Moderate Risk<br>`>= 15.0`: Low Risk |

---

## 4. Key Limitations & Methodological Constraints
1. **Geographic & Food Matrix Bias**: NHANES reflects dietary recall patterns of the US civilian non-institutionalized population. Food names cannot be directly matched to Indian culinary preparations; therefore, **only normalized nutrient intake totals (grams/mg/µg) and anthropometric covariates (Age, Sex, BMI) are utilized as model features**.
2. **Absence of Subjective Questionnaires**: NHANES does not feature subjective symptoms identical to NutriScan's 12-question screening questionnaire. Consequently, two distinct model variants are trained:
   - **Variant A (Diet + Demographics Only)**: Trained and validated on NHANES objective dietary + laboratory biomarker data.
   - **Variant B (Diet + Demographics + Symptoms)**: Prototype model incorporating self-reported clinical indicators.
