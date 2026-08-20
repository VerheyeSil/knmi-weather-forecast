const CHART_WIDTH = 320;
const CHART_HEIGHT = 130;
const PAD_X = 24;
const PAD_TOP = 26;
const PAD_BOTTOM = 26;

/**
 * A small self-contained chart for one forecast variable. Receives fully
 * resolved values + labels rather than computing dates itself, so it has
 * no opinion about "today" or data lag — just renders whatever real
 * future days it's given.
 *
 * type="line" for continuous quantities (temperature), type="bar" for
 * daily totals (precipitation, wind).
 *
 * Optional unit toggle: pass `unitOptions` (array of unit label strings),
 * `activeUnitIndex`, and `onToggleUnit` to render the unit as a clickable
 * button that cycles through them (used for wind's m/s <-> Bft toggle).
 * Omit these and the unit renders as static text, as before.
 */
export default function VariableChart({
  label,
  unit,
  color,
  type = "line",
  values, // array of numbers or null, one per forecast day
  labels, // array of { weekday, day } matching values, same length
  formatValue = (v) => Math.round(v),
  unitOptions,
  activeUnitIndex,
  onToggleUnit,
}) {
  const hasData = values.some((v) => v != null);
  const plotWidth = CHART_WIDTH - PAD_X * 2;
  const plotHeight = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;
  const stepX = plotWidth / (values.length - 1 || 1);

  const unitControl =
    unitOptions && unitOptions.length > 1 ? (
        <button
        type="button"
        className={`variable-chart-unit-toggle ${
            activeUnitIndex === 1 ? "is-secondary" : ""
        }`}
        onClick={onToggleUnit}
        aria-label={`Switch unit (currently ${unitOptions[activeUnitIndex]})`}
        >
        <span className="unit-toggle-option">Bft</span>
        <span className="unit-toggle-option">m/s</span>
        </button>
    ) : (
        <span className="variable-chart-unit">{unit}</span>
    );

  if (!hasData) {
    return (
      <div className="variable-chart variable-chart--empty">
        <div className="variable-chart-label">
          {label} {unitControl}
        </div>
        <p>No reliable forecast data for this station.</p>
      </div>
    );
  }

  const numericValues = values.filter((v) => v != null);
  const minV = Math.min(...numericValues);
  const maxV = Math.max(...numericValues);
  const span = maxV - minV || 1;

  const yFor = (v) => {
    if (type === "line") {
      const padded = span * 0.35;
      const lo = minV - padded;
      const hi = maxV + padded;
      const f = (v - lo) / (hi - lo || 1);
      return PAD_TOP + plotHeight - f * plotHeight;
    }
    const hi = Math.max(maxV, 1);
    const f = v / hi;
    return PAD_TOP + plotHeight - f * plotHeight;
  };

  const points = values.map((v, i) => ({
    x: PAD_X + i * stepX,
    y: v != null ? yFor(v) : null,
    v,
    label: labels[i],
  }));

  const linePath = points
    .filter((p) => p.y != null)
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.y}`)
    .join(" ");

  const baselineY = PAD_TOP + plotHeight;

  return (
    <div className="variable-chart">
      <div className="variable-chart-label">
        {label} {unitControl}
      </div>
      <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} className="variable-chart-svg">
        <line x1={PAD_X} x2={CHART_WIDTH - PAD_X} y1={baselineY} y2={baselineY} className="variable-chart-baseline" />

        {type === "line" && <path d={linePath} fill="none" stroke={color} strokeWidth={2} />}

        {points.map((p, i) => (
          <g key={i}>
            {type === "bar" && p.y != null && (
              <rect x={p.x - 8} y={p.y} width={16} height={baselineY - p.y} fill={color} rx={2} />
            )}
            {type === "line" && p.y != null && <circle cx={p.x} cy={p.y} r={3} fill={color} />}
            {p.v != null && (
              <text x={p.x} y={Math.max(12, p.y - 8)} textAnchor="middle" className="variable-chart-value">
                {formatValue(p.v)}
              </text>
            )}
            <text x={p.x} y={CHART_HEIGHT - 16} textAnchor="middle" className="variable-chart-day">
              {p.label.weekday}
            </text>
            <text x={p.x} y={CHART_HEIGHT - 5} textAnchor="middle" className="variable-chart-date">
              {p.label.day}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}