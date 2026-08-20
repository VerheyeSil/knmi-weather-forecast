import { useState } from "react";
import VariableChart from "./VariableChart";

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

const BEAUFORT_THRESHOLDS = [0.5, 1.5, 3.3, 5.4, 7.9, 10.7, 13.8, 17.1, 20.7, 24.4, 28.4, 32.6];

function msToBeaufort(ms) {
  if (ms == null) return null;
  for (let force = 0; force < BEAUFORT_THRESHOLDS.length; force++) {
    if (ms <= BEAUFORT_THRESHOLDS[force]) return force;
  }
  return 12;
}

const WIND_UNITS = [
  { label: "Bft", transform: msToBeaufort, format: (v) => Math.round(v) },
  { label: "m/s", transform: (v) => v, format: (v) => v.toFixed(1) },
];

function getForecastDays(baseDateStr, horizon = 7) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const baseDate = new Date(baseDateStr);
  baseDate.setHours(0, 0, 0, 0);

  const lagDays = Math.round((today - baseDate) / (1000 * 60 * 60 * 24));
  const firstFutureStep = Math.max(1, lagDays + 1);

  const days = [];
  for (let step = firstFutureStep; step <= horizon; step++) {
    const date = new Date(baseDate);
    date.setDate(date.getDate() + step);
    days.push({
      step,
      weekday: WEEKDAYS[date.getDay()],
      day: String(date.getDate()),
    });
  }
  return days;
}

const VARIABLES = [
  {
    key: "temp_mean",
    rangeMinKey: "temp_min",
    rangeMaxKey: "temp_max",
    label: "Temperature",
    unit: "°C",
    color: "var(--accent-brass)",
    type: "line",
    fullWidth: true,
  },
  {
    key: "precip_sum",
    label: "Precipitation",
    unit: "mm",
    color: "var(--accent-water)",
    type: "bar",
    fullWidth: true,
  },
  {
    key: "wind_speed_mean",
    dirKey: "wind_dir_vec",
    label: "Wind",
    color: "var(--text-muted)",
    type: "wind-combo",
    isWind: true,
    fullWidth: true,
  },
];

export default function StationPanel({ station }) {
  const [windUnitIndex, setWindUnitIndex] = useState(0);

  if (!station) {
    return (
      <aside className="station-panel station-panel--empty">
        <p>Select a station on the map.</p>
      </aside>
    );
  }

  const forecastDays = getForecastDays(station.forecast_base_date);
  const labels = forecastDays.map(({ weekday, day }) => ({ weekday, day }));
  const missingDays = 7 - forecastDays.length;
  const windUnit = WIND_UNITS[windUnitIndex];

  return (
    <aside className="station-panel">
      <header>
        <h2>{station.name}</h2>
        <p className="coords">
          {station.lat.toFixed(2)}°N &nbsp; {station.lon.toFixed(2)}°E &nbsp; {station.alt_m}m
        </p>
        {missingDays > 0 && (
          <p className="station-panel-note">
            Showing {forecastDays.length} of 7 forecast days — station data is {missingDays}{" "}
            day{missingDays > 1 ? "s" : ""} behind.
          </p>
        )}
      </header>

      <div className="variable-chart-list">
        {VARIABLES.map((v) => {
          const values = forecastDays.map(({ step }) => {
            const raw = station[`${v.key}_+${step}`] ?? null;
            if (v.isWind) return raw != null ? windUnit.transform(raw) : null;
            return raw;
          });

          const minValues = v.rangeMinKey
            ? forecastDays.map(({ step }) => station[`${v.rangeMinKey}_+${step}`] ?? null)
            : undefined;
          const maxValues = v.rangeMaxKey
            ? forecastDays.map(({ step }) => station[`${v.rangeMaxKey}_+${step}`] ?? null)
            : undefined;
          const directionValues = v.dirKey
            ? forecastDays.map(({ step }) => station[`${v.dirKey}_+${step}`] ?? null)
            : undefined;

          return (
            <VariableChart
              key={v.key}
              label={v.label}
              unit={v.isWind ? undefined : v.unit}
              color={v.color}
              type={v.type}
              values={values}
              minValues={minValues}
              maxValues={maxValues}
              directionValues={directionValues}
              labels={labels}
              fullWidth={v.fullWidth}
              formatValue={v.isWind ? windUnit.format : (val) => Math.round(val)}
              unitOptions={v.isWind ? WIND_UNITS.map((u) => u.label) : undefined}
              activeUnitIndex={v.isWind ? windUnitIndex : undefined}
              onToggleUnit={
                v.isWind ? () => setWindUnitIndex((i) => (i + 1) % WIND_UNITS.length) : undefined
              }
            />
          );
        })}
      </div>
    </aside>
  );
}