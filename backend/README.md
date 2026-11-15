# NutriScan Backend (status as of 16 Nov 2026)

Owner: Anjali Devi (23ESKCA011) - Backend Engineer / API & Database

Built with Flask, MongoDB (PyMongo) and JWT authentication.
This covers the Form 2 user stories from 01-09-2026 to 16-11-2026.
Recommendations, ML predictions and the AI meal parser come in later sprints.

## Needs from the team repo
- `data_pipeline/` and `data/` (dataset work by the team lead): used to seed foods and RDA values and to map nutrients.

## Run
```
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then edit values
python -m backend.app
```
Open http://localhost:5000/api/health to check that it is running.
With USE_MOCK_DB=true it runs without a MongoDB server (in-memory database).

## API endpoints
| Method | Endpoint | Purpose | FR |
|---|---|---|---|
| GET | /api/health | Server and database health check | - |
| POST | /api/auth/register | Create an account with a profile | FR-001 |
| POST | /api/auth/login | Log in and get a JWT token | FR-001 |
| GET | /api/auth/me | Current logged-in user | FR-001 |
| GET / PUT | /api/profile | View or update profile (age, gender, height, weight, activity, diet) | FR-001 |
| GET | /api/foods?q=rice | Search foods (IFCT 2017) | FR-002 |
| GET | /api/foods/<code> | Food details by code | FR-002 |
| POST / GET | /api/intake | Record or list daily food intake | FR-002 |
| PUT / DELETE | /api/intake/<id> | Update or delete an intake log | FR-002 |
| DELETE | /api/intake/<id>/entry/<n> | Remove one food from a log | FR-002 |
| POST | /api/nutrition/calculate | Calculate nutrients for a list of foods | FR-003 |
| GET | /api/nutrition/summary?date=YYYY-MM-DD | Daily nutrient totals compared with ICMR-NIN RDA | FR-003, FR-004 |
| GET | /api/history | Past assessment records (paginated) | FR-005 |
| GET | /api/history/daily-meals | Day-wise meal history | FR-005 |
| GET | /api/history/trend?nutrient=iron_mg | Nutrient intake trend over time | FR-005 |

Protected endpoints need the header `Authorization: Bearer <token>`.
