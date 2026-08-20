"""
Model training and evaluation for KNMI multi-step weather forecasting.

Strategy:
- One model per (target variable, horizon step) pair, e.g. temp_mean +3 days.
- Each model is shared across all stations, with 'station' as an input feature.
- Chronological train/test split (never random split for time series data).

Feature consistency: the exact feature column list and a median imputer are
fit once at training time and saved alongside the models. Prediction reuses
this saved pipeline rather than recomputing feature columns from whatever
data happens to be available at inference time — different fetches (years
of training data vs. a short inference snapshot) can have different columns
fully populated, so recomputing independently causes mismatches.
"""

from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error

from knmi_weather_forecast.config import (
    FEATURE_PIPELINE_PATH,
    FORECAST_HORIZON,
    MODELS_DIR,
    RANDOM_FOREST_PARAMS,
    TARGET_VARS,
    TEST_FRACTION,
)

NON_FEATURE_PREFIXES = ("target_",)
NON_FEATURE_COLUMNS = {"date", "date_int"}


def get_feature_columns(df: pd.DataFrame) -> list[str]:
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
    df: pd.DataFrame, test_fraction: float = TEST_FRACTION
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff_date = df["date"].quantile(1 - test_fraction, interpolation="nearest")
    train = df[df["date"] <= cutoff_date]
    test = df[df["date"] > cutoff_date]
    return train, test


def prepare_xy(
    df: pd.DataFrame, target_col: str, feature_cols: list[str]
) -> tuple[pd.DataFrame, pd.Series]:
    subset = df[feature_cols + [target_col]].dropna()
    X = subset[feature_cols]
    y = subset[target_col]
    return X, y


def train_single_model(
    df: pd.DataFrame,
    target_col: str,
    feature_cols: list[str],
    test_fraction: float = TEST_FRACTION,
) -> tuple[RandomForestRegressor, dict]:
    train_df, test_df = time_based_split(df, test_fraction)

    X_train, y_train = prepare_xy(train_df, target_col, feature_cols)
    X_test, y_test = prepare_xy(test_df, target_col, feature_cols)

    model = RandomForestRegressor(**RANDOM_FOREST_PARAMS)
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
    if target_vars is None:
        target_vars = TARGET_VARS

    feature_cols = get_feature_columns(df)
    results = {}

    if save:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        imputer = SimpleImputer(strategy="median")
        imputer.fit(df[feature_cols])
        joblib.dump(
            {"feature_columns": feature_cols, "imputer": imputer},
            FEATURE_PIPELINE_PATH,
        )
        print(f"Saved feature pipeline ({len(feature_cols)} columns) to {FEATURE_PIPELINE_PATH}")

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
    model_path = MODELS_DIR / f"{var}_+{step}.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No trained model found at {model_path}")
    return joblib.load(model_path)


def load_feature_pipeline() -> tuple[list[str], SimpleImputer]:
    if not FEATURE_PIPELINE_PATH.exists():
        raise FileNotFoundError(
            f"No feature pipeline found at {FEATURE_PIPELINE_PATH}. "
            "Run models.py to train (and save) models first."
        )
    pipeline = joblib.load(FEATURE_PIPELINE_PATH)
    return pipeline["feature_columns"], pipeline["imputer"]


def prepare_inference_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Align an arbitrary DataFrame's features to exactly match what the
    models were trained on: same columns, same order, missing columns
    filled via the training-time imputer instead of erroring.
    """
    feature_cols, imputer = load_feature_pipeline()
    aligned = df.reindex(columns=feature_cols)
    imputed_values = imputer.transform(aligned)
    return pd.DataFrame(imputed_values, columns=feature_cols, index=df.index)


if __name__ == "__main__":
    from knmi_weather_forecast.config import TRAIN_START_DATE
    from knmi_weather_forecast.data import load_or_fetch_daily_data
    from knmi_weather_forecast.features import build_feature_set

    raw = load_or_fetch_daily_data(start=TRAIN_START_DATE)
    features = build_feature_set(raw)

    results = train_all_models(features)