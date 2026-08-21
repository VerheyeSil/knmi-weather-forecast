# KNMI Weather Forecast

Personal data science project: KNMI historical weather data → trained ML
forecast models → FastAPI backend → React frontend. Full pipeline, not
just a model — data ingestion, feature engineering, training, serving,
and visualization all live here.

## Commands

**Backend** (from project root):
```bash
uv sync --extra api                                          # install deps
uv run python src/knmi_weather_forecast/diagnostics.py        # coverage check + builds data cache
uv run python src/knmi_weather_forecast/models.py              # train all models
uv run python src/knmi_weather_forecast/predict.py              # generate a forecast (CLI sanity check)
uv run uvicorn knmi_weather_forecast.api.main:app --reload      # run API (localhost:8000, /docs for interactive)
```

**Frontend** (from `frontend/`):
```bash
npm install
npm run dev            # localhost:5173, expects backend on :8000
```

Run backend + frontend in separate terminals for local dev.

## Architecture
data.py -> fetch KNMI daily data, local parquet cache (load_or_fetch_daily_data),
station metadata parsing
features.py -> clean/rename raw KNMI codes, unit conversion, seasonal + lag/rolling
features, multi-step targets
models.py -> train one RandomForest per (variable, horizon step); persists a shared
feature-column list + median imputer so training/inference always agree
diagnostics.py -> per-station coverage check (some stations don't measure all variables —
e.g. marine/tide stations lack temp/precip); writes station_coverage.csv
predict.py -> loads latest data + trained models -> forecast DataFrame
api/main.py -> FastAPI: /health, /stations, /forecast, /forecast/{id}, /forecast/refresh
api/cache.py -> TTL cache wrapping predict_forecast() so repeated requests don't refetch
config.py -> ALL tunable settings live here (paths, thresholds, hyperparameters,
date ranges). No magic strings/paths elsewhere — check here first.


Frontend: see `frontend/README.md` for its own structure/conventions.

## Conventions

- **`config.py` is the single source of truth** for settings. Adding a new tunable value
  goes there, not hardcoded inline, even in a "temporary" script.
- **Git workflow**: feature branch → PR → squash-merge → delete branch. Commit messages:
  `feat:`, `fix:`, `refactor:`, etc.
- **When editing a file with multiple sequential changes in one session, prefer
  rewriting the whole file rather than many small edits** — this codebase has hit real
  bugs from partial/interleaved edits leaving files in an inconsistent state (both in
  Python and in the frontend CSS/JSX). If a file has been touched more than 2-3 times
  in a row, just regenerate it whole.
- Trained models (`models/`) and the data cache (`data/processed/*.parquet`) are
  gitignored — never commit them, never hand-edit them.

## Known gotchas (don't rediscover these)

- **KNMI rejects very large single requests** ("too many results" error) when pulling
  ALL stations × ALL variables over many years. `fetch_daily_data_long_range` /
  `load_or_fetch_daily_data` already chunk by date range — use those, not raw
  `fetch_daily_data`, for anything beyond a short window.
- **Force numeric dtypes on every parse.** Very recent/sparse days can parse as
  `object` dtype instead of numeric; if that ever merges with the properly-typed
  cache, pandas silently upcasts the whole column to `object`, breaking every
  downstream numeric check. `_parse_daily_response` already coerces this — don't
  remove that.
- **Publication lag**: KNMI's latest complete day can be 1-3 days behind "today."
  Forecast steps (`+1`..`+N`) are relative to that lagged base date, not to today.
  The frontend (`StationPanel.jsx: getForecastDays`) already resolves this correctly —
  don't reintroduce raw step-to-weekday mapping.
- **Some stations can't forecast some variables.** Marine/coastal stations report
  wind but not temp/precip (near-0% historical coverage) — `diagnostics.py` +
  `predict.py` already filter these to `null` rather than showing garbage
  extrapolated values. This is correct behavior, not a bug, if you see "No reliable
  forecast data" for a station.
- **Wind direction is not yet circularly-modeled.** `wind_dir_vec` is trained as a
  plain regression on raw degrees, which mishandles the 0°/360° wraparound. Known,
  deferred to a future model-tuning pass (sin/cos decomposition + atan2 reconstruction).

## Frontend conventions

- Design tokens (colors, fonts) are CSS custom properties at the top of
  `frontend/src/styles.css` — reuse them, don't introduce new hex values inline.
- Adding a forecast variable: one entry in the `VARIABLES` array in
  `StationPanel.jsx`. No changes needed in `VariableChart.jsx` unless it needs a
  genuinely new chart type (currently: `line`, `bar`, `wind-combo`).
- Adding a sidebar tab: one entry in `VIEWS` in `App.jsx` + a new file in `src/views/`.
- No charting library — `VariableChart.jsx` is hand-built SVG, intentionally.

## Current known limitations (see root README.md for full list)

Wind direction circular-stats fix, extending `FORECAST_HORIZON` so 7 future days are
always available regardless of lag, and more robust model evaluation (time-series
CV) are the next planned pieces of work.