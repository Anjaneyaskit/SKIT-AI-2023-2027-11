# NutriScan: AI-Based Nutrition Deficiency Detection & Recommendation System

SKIT Jaipur, Dept. of CSE (AI), Project 2026-27, Project ID: SKIT/AI/2023-2027/11
SDG 3: Good Health and Well-Being

**Status: work completed up to 16 Nov 2026** (as per Form 2 timeline)

## Team and folders

| Member | Role | Folder(s) | Form 2 tasks covered (1 Sep to 16 Nov) |
|---|---|---|---|
| Anjali Choudhary (23ESKCA010) | Team Lead / Dataset & Preprocessing | `data/`, `data_pipeline/` | Dataset structure, collection, cleaning, missing data, consistency, unit and category standardisation, transformation, feature preparation, processed dataset, data quality validation |
| Anjali Devi (23ESKCA011) | Backend / API & Database | `backend/` | Backend setup and config, MongoDB design and operations, API structure, nutrition APIs, input validation, error handling, services, database queries |
| Anjaneya Sharma (23ESKCA012) | ML Model Development | `ml/` | ML pipeline setup, feature preparation, baseline models (Logistic Regression, Random Forest, XGBoost), training, evaluation, model comparison and selection |
| Jaspinder Singh (23ESKCA056) | Frontend & Testing | `frontend/` | Structure, layout, navigation, input screens, form validation, result and recommendation screens, responsive UI, UI enhancement, frontend functionality |

## Tech stack
- **Frontend:** HTML templates, CSS and JavaScript
- **Backend:** Python Flask, JWT authentication
- **Database:** MongoDB (PyMongo; in-memory mongomock for development)
- **ML:** scikit-learn and XGBoost
- **Data:** IFCT 2017 (Indian Food Composition Tables), ICMR-NIN 2020 RDA

## How to run
```
python -m venv venv
venv\Scripts\activate             (Windows)
pip install -r requirements.txt
copy .env.example .env             (then edit the values)
python -m backend.app
```
Open http://localhost:5000 for the app, and http://localhost:5000/api/health to check the server.
With `USE_MOCK_DB=true`, no MongoDB server is needed. Foods and RDA values load automatically on start.

Other scripts:
- `python -m data_pipeline.validate_mapping`: checks nutrient calculations against hand-computed values
- `python -m ml.train_baseline`: trains the baseline models
- `python -m ml.evaluate`: evaluation reports and charts (saved in `ml/reports/`)

## What works now
- Register, login, and edit profile
- Search foods, and log daily meals (add, edit, delete)
- Daily nutrient totals compared with ICMR-NIN RDA values
- Intake history and nutrient trends
- Baseline deficiency-risk models trained for protein, iron, calcium, zinc, vitamin C and folate, with evaluation reports

## Planned for next sprints (after 16 Nov)
- Connecting the ML models to the backend (deficiency assessment API) and the questionnaire/results/recommendation screens
- Food recommendations, model tuning and explainability (SHAP), final model training
- RDA values for children, adolescents and pregnant/lactating women (see `data/raw/RDA_TODO.md`)
- Testing, optimisation and deployment
