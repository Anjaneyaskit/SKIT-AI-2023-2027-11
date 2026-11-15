"""
RDA Service for NutriScan
Loads ICMR-NIN 2020 RDA recommendations from data/raw/rda_icmr_nin_2020.csv,
safely handles TODO placeholder rows, and provides age/gender cohort matching.
"""

import os
import csv
from typing import Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RDA_CSV_PATH = os.path.join(PROJECT_ROOT, 'data', 'raw', 'rda_icmr_nin_2020.csv')


class RDAService:
    _instance = None
    _rda_records = []

    def __init__(self, csv_path: str = RDA_CSV_PATH):
        self.csv_path = csv_path
        self._load_records()

    def _load_records(self):
        """Loads and parses verified RDA rows from CSV, skipping TODO items safely."""
        self._rda_records = []
        if not os.path.exists(self.csv_path):
            print(f"[RDA Service] Warning: File not found at {self.csv_path}")
            return

        with open(self.csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rda_raw = row.get('rda_value', '').strip()
                # Skip any unverified / TODO rows
                if not rda_raw or 'TODO' in rda_raw:
                    continue

                try:
                    rda_val = float(rda_raw)
                except ValueError:
                    continue

                ear_raw = row.get('ear_value', '').strip()
                ear_val = None
                if ear_raw and 'TODO' not in ear_raw:
                    try:
                        ear_val = float(ear_raw)
                    except ValueError:
                        ear_val = None

                self._rda_records.append({
                    'group_label': row.get('group_label', ''),
                    'gender': row.get('gender', '').lower().strip(),
                    'age_min': int(float(row.get('age_min', 0))),
                    'age_max': int(float(row.get('age_max', 120))),
                    'special_condition': row.get('special_condition', 'none').lower().strip(),
                    'nutrient_key': row.get('nutrient_key', '').strip(),
                    'rda_value': rda_val,
                    'unit': row.get('unit', '').strip(),
                    'ear_value': ear_val
                })

    def get_rda_for_profile(self, gender: str, age: int, special_condition: str = 'none') -> Dict[str, Dict[str, Any]]:
        """
        Finds the matching RDA cohort for a given user profile.
        Returns a dict: { nutrient_key: {'rda_value': float, 'unit': str, 'ear_value': Optional[float]} }
        """
        gender_clean = gender.lower().strip()
        cond_clean = special_condition.lower().strip()
        matched = {}

        for rec in self._rda_records:
            rec_gender = rec['gender']
            # Match gender: male, female, or 'both'
            if rec_gender not in ('both', gender_clean):
                continue

            # Match age range
            if not (rec['age_min'] <= age <= rec['age_max']):
                continue

            # Match special condition
            if rec['special_condition'] != cond_clean:
                continue

            matched[rec['nutrient_key']] = {
                'rda_value': rec['rda_value'],
                'unit': rec['unit'],
                'ear_value': rec['ear_value'],
                'group_label': rec['group_label']
            }

        return matched

    def get_all_verified_nutrients(self) -> list:
        """Returns list of nutrient keys that have verified RDA values loaded."""
        return sorted(list(set(r['nutrient_key'] for r in self._rda_records)))


# Global singleton instance
_rda_service_instance: Optional[RDAService] = None

def get_rda_service() -> RDAService:
    global _rda_service_instance
    if _rda_service_instance is None:
        _rda_service_instance = RDAService()
    return _rda_service_instance
