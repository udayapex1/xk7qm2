import { NavLink, Route, Routes } from 'react-router-dom';
import ForecastPage from './pages/ForecastPage';
import AccuracyPage from './pages/AccuracyPage';
import DecisionPage from './pages/DecisionPage';
export default function App() {
  return (
    <div className="shell">
      <nav className="topbar">
        <a className="brand" href="/">
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
