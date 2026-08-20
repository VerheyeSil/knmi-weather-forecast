import { useState } from "react";
import Sidebar from "./components/Sidebar";
import ForecastView from "./views/ForecastView";
import "./styles.css";

// Each entry becomes one sidebar tab. Add a new view file under src/views/,
// wire it in here with available: true, and it shows up automatically —
// nothing else in the shell needs to change.
const VIEWS = [
  { id: "forecast", label: "Forecast", available: true },
  { id: "trends", label: "Trends", available: false },
  { id: "extremen", label: "Extremes", available: false },
];

export default function App() {
  const [activeView, setActiveView] = useState("forecast");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="app">
      <Sidebar
        views={VIEWS}
        activeView={activeView}
        onSelect={setActiveView}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((c) => !c)}
      />
      <div className="app-main">
        {activeView === "forecast" && <ForecastView />}
      </div>
    </div>
  );
}