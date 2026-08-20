"""
FastAPI application exposing the KNMI weather forecast models.

Run locally with:
    uv run uvicorn knmi_weather_forecast.api.main:app --reload

Requires the 'api' optional dependency group:
    uv sync --extra api
"""

from __future__ import annotations

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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


def _dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a DataFrame to JSON-safe records (NaN -> None)."""
    clean = df.astype(object).where(pd.notnull(df), None)
    return clean.to_dict(orient="records")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/stations")
def get_stations() -> list[dict]:
    """Return station metadata (id, name, lat, lon, altitude) for all KNMI stations."""
    stations_df = fetch_station_metadata()
    return _dataframe_to_records(stations_df)


@app.get("/forecast")
def get_forecast() -> list[dict]:
    """
    Return the current 7-day forecast (temperature, precipitation, wind)
    for every KNMI station with sufficient historical data reliability.

    Note: this recomputes the forecast on every request (fetches recent
    KNMI data + runs all models fresh). Fine for development; once this
    is under real traffic, add caching (e.g. compute once per hour) so
    repeated requests don't each trigger a fresh KNMI fetch.
    """
    forecast_df = predict_forecast()
    return _dataframe_to_records(forecast_df)


@app.get("/forecast/{station_id}")
def get_station_forecast(station_id: int) -> dict:
    """Return the 7-day forecast for a single station by its KNMI station ID."""
    forecast_df = predict_forecast()
    station_row = forecast_df[forecast_df["station"] == station_id]
    if station_row.empty:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    return _dataframe_to_records(station_row)[0]