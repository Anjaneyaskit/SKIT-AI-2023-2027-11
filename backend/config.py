"""
Backend Configuration for NutriScan
Reads application settings, database URIs, and JWT credentials from environment variables.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'nutriscan_default_secret_key_change_me')
    JWT_SECRET = os.getenv('JWT_SECRET', 'nutriscan_jwt_secret_key_change_me')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', 24)))

    MONGO_URI = os.getenv('MONGO_URI') or os.getenv('MONGODB_URI') or 'mongodb://localhost:27017/'
    DB_NAME = os.getenv('DB_NAME', 'nutriscan_db')
    USE_MOCK_DB = os.getenv('USE_MOCK_DB', 'false').lower() in ('true', '1', 'yes')
    LLM_ENABLED = os.getenv('LLM_ENABLED', 'true').lower() in ('true', '1', 'yes')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    JSON_SORT_KEYS = False
