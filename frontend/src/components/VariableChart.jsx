const CHART_WIDTH = 640;
const CHART_HEIGHT = 130;
const PAD_X = 32;
const PAD_TOP = 26;
const PAD_BOTTOM = 26;

const COMPASS_POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

function degreesToCompass(deg) {
  if (deg == null) return "";
  const idx = Math.round(deg / 45) % 8;
  return COMPASS_POINTS[idx];
}

export default function VariableChart({
  label,
  unit,
  color,
  type = "line",
  values,
  minValues,
  maxValues,
  directionValues,
  labels,
  formatValue = (v) => Math.round(v),
  unitOptions,
  activeUnitIndex,
  onToggleUnit,
  fullWidth = false,
}) {
  const hasData = values.some((v) => v != null);

  const plotWidth = CHART_WIDTH - PAD_X * 2;
  const plotHeight = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;
  const stepX = plotWidth / (values.length - 1 || 1);

  const unitControl =
    unitOptions && unitOptions.length > 1 ? (
      <button
        type="button"
        className={`variable-chart-unit-toggle ${activeUnitIndex === 1 ? "is-secondary" : ""}`}
        onClick={onToggleUnit}
        aria-label={`Switch unit (currently ${unitOptions[activeUnitIndex]})`}
      >
        {unitOptions.map((opt) => (
          <span className="unit-toggle-option" key={opt}>
            {opt}
          </span>
        ))}
      </button>
    ) : (
      <span className="variable-chart-unit">{unit}</span>
    );

  if (!hasData) {
    return (
      <div className={`variable-chart variable-chart--empty ${fullWidth ? "variable-chart--full" : ""}`}>
        <div className="variable-chart-label">
          {label} {unitControl}
        </div>
        <p>No reliable forecast data for this station.</p>
      </div>
    );
  }

  if (type === "wind-combo") {
    const dayPoints = values.map((v, i) => ({
      x: PAD_X + i * stepX,
      speed: v,
      dir: directionValues ? directionValues[i] : null,
      label: labels[i],
    }));

    return (
      <div className={`variable-chart ${fullWidth ? "variable-chart--full" : ""}`}>
        <div className="variable-chart-label">
          {label} {unitControl}
        </div>
        <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} className="variable-chart-svg">
          {dayPoints.map((p, i) => (
            <g key={i}>
              {p.speed != null && (
                <text x={p.x} y={16} textAnchor="middle" className="variable-chart-value">
                  {formatValue(p.speed)}
                </text>
              )}
              {renderWindNeedle(p.x, 62, p.dir, color, `wind-${i}`)}
              {p.dir != null && (
                <text x={p.x} y={92} textAnchor="middle" className="variable-chart-direction-value">
                  {degreesToCompass(p.dir)}
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

  const numericValues = [
    ...values,
    ...(type === "line" ? minValues || [] : []),
    ...(type === "line" ? maxValues || [] : []),
  ].filter((v) => v != null);

  const minV = Math.min(...numericValues);
  const maxV = Math.max(...numericValues);
  const span = maxV - minV || 1;

  const padded = type === "line" ? span * 0.15 : 0;
  const scaleMin = type === "line" ? minV - padded : 0;
  const scaleMax = type === "line" ? maxV + padded : Math.max(maxV, 1);

  const yFor = (v) => {
    const f = (v - scaleMin) / (scaleMax - scaleMin || 1);
    return PAD_TOP + plotHeight - f * plotHeight;
  };

  const points = values.map((v, i) => ({
    x: PAD_X + i * stepX,
    y: v != null ? yFor(v) : null,
    v,
    label: labels[i],
  }));

  const rangePoints =
    type === "line" && minValues && maxValues
      ? values.map((_, i) => ({
          x: PAD_X + i * stepX,
          minY: minValues[i] != null ? yFor(minValues[i]) : null,
          maxY: maxValues[i] != null ? yFor(maxValues[i]) : null,
        }))
      : [];

  const validRangePoints = rangePoints.filter((p) => p.minY != null && p.maxY != null);

  const rangePath =
    validRangePoints.length > 0
      ? [
          ...validRangePoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.maxY}`),
          ...[...validRangePoints].reverse().map((p) => `L ${p.x},${p.minY}`),
          "Z",
        ].join(" ")
      : "";

  const linePath = points
    .filter((p) => p.y != null)
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x},${p.y}`)
    .join(" ");

  const baselineY = PAD_TOP + plotHeight;

  const gridCount = 4;
  const gridValues =
    type === "line"
      ? Array.from({ length: gridCount + 1 }, (_, i) => {
          const value = scaleMin + ((scaleMax - scaleMin) * i) / gridCount;
          return { value, y: PAD_TOP + plotHeight - (i / gridCount) * plotHeight };
        })
      : [];

  return (
    <div className={`variable-chart ${fullWidth ? "variable-chart--full" : ""}`}>
      <div className="variable-chart-label">
        {label} {unitControl}
      </div>

      <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} className="variable-chart-svg">
        {type === "line" &&
          gridValues.map((grid, i) => (
            <g key={`grid-${i}`}>
              <line x1={PAD_X} x2={CHART_WIDTH - PAD_X} y1={grid.y} y2={grid.y} className="variable-chart-grid" />
              <text x={PAD_X - 6} y={grid.y + 3} textAnchor="end" className="variable-chart-axis-value">
                {Math.round(grid.value)}°
              </text>
            </g>
          ))}

        {type === "bar" && (
          <line x1={PAD_X} x2={CHART_WIDTH - PAD_X} y1={baselineY} y2={baselineY} className="variable-chart-baseline" />
        )}

        {type === "line" && rangePath && <path d={rangePath} fill={color} opacity={0.14} stroke="none" />}
        {type === "line" && linePath && <path d={linePath} fill="none" stroke={color} strokeWidth={2} />}

        {points.map((p, i) => (
          <g key={i}>
            {type === "bar" && p.y != null && (
              <rect x={p.x - 8} y={p.y} width={16} height={baselineY - p.y} fill={color} rx={2} />
            )}
            {type === "line" && p.y != null && <circle cx={p.x} cy={p.y} r={3} fill={color} />}

            {type === "bar" && p.v != null && (
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

function renderWindNeedle(x, y, degrees, color, key) {
  if (degrees == null) {
    return (
      <text key={key} x={x} y={y + 4} textAnchor="middle" className="variable-chart-day">
        —
      </text>
    );
  }
  return (
    <g key={key}>
      <circle cx={x} cy={y} r={14} className="wind-dial-ring" />
      <g transform={`translate(${x} ${y}) rotate(${degrees})`}>
        <path d="M 0,-14 L 5,8 L 0,4 L -5,8 Z" fill={color} className="wind-dial-needle" />
      </g>
      <circle cx={x} cy={y} r={2.5} className="wind-dial-pivot" stroke={color} />
    </g>
  );
}