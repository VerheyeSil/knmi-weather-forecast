const DAY_LABELS = ["ZO", "MA", "DI", "WO", "DO", "VR", "ZA"];
const MAX_PRECIP_MM = 15; // bar fill caps here, for visual scale

function dayLabelFor(baseDateStr, offset) {
  const base = new Date(baseDateStr);
  base.setDate(base.getDate() + offset);
  return DAY_LABELS[base.getDay()];
}

export default function StationPanel({ station }) {
  if (!station) {
    return (
      <aside className="station-panel station-panel--empty">
        <p>Selecteer een station op de kaart.</p>
      </aside>
    );
  }

  const days = Array.from({ length: 7 }, (_, i) => i + 1);
  const hasTemp = station["temp_mean_+1"] != null;
  const hasPrecip = station["precip_sum_+1"] != null;
  const hasWind = station["wind_speed_mean_+1"] != null;

  return (
    <aside className="station-panel">
      <header>
        <h2>{station.name}</h2>
        <p className="coords">
          {station.lat.toFixed(2)}°N &nbsp; {station.lon.toFixed(2)}°E &nbsp; {station.alt_m}m
        </p>
      </header>

      <div className="readout">
        {days.map((d) => (
          <div className="readout-day" key={d}>
            <span className="readout-label">{dayLabelFor(station.forecast_base_date, d)}</span>

            <span className="readout-temp">
              {hasTemp ? Math.round(station[`temp_mean_+${d}`]) + "°" : "—"}
            </span>

            <span className="readout-precip-track">
              <span
                className="readout-precip-fill"
                style={{
                  height: hasPrecip
                    ? `${Math.min(100, (station[`precip_sum_+${d}`] / MAX_PRECIP_MM) * 100)}%`
                    : "0%",
                }}
              />
            </span>

            <span className="readout-wind">
              {hasWind ? Math.round(station[`wind_speed_mean_+${d}`]) : "—"}
            </span>
          </div>
        ))}
      </div>

      <div className="readout-legend">
        <span>TEMP °C</span>
        <span>NEERSLAG</span>
        <span>WIND M/S</span>
      </div>

      {(!hasTemp || !hasPrecip || !hasWind) && (
        <p className="readout-note">
          Onvoldoende historische data voor een betrouwbare voorspelling van dit station voor
          een of meer variabelen.
        </p>
      )}
    </aside>
  );
}