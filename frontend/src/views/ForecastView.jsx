import { useEffect, useState } from "react";
import { fetchForecast } from "../api";
import NLMap from "../components/LeafletMap";
import StationPanel from "../components/StationPanel";

export default function ForecastView() {
  const [stations, setStations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [cacheAge, setCacheAge] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error

  useEffect(() => {
    fetchForecast()
      .then((data) => {
        setStations(data.forecast);
        setCacheAge(data.cache_age_seconds);
        setSelectedId(data.forecast[0]?.station ?? null);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  // Client-side ticking of the cache-age label, purely cosmetic.
  useEffect(() => {
    if (cacheAge == null) return;
    const id = setInterval(() => setCacheAge((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, [cacheAge != null]);

  const selected = stations.find((s) => s.station === selectedId) || null;

  return (
    <div className="view">
      <header className="view-header">
        <h1>Week prediction</h1>
        <p className="view-status">
          {status === "loading" && "loading data…"}
          {status === "error" && "could not establish connection with the API"}
          {status === "ready" && cacheAge != null && `data ⟳ ${formatAge(cacheAge)} ago`}
        </p>
      </header>

      <main className="view-body">
        <NLMap stations={stations} selectedId={selectedId} onSelect={setSelectedId} />
        <StationPanel station={selected} />
      </main>
    </div>
  );
}

function formatAge(seconds) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}