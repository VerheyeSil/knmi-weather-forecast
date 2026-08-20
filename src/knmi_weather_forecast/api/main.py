"""
FastAPI application exposing the KNMI weather forecast models.

Run locally with:
    uv run uvicorn knmi_weather_forecast.api.main:app --reload

Requires the 'api' optional dependency group:
    uv sync --extra api
"""

from __future__ import annotations

import time

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from knmi_weather_forecast.api.cache import TTLCache
from knmi_weather_forecast.config import FORECAST_CACHE_TTL_SECONDS, STATIONS_CACHE_TTL_SECONDS
from knmi_weather_forecast.data import fetch_station_metadata
from knmi_weather_forecast.predict import predict_forecast

app = FastAPI(
    title="KNMI Weather Forecast API",
    description="7-day temperature, precipitation, and wind forecasts per KNMI weather station.",
    version="0.1.0",
)

# Permissive for local development. Once the web app has a real domain,
# replace "*" with that specific origin instead of leaving this open.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_forecast_cache: TTLCache[pd.DataFrame] = TTLCache(ttl_seconds=FORECAST_CACHE_TTL_SECONDS)
_stations_cache: TTLCache[pd.DataFrame] = TTLCache(ttl_seconds=STATIONS_CACHE_TTL_SECONDS)


def _dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to JSON-safe records (NaN -> None)."""
    clean = df.astype(object).where(pd.notnull(df), None)
    return clean.to_dict(orient="records")


def _cache_age_seconds(cache: TTLCache) -> float | None:
    if cache.computed_at is None:
        return None
    return round(time.monotonic() - cache.computed_at, 1)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stations")
def get_stations() -> dict:
    """Return station metadata (id, name, lat, lon, altitude) for all KNMI stations."""
    stations_df = _stations_cache.get(fetch_station_metadata)
    return {
        "cache_age_seconds": _cache_age_seconds(_stations_cache),
        "stations": _dataframe_to_records(stations_df),
    }


@app.get("/forecast")
def get_forecast() -> dict:
    """
    Return the current 7-day forecast (temperature, precipitation, wind)
    for every KNMI station with sufficient historical data reliability.

    Cached for FORECAST_CACHE_TTL_SECONDS — repeated requests within that
    window return the same cached result instead of recomputing.
    """
    forecast_df = _forecast_cache.get(predict_forecast)
    return {
        "cache_age_seconds": _cache_age_seconds(_forecast_cache),
        "forecast": _dataframe_to_records(forecast_df),
    }


@app.get("/forecast/{station_id}")
def get_station_forecast(station_id: int) -> dict:
    """Return the 7-day forecast for a single station by its KNMI station ID."""
    forecast_df = _forecast_cache.get(predict_forecast)
    station_row = forecast_df[forecast_df["station"] == station_id]
    if station_row.empty:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return {
        "cache_age_seconds": _cache_age_seconds(_forecast_cache),
        **_dataframe_to_records(station_row)[0],
    }


@app.post("/forecast/refresh")
def refresh_forecast() -> dict:
    """Force the next /forecast request to recompute rather than use the cache."""
    _forecast_cache.invalidate()
    return {"status": "cache invalidated"}