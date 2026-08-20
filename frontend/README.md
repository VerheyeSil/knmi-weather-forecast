# KNMI Weather Forecast — Frontend

React + Vite app for the [KNMI weather forecast project](../README.md). Displays a map of Dutch weather stations and a 7-day forecast panel (temperature, precipitation, wind) for the selected station.

## Setup

```bash
npm install
npm run dev
```

Requires the backend API running at `http://127.0.0.1:8000` (see the root README). Override the API base URL with a `VITE_API_URL` environment variable if needed.

## Structure
src/
├── App.jsx # shell: sidebar + active view
├── api.js # fetch wrapper for the backend API
├── styles.css # design tokens + all styling
├── components/
│ ├── Sidebar.jsx # collapsible left navigation
│ ├── LeafletMap.jsx # dark-themed OSM map, stations as temperature-colored dots
│ ├── StationPanel.jsx # per-station forecast: config-driven list of charts
│ └── VariableChart.jsx # reusable chart (line / bar / wind-combo), no external chart library
└── views/
└── ForecastView.jsx # current tab: map + forecast panel

## Adding a new sidebar tab

Add an entry to the `VIEWS` array in `App.jsx` (`available: true`) and create the corresponding file in `src/views/`. The sidebar and routing pick it up automatically.

## Adding a new forecast variable

Add an entry to the `VARIABLES` array in `StationPanel.jsx` — label, unit, color, chart `type` (`"line"`, `"bar"`, or `"wind-combo"`), and which API field(s) to read. No changes needed in `VariableChart.jsx` unless the new variable needs a genuinely new visualization type.

## Design

Dark "synoptic chart / instrument panel" aesthetic — grounded in meteorological chart conventions rather than a generic dashboard template. Palette and type scale are defined as CSS custom properties at the top of `styles.css`:

- **Colors**: North Sea slate (background), instrument brass (temperature/primary accent), water-teal (precipitation), signal red (warnings), muted blue-grey (secondary text)
- **Type**: Space Grotesk (headings), Inter (body), IBM Plex Mono (all numeric data — coordinates, values, cache age)

No charting library — all charts (`VariableChart.jsx`) are hand-built SVG, kept intentionally simple and reusable across variables.