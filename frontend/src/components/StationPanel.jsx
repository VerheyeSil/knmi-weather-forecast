import { useState } from "react";
import VariableChart from "./VariableChart";

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

// Standard Beaufort scale: each entry is the upper bound (m/s) for that
// force. https://en.wikipedia.org/wiki/Beaufort_scale
const BEAUFORT_THRESHOLDS = [0.5, 1.5, 3.3, 5.4, 7.9, 10.7, 13.8, 17.1, 20.7, 24.4, 28.4, 32.6];

function msToBeaufort(ms) {
  if (ms == null) return null;

  for (let force = 0; force < BEAUFORT_THRESHOLDS.length; force++) {
    if (ms <= BEAUFORT_THRESHOLDS[force]) return force;
  }

  return 12;
}

/**
 * KNMI's data has a publication lag — the most recent complete day
 * ("forecast_base_date") can be 1-2 days behind today. Model step "+1"
 * means "one day after that base date," which isn't necessarily
 * tomorrow.
 */
function getForecastDays(baseDateStr, horizon = 7) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const baseDate = new Date(baseDateStr);
  baseDate.setHours(0, 0, 0, 0);

  const lagDays = Math.round(
    (today - baseDate) / (1000 * 60 * 60 * 24)
  );

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

// Add new forecast variables here as they become available.
const VARIABLES = [
  {
    key: "temp_mean",
    label: "Temperature",
    unit: "°C",
    color: "var(--accent-brass)",
    type: "line",
  },
  {
    key: "precip_sum",
    label: "Precipitation",
    unit: "mm",
    color: "var(--accent-water)",
    type: "bar",
  },
  {
    key: "wind_speed_mean",
    label: "Wind speed",
    unit: "Bft",
    color: "var(--text-muted)",
    type: "bar",
    transform: msToBeaufort,
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
  const labels = forecastDays.map(({ weekday, day }) => ({
    weekday,
    day,
  }));

  const missingDays = 7 - forecastDays.length;

  const windUnits = ["Bft", "m/s"];

  return (
    <aside className="station-panel">
      <header>
        <h2>{station.name}</h2>

        <p className="coords">
          {station.lat.toFixed(2)}°N &nbsp;
          {station.lon.toFixed(2)}°E &nbsp;
          {station.alt_m}m
        </p>

        {missingDays > 0 && (
          <p className="station-panel-note">
            Showing {forecastDays.length} of 7 forecast days — station data is{" "}
            {missingDays} day{missingDays > 1 ? "s" : ""} behind.
          </p>
        )}
      </header>

      <div className="variable-chart-list">
        {VARIABLES.map((v) => {
          const isWind = v.key === "wind_speed_mean";

          const values = forecastDays.map(({ step }) => {
            const raw = station[`${v.key}_+${step}`] ?? null;

            // Wind can be displayed either as Beaufort or m/s.
            if (isWind && windUnitIndex === 1) {
              return raw;
            }

            return v.transform ? v.transform(raw) : raw;
          });

          return (
            <VariableChart
              key={v.key}
              label={v.label}
              unit={isWind ? windUnits[windUnitIndex] : v.unit}
              color={v.color}
              type={v.type}
              values={values}
              labels={labels}
              formatValue={(value) =>
                isWind && windUnitIndex === 1
                  ? value.toFixed(1)
                  : Math.round(value)
              }
              {...(isWind
                ? {
                    unitOptions: windUnits,
                    activeUnitIndex: windUnitIndex,
                    onToggleUnit: () =>
                      setWindUnitIndex(
                        (current) => (current + 1) % windUnits.length
                      ),
                  }
                : {})}
            />
          );
        })}
      </div>
    </aside>
  );
}