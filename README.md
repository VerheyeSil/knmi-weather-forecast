# KNMI Weather Forecast

A personal data science project that builds 7-day weather forecasts for the Netherlands from KNMI's open historical station data — covering the full pipeline from raw data ingestion through trained ML models to a live API and web app.

Forecasts temperature (mean/min/max), precipitation, wind speed, and wind direction, for every KNMI weather station with sufficient historical reliability.

## Architecture
KNMI Daggegevens API
│
src/knmi_weather_forecast/data.py fetch + local parquet cache
│
src/knmi_weather_forecast/features.py cleaning, units, lag/rolling features
│
src/knmi_weather_forecast/models.py per-variable/per-horizon RandomForest models
│
src/knmi_weather_forecast/predict.py inference: latest data → forecast
│
src/knmi_weather_forecast/api/ FastAPI, with response caching
│
frontend/ React + Leaflet + custom SVG charts

## Data source

[KNMI Daggegevens](https://www.daggegevens.knmi.nl/klimatologie/daggegevens) — daily observations from ~50 stations across the Netherlands, going back decades. No API key required. Data is fetched, cleaned, and cached locally as parquet so repeated runs don't re-hit KNMI unnecessarily.

## Project structure
knmi-weather-forecast/
├── src/knmi_weather_forecast/
│ ├── config.py # all tunable settings — paths, thresholds, hyperparameters
│ ├── data.py # KNMI fetch, chunking (large ranges), local cache, station metadata
│ ├── features.py # cleaning, unit conversion, seasonal/lag/rolling features, targets
│ ├── models.py # training, evaluation, feature pipeline persistence
│ ├── diagnostics.py # per-station data-reliability coverage checks
│ ├── predict.py # generates the current forecast from trained models
│ └── api/
│ ├── main.py # FastAPI app: /health, /stations, /forecast, /forecast/{id}
│ └── cache.py # in-memory TTL cache for forecast/station responses
├── frontend/ # React app (see frontend/README.md)
├── data/
│ ├── raw/ # individual KNMI fetch responses (debug/audit trail)
│ └── processed/ # cached parquet dataset + station coverage table
├── models/ # trained model files + feature pipeline (gitignored)
└── notebooks/ # exploratory analysis


## Setup

### Prerequisites

- Python 3.14+ and [uv](https://docs.astral.sh/uv/)
- Node.js (LTS) — via [nvm](https://github.com/nvm-sh/nvm) if on WSL/Linux
- If on Windows: WSL2 is recommended for a smooth dev experience

### Backend

```bash
uv sync --extra api

# Check data reliability per station (also builds the local KNMI data cache)
uv run python src/knmi_weather_forecast/diagnostics.py

# Train all models (one per variable × forecast horizon step)
uv run python src/knmi_weather_forecast/models.py

# Run the API
uv run uvicorn knmi_weather_forecast.api.main:app --reload
```

The API serves at `http://127.0.0.1:8000` — interactive docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Serves at `http://localhost:5173`, expects the backend running on `http://127.0.0.1:8000` (override with a `VITE_API_URL` env var if needed).

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness check |
| `GET /stations` | Station metadata (name, lat/lon, altitude) |
| `GET /forecast` | 7-day forecast for all stations, cached ~1 hour |
| `GET /forecast/{station_id}` | Forecast for a single station |
| `POST /forecast/refresh` | Force the cache to recompute on next request |

## Known limitations

- **Publication lag**: KNMI's most recent complete day of data can be 1–3 days behind today. Since forecast steps are relative to that last complete day, the number of genuinely *future* days shown can be fewer than 7 when the lag is large. The panel is honest about this rather than mislabeling past days as forecasts (see "Showing N of 7 forecast days" note).
- **Wind direction** is currently modeled as a plain regression on raw compass degrees, which mishandles the 0°/360° wraparound (circular data). A proper fix (sin/cos decomposition) is planned but not yet implemented.
- **Marine/coastal stations** that don't reliably measure temperature or precipitation (e.g. tide gauges) are automatically excluded from those specific forecasts rather than shown with fabricated values — see `diagnostics.py`.
- **Deployment** is out of scope for now; this runs locally only.

## Roadmap

- Extend `FORECAST_HORIZON` so a full 7 future days are always available regardless of publication lag
- Proper circular-statistics handling for wind direction
- More robust model evaluation (time-series cross-validation instead of a single chronological split)
- Additional sidebar views: historical trends, extreme weather events
- Possibly expand beyond KNMI's core variables (e.g. thunderstorm data)

## Attribution

Weather data: [KNMI](https://www.knmi.nl/). Map tiles: [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, styled by [CARTO](https://carto.com/attributions).