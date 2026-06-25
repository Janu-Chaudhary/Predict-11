"""Central paths and config. No magic strings scattered across modules."""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = three levels up from this file (src/predict11/config.py -> repo).
ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = Path(os.environ.get("P11_DATA_RAW", ROOT / "data" / "raw"))
DATA_CURATED = Path(os.environ.get("P11_DATA_CURATED", ROOT / "data" / "curated"))
MODELS_DIR = Path(os.environ.get("P11_MODELS", ROOT / "models"))

CRICSHEET_DIR = DATA_RAW / "cricsheet_ipl"
SQUADS_DIR = DATA_RAW / "Teams"
DUCKDB_PATH = DATA_CURATED / "predict11.duckdb"
MODEL_PATH = MODELS_DIR / "lgbm_fp.txt"
FEATURES_PARQUET = DATA_CURATED / "player_match_features.parquet"

# Temporal split: matches strictly before this season start go to train.
TEST_FROM_DATE = os.environ.get("P11_TEST_FROM", "2023-01-01")

for _d in (DATA_CURATED, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
