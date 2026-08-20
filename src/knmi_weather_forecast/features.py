"""
Feature engineering for KNMI daily weather data.

Takes the raw parsed DataFrame from data.py and produces:
- readable column names
- corrected units (KNMI stores many values in tenths)
- cyclical seasonal encoding
- lag and rolling features per station
- multi-step-ahead targets for direct forecasting
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# KNMI daily variable codes -> readable names.
# Not exhaustive of every possible column, but covers the common ones.
# See: https://www.knmi.nl/kennis-en-datacentrum/uitleg/daggegevens
RENAME_MAP = {
    "STN": "station",
    "YYYYMMDD": "date_int",
    "DDVEC": "wind_dir_vec",         # degrees
    "FHVEC": "wind_speed_vec",       # 0.1 m/s
    "FG": "wind_speed_mean",         # 0.1 m/s
    "FHX": "wind_speed_max_hourly",  # 0.1 m/s
    "FHN": "wind_speed_min_hourly",  # 0.1 m/s
    "FXX": "wind_gust_max",          # 0.1 m/s
    "TG": "temp_mean",               # 0.1 degC
    "TN": "temp_min",                # 0.1 degC
    "TX": "temp_max",                # 0.1 degC
    "T10N": "temp_min_10cm",         # 0.1 degC
    "SQ": "sunshine_duration",       # 0.1 hour
    "SP": "sunshine_pct_of_max",     # percent
    "Q": "global_radiation",         # J/cm^2
    "DR": "precip_duration",         # 0.1 hour
    "RH": "precip_sum",              # 0.1 mm (note: -1 means <0.05mm, handled below)
    "RHX": "precip_max_hourly",      # 0.1 mm (note: -1 means <0.05mm, handled below)
    "PG": "pressure_mean",           # 0.1 hPa
    "PX": "pressure_max",            # 0.1 hPa
    "PN": "pressure_min",            # 0.1 hPa
    "VVN": "visibility_min",         # code
    "VVX": "visibility_max",         # code
    "NG": "cloud_cover_mean",        # okta
    "UG": "humidity_mean",           # percent
    "UX": "humidity_max",            # percent
    "UN": "humidity_min",            # percent
    "EV24": "evapotranspiration",    # 0.1 mm
}

# "Hour of occurrence" metadata columns (e.g. hour the day's max temp happened).
# These are timing metadata, not measurements — drop them to keep the
# feature set focused on values a daily forecast model can actually use.
HOUR_OF_OCCURRENCE_COLUMNS = [
    "FHXH", "FHNH", "FXXH", "TNH", "TXH", "T10NH",
    "RHXH", "PXH", "PNH", "VVNH", "VVXH", "UXH", "UNH",
]

# Columns stored in tenths that need /10 to get real units
TENTHS_COLUMNS = [
    "wind_speed_vec", "wind_speed_mean", "wind_speed_max_hourly", "wind_speed_min_hourly",
    "wind_gust_max", "temp_mean", "temp_min", "temp_max", "temp_min_10cm",
    "sunshine_duration", "precip_duration", "precip_sum", "precip_max_hourly",
    "pressure_mean", "pressure_max", "pressure_min", "evapotranspiration",
]

# Core variables we'll build multi-step forecast targets for
TARGET_VARS = ["temp_mean", "precip_sum", "wind_speed_mean"]

FORECAST_HORIZON = 7  # days ahead


def clean_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    """Rename known columns, drop fully-empty columns, fix units."""
    df = df.copy()

    # Only rename columns we recognize; leave unknown ones as-is
    rename_cols = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
    df = df.rename(columns=rename_cols)

    # Drop hour-of-occurrence metadata columns (timing, not measurements)
    drop_cols = [c for c in HOUR_OF_OCCURRENCE_COLUMNS if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Drop columns that are NaN for every single row (truly never measured
    # across all stations in this pull) — keeps the frame from bloating
    # with columns that carry zero information.
    fully_empty = [c for c in df.columns if df[c].isna().all()]
    if fully_empty:
        df = df.drop(columns=fully_empty)

    # RH/RHX use -1 to mean "measurable but < 0.05mm" — treat as 0
    for col in ["precip_sum", "precip_max_hourly"]:
        if col in df.columns:
            df[col] = df[col].replace(-1, 0)

    # Convert tenths columns to real units
    for col in TENTHS_COLUMNS:
        if col in df.columns:
            df[col] = df[col] / 10.0

    return df


def add_seasonal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add cyclical day-of-year encoding, since weather is seasonal."""
    df = df.copy()
    day_of_year = df["date"].dt.dayofyear
    df["day_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    df["day_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    return df


def add_lag_and_rolling_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    lags: tuple[int, ...] = (1, 2, 3, 7),
    rolling_windows: tuple[int, ...] = (3, 7, 14),
) -> pd.DataFrame:
    """
    Add lag and rolling-mean features per station, for the given columns.
    Defaults to the core target variables if none are specified.
    """
    df = df.copy()
    df = df.sort_values(["station", "date"])

    if columns is None:
        columns = [c for c in TARGET_VARS if c in df.columns]

    grouped = df.groupby("station")

    for col in columns:
        if col not in df.columns:
            continue
        for lag in lags:
            df[f"{col}_lag{lag}"] = grouped[col].shift(lag)
        for window in rolling_windows:
            df[f"{col}_roll_mean{window}"] = (
                grouped[col]
                .transform(lambda s, w=window: s.shift(1).rolling(w).mean())
            )

    return df


def add_multistep_targets(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    horizon: int = FORECAST_HORIZON,
) -> pd.DataFrame:
    """
    Add target_{col}_+N columns for N in 1..horizon, per station.
    These are what a direct multi-step forecaster predicts.
    """
    df = df.copy()
    df = df.sort_values(["station", "date"])

    if columns is None:
        columns = [c for c in TARGET_VARS if c in df.columns]

    grouped = df.groupby("station")

    for col in columns:
        if col not in df.columns:
            continue
        for step in range(1, horizon + 1):
            df[f"target_{col}_+{step}"] = grouped[col].shift(-step)

    return df


def build_feature_set(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Full pipeline: clean -> seasonal features -> lags/rolling -> targets."""
    df = clean_and_rename(raw_df)
    df = add_seasonal_features(df)
    df = add_lag_and_rolling_features(df)
    df = add_multistep_targets(df)
    return df


if __name__ == "__main__":
    from knmi_weather_forecast.data import fetch_daily_data

    raw = fetch_daily_data(start="20240101")
    features = build_feature_set(raw)
    print(features.shape)
    print(features.columns.tolist())