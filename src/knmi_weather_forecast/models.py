"""
Model training and evaluation for KNMI multi-step weather forecasting.

Strategy:
- One model per (target variable, horizon step) pair, e.g. temp_mean +3 days.
- Each model is shared across all stations, with 'station' as an input feature.
- Chronological train/test split (never random split for time series data).
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from knmi_weather_forecast.features import TARGET_VARS, FORECAST_HORIZON

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"

# Columns that should never be used as input features (identifiers, raw
# date fields, or target columns for any horizon/variable — those would
# leak information about the future into the model).
NON_FEATURE_PREFIXES = ("target_",)
NON_FEATURE_COLUMNS = {"date", "date_int"}


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """
    All numeric columns except identifiers/dates and any target_* column.
    'station' is intentionally kept as a feature.
    """
    feature_cols = []
    for col in df.columns:
        if col in NON_FEATURE_COLUMNS:
            continue
        if col.startswith(NON_FEATURE_PREFIXES):
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        feature_cols.append(col)
    return feature_cols


def time_based_split(
    df: pd.DataFrame, test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split chronologically: earliest (1 - test_fraction) of dates -> train,
    the rest -> test. Never shuffle time series data randomly, since that
    leaks future information into training.
    """
    cutoff_date = df["date"].quantile(1 - test_fraction, interpolation="nearest")
    train = df[df["date"] <= cutoff_date]
    test = df[df["date"] > cutoff_date]
    return train, test


def prepare_xy(
    df: pd.DataFrame, target_col: str, feature_cols: list[str]
) -> tuple[pd.DataFrame, pd.Series]:
    """Drop rows with missing target or missing features, return X, y."""
    subset = df[feature_cols + [target_col]].dropna()
    X = subset[feature_cols]
    y = subset[target_col]
    return X, y


def train_single_model(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    test_fraction: float = 0.2,
) -> tuple[RandomForestRegressor, dict]:
    """Train and evaluate one model for one target column."""
    train_df, test_df = time_based_split(df, test_fraction)

    X_train, y_train = prepare_xy(train_df, target_col, feature_cols)
    X_test, y_test = prepare_xy(test_df, target_col, feature_cols)

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, preds),
        "rmse": np.sqrt(mean_squared_error(y_test, preds)),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    return model, metrics


def train_all_models(
    df: pd.DataFrame,
    target_vars: list[str] | None = None,
    horizon: int = FORECAST_HORIZON,
    save: bool = True,
) -> dict[tuple[str, int], dict]:
    """
    Train one model per (target_var, horizon_step) combination.
    Returns a dict of {(var, step): metrics}, and optionally saves each
    model to disk under models/{var}_+{step}.joblib
    """
    if target_vars is None:
        target_vars = TARGET_VARS

    feature_cols = get_feature_columns(df)
    results = {}

    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for var in target_vars:
        for step in range(1, horizon + 1):
            target_col = f"target_{var}_+{step}"
            if target_col not in df.columns:
                continue

            model, metrics = train_single_model(df, target_col, feature_cols)
            results[(var, step)] = metrics

            print(
                f"{var} +{step}d  |  MAE={metrics['mae']:.3f}  "
                f"RMSE={metrics['rmse']:.3f}  "
                f"(train={metrics['n_train']}, test={metrics['n_test']})"
            )

            if save:
                model_path = MODELS_DIR / f"{var}_+{step}.joblib"
                joblib.dump(model, model_path)

    return results


def load_model(var: str, step: int) -> RandomForestRegressor:
    """Load a previously trained model for a given variable and horizon step."""
    model_path = MODELS_DIR / f"{var}_+{step}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model found at {model_path}")
    return joblib.load(model_path)


if __name__ == "__main__":
    from knmi_weather_forecast.data import fetch_daily_data
    from knmi_weather_forecast.features import build_feature_set

    raw = fetch_daily_data(start="20240101")
    features = build_feature_set(raw)

    results = train_all_models(features)