"""
Database Access Layer for NutriScan
Provides unified MongoDB collection access with automatic fallback to mongomock
if a local/remote MongoDB instance is unavailable.
"""

import os
from typing import Optional
from pymongo import MongoClient
import mongomock
from backend.config import Config


class Database:
    _instance: Optional['Database'] = None
    _client = None
    _db = None
    _is_mock = False

    def __init__(self, uri: str = None, db_name: str = None, force_mock: bool = None):
        self.uri = uri or Config.MONGO_URI
        self.db_name = db_name or Config.DB_NAME
        self.force_mock = Config.USE_MOCK_DB if force_mock is None else force_mock
        self._connect()

    def _connect(self):
        if self.force_mock:
            print("[Database] Initializing in-memory mongomock database...")
            self._client = mongomock.MongoClient()
            self._db = self._client[self.db_name]
            self._is_mock = True
            return

        try:
            # Use 5s timeout to allow reliable cloud Atlas TLS handshake
            timeout_ms = 5000 if 'mongodb+srv' in self.uri else 2000
            client = MongoClient(self.uri, serverSelectionTimeoutMS=timeout_ms)
            client.admin.command('ping')
            self._client = client
            self._db = self._client[self.db_name]
            self._is_mock = False
            print(f"[Database] Successfully connected to MongoDB at {self.uri} (DB: {self.db_name})")
        except Exception as e:
            print(f"[Database] Could not connect to MongoDB server ({e}). Falling back to in-memory mongomock.")
            self._client = mongomock.MongoClient()
            self._db = self._client[self.db_name]
            self._is_mock = True

    @property
    def db(self):
        return self._db

    @property
    def users(self):
        return self._db['users']

    @property
    def foods(self):
        return self._db['foods']

    @property
    def rda(self):
        return self._db['rda']

    @property
    def intakes(self):
        return self._db['intakes']

    @property
    def assessments(self):
        return self._db['assessments']

    @property
    def is_mock(self):
        return self._is_mock

    def create_indexes(self):
        """Creates required collection indexes idempotently."""
        try:
            self.users.create_index('email', unique=True)
            self.foods.create_index('code', unique=True)
            self.foods.create_index([('name', 'text')])
            self.rda.create_index([('gender', 1), ('age_min', 1), ('age_max', 1)])
            self.intakes.create_index([('user_id', 1), ('date', 1)])
            self.assessments.create_index('user_id')
            print("[Database] Indexes created successfully.")
        except Exception as e:
            print(f"[Database] Index creation notice: {e}")


def get_db(force_mock: bool = None) -> Database:
    """Returns singleton Database instance."""
    if Database._instance is None:
        Database._instance = Database(force_mock=force_mock)
    return Database._instance


def reset_db_instance():
    """Resets the singleton for clean test fixtures."""
    Database._instance = None
