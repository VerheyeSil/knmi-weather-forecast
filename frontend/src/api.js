const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export async function fetchForecast() {
  const res = await fetch(`${API_BASE}/forecast`);
  if (!res.ok) throw new Error(`Forecast request failed: ${res.status}`);
  return res.json();
}