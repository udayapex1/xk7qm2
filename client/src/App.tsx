import { NavLink, Route, Routes } from 'react-router-dom';
import ForecastPage from './pages/ForecastPage';
import AccuracyPage from './pages/AccuracyPage';
import DecisionPage from './pages/DecisionPage';
export default function App() {
  return (
    <div className="shell">
      <nav className="topbar">
        <a className="brand" href="/">
          <svg
            aria-hidden="true"
            viewBox="0 0 24 24"
            className="brand-icon"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          >
            <path d="M3 8h11a3 3 0 1 0-3-3" />
            <path d="M2 12h17a2 2 0 1 1-2 2" />
            <path d="M4 16h8a2 2 0 1 1-2 2" />
          </svg>
          Wind Forecast Portal
        </a>
        <div className="tabs">
          <NavLink end to="/">
            Forecast
          </NavLink>
          <NavLink to="/accuracy">Accuracy</NavLink>
          <NavLink to="/decision">Decision helper</NavLink>
        </div>
      </nav>
      <Routes>
        <Route path="/" element={<ForecastPage />} />
        <Route path="/accuracy" element={<AccuracyPage />} />
        <Route path="/decision" element={<DecisionPage />} />
      </Routes>
      <footer>
        National wind data: Elexon BMRS · January 2026 · Times shown in
        Europe/London
      </footer>
    </div>
  );
}
