import { useEffect, useState } from "react";
import { fetchForecast } from "./api";
import NLMap from "./components/LeafletMap";
import StationPanel from "./components/StationPanel";
import "./styles.css";

export default function App() {
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

  // Client-side ticking of the cache-age label, just for the live feel —
  // purely cosmetic, doesn't refetch.
  useEffect(() => {
    if (cacheAge == null) return;
    const id = setInterval(() => setCacheAge((v) => v + 1), 1000);
    return () => clearInterval(id);
  }, [cacheAge != null]);

  const selected = stations.find((s) => s.station === selectedId) || null;

  return (
    <div className="app">
      <header className="app-header">
        <h1>KNMI Weekverwachting</h1>
        <p className="app-status">
          {status === "loading" && "data laden…"}
          {status === "error" && "kon geen verbinding maken met de API"}
          {status === "ready" && cacheAge != null && `data ⟳ ${formatAge(cacheAge)} geleden`}
        </p>
      </header>

      <main className="app-body">
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
  return `${Math.floor(minutes / 60)}u ${minutes % 60}m`;
}