# ICMR-NIN 2020 RDA & EAR Pending Values (TODO)

This document tracks nutrient recommendation values that need to be filled or verified from the official **ICMR-National Institute of Nutrition (NIN) 2020 "Nutrient Requirements for Indians" Report**.

## 1. Status Overview

- **Adult Males (19-30, 31-50, 51-60)**: Verified for Energy, Protein, Calcium, Iron, Zinc, Magnesium, Vitamin A, Vitamin C, Thiamine, Riboflavin, Niacin, Vitamin B6, Folate, and Vitamin D.
- **Adult Females (19-30, 31-50, 51-60)**: Verified for Energy, Protein, Calcium, Iron, Zinc, Magnesium, Vitamin A, Vitamin C, Thiamine, Riboflavin, Niacin, Vitamin B6, Folate, and Vitamin D.
- **Elderly (60+)**: Caloric requirements with reduced BMR adjustment need exact reference number confirmation.
- **Children (1-3, 4-6, 7-9 years)**: Marked as `TODO_FILL_FROM_ICMR_NIN_2020_PDF`.
- **Adolescents (10-12, 13-15, 16-18 years male and female)**: Marked as `TODO_FILL_FROM_ICMR_NIN_2020_PDF`.
- **Pregnant and Lactating Women**: Additional energy and micronutrient increments marked as `TODO_FILL_FROM_ICMR_NIN_2020_PDF`.
- **EAR (Estimated Average Requirement)**: Adult EAR is partially filled; secondary age bands marked as `TODO_FILL_FROM_ICMR_NIN_2020_PDF`.

## 2. Specific Items to Fill in `data/raw/rda_icmr_nin_2020.csv`

1. **Childhood Groups (Ages 1 - 9)**:
   - Energy (kcal/day) by age band
   - Protein (g/day)
   - Calcium (mg/day)
   - Iron (mg/day)
   - Vitamin A (µg/day)
   - Folate & Zinc

2. **Adolescent Groups (Ages 10 - 18, Male & Female)**:
   - Energy requirements across activity levels
   - Protein allowances during adolescent growth spurt
   - Iron allowances (especially higher requirement for adolescent females post-menarche)

3. **Special Conditions**:
   - Pregnancy: Second and Third trimester increments (+350 kcal/day energy, +6.8g to +22g protein, iron +21mg)
   - Lactation: 0-6 months (+600 kcal/day, +16.9g protein) and 7-12 months (+520 kcal/day, +13.2g protein)

4. **Nutrients with Special Guidelines**:
   - **Sodium**: Suggested Upper Limit 2000 mg/day (ICMR-NIN safe upper limit)
   - **Potassium**: Adequate Intake / Recommendation 3500 mg/day
   - **Visible Fat & Fibre**: Minimum desirable intakes (25g fat male, 20g female; 30g fibre male, 25g female)

## 3. How the System Handles TODO Values

The `backend/services/rda_service.py` loader detects any value containing `TODO_FILL_FROM_ICMR_NIN_2020_PDF` or non-numeric tokens:
- It safely excludes unverified rows rather than guessing or fabricating numbers.
- When an API request or dashboard calculates intake for a profile where the exact RDA is pending, it returns `rda_percent: null` and an informative note: `"RDA reference pending for this specific cohort in ICMR-NIN 2020 reference table"`.
