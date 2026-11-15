# Indian Food Composition Tables (IFCT 2017) - Dataset Documentation

## 1. Overview and Source Attribution
The primary food composition dataset utilized in **NutriScan** is based on the **Indian Food Composition Tables (IFCT 2017)** published by the **National Institute of Nutrition (ICMR - NIN)**, Hyderabad, India.

- **Official ICMR-NIN Portal**: [https://www.nin.res.in/](https://www.nin.res.in/)
- **IFCT Documentation & Open Data**: [https://ifct2017.github.io/](https://ifct2017.github.io/)
- **Repository**: [https://github.com/ifct2017/compositions](https://github.com/ifct2017/compositions)
- **Kaggle Distribution**: [https://www.kaggle.com/datasets/gijoe707/ifct2017](https://www.kaggle.com/datasets/gijoe707/ifct2017)

## 2. Dataset Architecture
- **Total Food Items**: 542 foods categorized across Indian food groups (cereals, pulses, vegetables, fruits, dairy, meats, spices, etc.).
- **Raw Columns**: 356 columns consisting of:
  - Identification & Metadata: `code` (alphanumeric unique ID), `name` (common English name), `scie` (scientific binomial name), `regn` (region code).
  - Base Nutrients: 176 nutrient columns.
  - Measurement Error Columns: 176 corresponding `_e` columns containing analytical standard error / measurement uncertainty.
- **Basis of Values**: All nutrient values represent quantity per **100 g edible portion**.
- **Encoding**: UTF-8 with Byte Order Mark (`utf-8-sig`).

## 3. Preprocessing and Data Cleaning Protocol
1. **Dropping Measurement Error (`_e`) Columns**:
   The 176 `_e` columns denote analytical measurement errors and do not represent distinct nutritional content consumed. All `*_e` columns are discarded during pipeline loading.
2. **Region Code Mapping**:
   `regn` integer codes are mapped to human-readable geographic administrative sampling regions:
   - `1`: North
   - `2`: East
   - `3`: South
   - `4`: West
   - `5`: Central
   - `6`: Pooled / Multi-region
   - `10`: Other
3. **Missing Value Imputation**:
   - `scie` (scientific name) contains missing entries in 117 rows; missing names are labeled `"Unknown"`.
   - Numeric nutrient columns: Only `biot` (biotin) had 8 missing values in the raw dataset. These are imputed with the column median. All other 175 numeric columns are complete.
4. **Energy Conversion**:
   Raw energy `enerc` is reported in kilojoules (**kJ**). It is converted to kilocalories (**kcal**) via the standard factor:
   $$\text{energy\_kcal} = \frac{\text{enerc}}{4.184}$$
   The original kilojoule value is retained as `enerc_kj`.
5. **Deduplication & Negative Checks**:
   - Zero duplicated food codes exist.
   - Zero negative nutrient values detected after loading.
6. **Near-Zero-Variance Columns**:
   Identified 14 near-zero-variance columns (e.g., specific trace minerals like `hg`, `cd`, `li`, `as`, `pb`, or rare fatty acid isomers) with variance < 0.01. **These are preserved in the cleaned full dataset** for comprehensive reference but flagged for exclusion during ML feature engineering.

## 4. Nutrient Groups, Units, and Metadata

### A. Macronutrients & Energy (per 100 g)
| Column Code | Friendly Key | Nutrient Description | Unit | Derivation / Notes |
|---|---|---|---|---|
| `enerc` | `enerc_kj` | Energy (Kilojoules) | kJ | Raw IFCT column |
| - | `energy_kcal` | Energy (Kilocalories) | kcal | Derived: `enerc / 4.184` |
| `protcnt` | `protein_g` | Total Protein | g | Kjeldahl total nitrogen conversion |
| `fatce` | `fatg` / `fat_g` | Total Crude Fat | g | Ether extract |
| `choavldf` | `carbs_g` | Available Carbohydrate | g | By difference (100 - water - protein - fat - ash - fibre) |
| `fibtg` | `fibre_g` | Total Dietary Fibre | g | Enzymatic-gravimetric method |
| `fibins` | `fibins_g` | Insoluble Dietary Fibre | g | TO VERIFY |
| `fibsol` | `fibsol_g` | Soluble Dietary Fibre | g | TO VERIFY |
| `water` | `water_g` | Moisture / Water Content | g | Gravimetric drying |
| `ash` | `ash_g` | Total Mineral Ash | g | Muffle furnace combustion |

### B. Minerals & Trace Elements (per 100 g)
| Column Code | Friendly Key | Nutrient Description | Unit | Notes |
|---|---|---|---|---|
| `fe` | `iron_mg` | Iron | mg | AAS / ICP-MS |
| `ca` | `calcium_mg` | Calcium | mg | AAS / ICP-MS |
| `zn` | `zinc_mg` | Zinc | mg | AAS / ICP-MS |
| `mg` | `magnesium_mg` | Magnesium | mg | AAS / ICP-MS |
| `na` | `sodium_mg` | Sodium | mg | Flame photometry / AAS |
| `k` | `potassium_mg` | Potassium | mg | Flame photometry / AAS |
| `p` | `phosphorus_mg` | Phosphorus | mg | Colorimetric |
| `cu` | `copper_mg` | Copper | mg | AAS / ICP-MS |
| `mn` | `manganese_mg` | Manganese | mg | AAS / ICP-MS |
| `se` | `selenium_ug` | Selenium | µg | ICP-MS (trace) |
| `cr`, `mo`, `ni` | - | Chromium, Molybdenum, Nickel | µg | Trace minerals |
| `al`, `as`, `cd`, `pb`, `hg`, `li` | - | Heavy Metals & Trace Minerals | µg / mg | Toxicological / trace monitoring |

### C. Vitamins (per 100 g)
| Column Code | Friendly Key | Nutrient Description | Unit | Notes |
|---|---|---|---|---|
| `vitc` | `vitamin_c_mg` | Vitamin C (Ascorbic Acid) | mg | HPLC |
| `retol` | `vitamin_a_ug` | Preformed Vitamin A (Retinol) | µg | HPLC. Plant carotenoids cataloged separately. |
| `folsum` | `folate_ug` | Total Folate | µg | Microbiological assay / sum |
| `thia` | `thiamine_mg` | Thiamine (Vitamin B1) | mg | Fluorometric / HPLC |
| `ribf` | `riboflavin_mg` | Riboflavin (Vitamin B2) | mg | Fluorometric / HPLC |
| `nia` | `niacin_mg` | Niacin (Vitamin B3) | mg | Microbiological assay / HPLC |
| `pantac` | `pantothenic_acid_mg` | Pantothenic Acid (Vitamin B5) | mg | Microbiological assay |
| `vitb6c` | `vitamin_b6_mg` | Total Vitamin B6 | mg | Microbiological assay |
| `biot` | `biotin_ug` | Biotin (Vitamin B7) | µg | Microbiological assay (8 cells median imputed) |
| `ergcal` | - | Ergocalciferol (Vitamin D2) | µg | HPLC |
| `chocal` | - | Cholecalciferol (Vitamin D3) | µg | HPLC |
| - | `vitamin_d_ug` | Vitamin D (D2 + D3 Approximation) | µg | Derived: `ergcal + chocal` |
| `vite` | `vitamin_e_mg` | Total Vitamin E | mg | HPLC sum of tocopherols |
| `vitk1`, `vitk2`| - | Phylloquinone / Menaquinone | µg | HPLC |

### D. Carotenoids, Sugars, Amino Acids, Fatty Acids & Bioactives
- **Carotenoids**: `lutn`, `zea`, `lycpn`, `crypxb`, `cartg`, `carta`, `cartb` ($\beta$-carotene), `cartoid` ($\mu$g).
- **Sugars**: `cho` (total carbohydrate), `starch`, `frus` (fructose), `glus` (glucose), `sucs` (sucrose), `mals` (maltose), `lactose`, `fsugar` (free sugar) (g).
- **Amino Acids**: 18 individual amino acids (`ala`, `arg`, `asp`, `glu`, `gly`, `pro`, `ser`, `tyr`, `his`, `ile`, `leu`, `lys`, `met`, `cys`, `phe`, `thr`, `trp`, `val`) (g).
- **Fatty Acids**: Comprehensive saturated, monounsaturated, polyunsaturated fatty acid profiles (`f14d0` to `f24d0`, etc.) (g).
- **Organic Acids & Anti-nutrients**: `phytac` (phytic acid), `oxalt` (total oxalic acid), `oxals` (soluble oxalate), `sapon` (saponins), `citac` (citric acid), etc. (mg/g).

## 5. Critical Dataset Gaps & Limitations
1. **Vitamin B12 Absence**:
   **The IFCT 2017 tables do NOT report Vitamin B12 values.** NutriScan explicitly documents this limitation. Vitamin B12 is neither fabricated nor hallucinated.
2. **Vitamin D Approximation**:
   Vitamin D in IFCT 2017 is captured via two distinct columns: `ergcal` (Vitamin D2) and `chocal` (Vitamin D3). Total active Vitamin D ($\mu$g) is approximated by summing `ergcal + chocal`.
3. **Plant-Origin Vitamin A vs Retinol**:
   Preformed Vitamin A (`retol`) is primarily present in animal-derived foods. For plant foods, provitamin A activity originates from carotenoids (primarily $\beta$-carotene `cartb`). In the current baseline, `retol` represents preformed retinol; provitamin A bio-conversion can be evaluated in future iterations using ICMR conversion factors ($1\,\mu\text{g Retinol Equivalent} = 8\,\mu\text{g } \beta\text{-carotene}$).
