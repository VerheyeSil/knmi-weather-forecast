"""
Generate a 7-day forecast (temperature, precipitation, wind) per station,
labeled with station name and location, using the trained models.

Stations that don't reliably measure a given variable (per diagnostics.py's
coverage check) are flagged so unreliable extrapolated predictions aren't
mistaken for real forecasts.
"""

from __future__ import annotations

import pandas as pd

from knmi_weather_forecast.config import (
    COVERAGE_THRESHOLD,
    FORECAST_HORIZON,
    PREDICT_LOOKBACK_DAYS,
    STATION_COVERAGE_PATH,
    TARGET_VAR_RAW_CODES,
    TARGET_VARS,
)
from knmi_weather_forecast.data import fetch_daily_data, fetch_station_metadata
from knmi_weather_forecast.features import build_feature_set
from knmi_weather_forecast.models import load_model, prepare_inference_features


def get_latest_feature_row_per_station() -> pd.DataFrame:
    """
    Fetch recent data, build the same features used in training, and
    return only the most recent complete row per station — this is what
    gets fed into the models to produce a forecast starting "tomorrow."
    """
    start = (pd.Timestamp.today() - pd.Timedelta(days=PREDICT_LOOKBACK_DAYS)).strftime("%Y%m%d")
    raw = fetch_daily_data(start=start, save_raw=False)
    features = build_feature_set(raw)

    latest = (
        features.sort_values(["station", "date"])
        .groupby("station")
        .tail(1)
        .reset_index(drop=True)
    )
    return latest


def load_unreliable_stations() -> dict[str, set[int]]:
    """
    Load the pre-computed station coverage table (from diagnostics.py) and
    return {renamed_var: set(unreliable_station_ids)}.
    """
    if not STATION_COVERAGE_PATH.exists():
        raise FileNotFoundError(
            f"No coverage table found at {STATION_COVERAGE_PATH}. "
            "Run `uv run python src/knmi_weather_forecast/diagnostics.py` first."
        )

    coverage = pd.read_csv(STATION_COVERAGE_PATH)
    unreliable = {}
    for var, raw_code in TARGET_VAR_RAW_CODES.items():
        col = f"{raw_code}_coverage"
        if col not in coverage.columns:
            continue
        low = coverage[coverage[col] < COVERAGE_THRESHOLD]
        unreliable[var] = set(low["station"])
    return unreliable


def predict_forecast() -> pd.DataFrame:
    """
    Run all trained models (one per variable x horizon step) against the
    latest available data, and return one row per station with columns
    like temp_mean_+1 ... temp_mean_+7, precip_sum_+1 ... etc.
    Unreliable station/variable combinations are set to NaN.
    """
    latest = get_latest_feature_row_per_station()
    X = prepare_inference_features(latest)

    forecast = latest[["station", "date"]].copy()
    forecast = forecast.rename(columns={"date": "forecast_base_date"})

    unreliable = load_unreliable_stations()

    for var in TARGET_VARS:
        unreliable_for_var = unreliable.get(var, set())
        for step in range(1, FORECAST_HORIZON + 1):
            model = load_model(var, step)
            preds = model.predict(X)
            col = f"{var}_+{step}"
            forecast[col] = preds
            forecast.loc[forecast["station"].isin(unreliable_for_var), col] = pd.NA

    stations = fetch_station_metadata()
    forecast = forecast.merge(stations, on="station", how="left")

    return forecast


def _print_variable_forecast(forecast_df: pd.DataFrame, var: str, label: str) -> None:
    cols = ["name"] + [f"{var}_+{i}" for i in range(1, FORECAST_HORIZON + 1)]
    print(f"\n{label} forecast (+1 to +7 days):")
    print(forecast_df[cols].to_string(index=False))
    n_unreliable = forecast_df[f"{var}_+1"].isna().sum()
    if n_unreliable:
        print(f"({n_unreliable} station(s) omitted — insufficient historical {label.lower()} data)")


if __name__ == "__main__":
    forecast_df = predict_forecast()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)

    print(forecast_df[["station", "name", "lat", "lon", "forecast_base_date"]].to_string(index=False))

    _print_variable_forecast(forecast_df, "temp_mean", "Temperature")
    _print_variable_forecast(forecast_df, "precip_sum", "Precipitation")
    _print_variable_forecast(forecast_df, "wind_speed_mean", "Wind speed")