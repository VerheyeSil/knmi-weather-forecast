import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const NL_CENTER = [52.1, 5.3];
const DEFAULT_ZOOM = 7;

// Cool water-teal -> brass -> signal-red, roughly 0C to 28C
function tempToColor(temp) {
  if (temp == null) return "#4A6068";
  const stops = [
    { t: 2, c: [51, 80, 92] },
    { t: 14, c: [200, 155, 74] },
    { t: 26, c: [193, 80, 63] },
  ];
  let lo = stops[0];
  let hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (temp >= stops[i].t && temp <= stops[i + 1].t) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const span = hi.t - lo.t || 1;
  const f = Math.max(0, Math.min(1, (temp - lo.t) / span));
  const c = lo.c.map((v, i) => Math.round(v + (hi.c[i] - v) * f));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

export default function NLMap({ stations, selectedId, onSelect }) {
  if (!stations.length) return null;

  return (
    <MapContainer
      center={NL_CENTER}
      zoom={DEFAULT_ZOOM}
      scrollWheelZoom={true}
      className="leaflet-map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      {stations.map((s) => {
        const isSelected = s.station === selectedId;
        const temp = s["temp_mean_+1"];
        return (
          <CircleMarker
            key={s.station}
            center={[s.lat, s.lon]}
            radius={isSelected ? 8 : 5}
            pathOptions={{
              fillColor: tempToColor(temp),
              fillOpacity: 1,
              color: isSelected ? "#ECE7DC" : "#16232B",
              weight: isSelected ? 2 : 1,
            }}
            eventHandlers={{ click: () => onSelect(s.station) }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={1}>
              {s.name} {temp != null ? `· ${temp.toFixed(1)}°C` : ""}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}