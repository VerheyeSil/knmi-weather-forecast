"""
Centralized configuration for the KNMI weather forecasting project.

Every tunable constant, file path, and shared literal used across
data.py, features.py, models.py, diagnostics.py, and predict.py lives
here, so there's a single place to change a setting rather than hunting
through multiple files for hardcoded values.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

MODELS_DIR = PROJECT_ROOT / "models"
FEATURE_PIPELINE_PATH = MODELS_DIR / "feature_pipeline.joblib"

DAILY_CACHE_PATH = PROCESSED_DATA_DIR / "knmi_daily_cache.parquet"
STATION_COVERAGE_PATH = PROCESSED_DATA_DIR / "station_coverage.csv"

# ---------------------------------------------------------------------------
# KNMI API
# ---------------------------------------------------------------------------
KNMI_DAILY_URL = "https://www.daggegevens.knmi.nl/klimatologie/daggegevens"

# KNMI rejects very large single requests ("too many results"); long date
# ranges are split into chunks of this many days and stitched back together.
FETCH_CHUNK_DAYS = 700

# Any date works here — it's only used to pull KNMI's station metadata
# header (name/lat/lon/altitude), which is the same regardless of date.
STATION_METADATA_PROBE_DATE = "20240101"

DEFAULT_FETCH_START = "20200101"

# ---------------------------------------------------------------------------
# Target variables (renamed feature name -> raw KNMI column code)
# ---------------------------------------------------------------------------
TARGET_VAR_RAW_CODES = {
    "temp_mean": "TG",
    "precip_sum": "RH",
    "wind_speed_mean": "FG",
}
TARGET_VARS = list(TARGET_VAR_RAW_CODES.keys())

FORECAST_HORIZON = 7  # days ahead

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
LAG_DAYS = (1, 2, 3, 7)
ROLLING_WINDOWS = (3, 7, 14)

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
TRAIN_START_DATE = "20100101"
TEST_FRACTION = 0.2

RANDOM_FOREST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 12,
    "min_samples_leaf": 5,
    "n_jobs": -1,
    "random_state": 42,
}

# ---------------------------------------------------------------------------
# Diagnostics / station reliability
# ---------------------------------------------------------------------------
COVERAGE_THRESHOLD = 0.90

# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------
# Rolling/lag features need history before the "current" day, so pull
# enough trailing days to fill the largest rolling window plus a margin.
PREDICT_LOOKBACK_DAYS = 30

# ---------------------------------------------------------------------------
# API caching
# ---------------------------------------------------------------------------
# KNMI publishes daily data once a day, so recomputing the forecast more
# often than this just wastes time and hits KNMI's servers for no benefit.
FORECAST_CACHE_TTL_SECONDS = 60 * 60  # 1 hour

# Station metadata (name/lat/lon) essentially never changes.
STATIONS_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours