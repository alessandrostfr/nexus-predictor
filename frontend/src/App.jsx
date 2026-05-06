import { BarChart3, Database, LayoutDashboard } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  getEditionPrediction,
  getEditions,
  getFabrikVenue,
  getGenres,
  getHealthStatus,
} from './api/client.js';
import { AppHeader } from './components/AppHeader.jsx';
import { BottomNavigation } from './components/BottomNavigation.jsx';
import { DashboardShell } from './pages/DashboardShell.jsx';
import { DataSourcesShell } from './pages/DataSourcesShell.jsx';
import { PredictionsShell } from './pages/PredictionsShell.jsx';

const DEFAULT_YEAR = 2026;

const NAV_ITEMS = [
  { id: 'overview', label: 'Inicio', icon: LayoutDashboard },
  { id: 'data', label: 'Datos', icon: Database },
  { id: 'predictions', label: 'Predicción', icon: BarChart3 },
];

const INITIAL_SHELL_DATA = {
  health: null,
  editions: [],
  genres: [],
  venue: null,
  prediction: null,
  isLoading: true,
  error: null,
  partialErrors: [],
};

function readSettledData(result, fallback) {
  return result.status === 'fulfilled' ? result.value.data : fallback;
}

function readSettledError(result, label) {
  if (result.status === 'fulfilled') {
    return null;
  }

  return `${label}: ${result.reason?.message ?? 'unknown error'}`;
}

function App() {
  const [activeView, setActiveView] = useState('overview');
  const [shellData, setShellData] = useState(INITIAL_SHELL_DATA);

  useEffect(() => {
    let isMounted = true;

    async function loadShellData() {
      setShellData((current) => ({ ...current, isLoading: true, error: null }));

      // Block 6 intentionally loads only shell-level data.
      const [healthResult, editionsResult, genresResult, venueResult, predictionResult] = await Promise.allSettled([
        getHealthStatus(),
        getEditions(),
        getGenres(),
        getFabrikVenue(),
        getEditionPrediction(DEFAULT_YEAR, 6),
      ]);

      if (!isMounted) {
        return;
      }

      const healthError = readSettledError(healthResult, 'Health');
      const partialErrors = [
        readSettledError(editionsResult, 'Editions'),
        readSettledError(genresResult, 'Genres'),
        readSettledError(venueResult, 'Venue'),
        readSettledError(predictionResult, 'Predictions'),
      ].filter(Boolean);

      setShellData({
        health: readSettledData(healthResult, null),
        editions: readSettledData(editionsResult, []),
        genres: readSettledData(genresResult, []),
        venue: readSettledData(venueResult, null),
        prediction: readSettledData(predictionResult, null),
        isLoading: false,
        error: healthError,
        partialErrors,
      });
    }

    loadShellData();

    return () => {
      isMounted = false;
    };
  }, []);

  const activePage = useMemo(() => {
    if (activeView === 'data') {
      return <DataSourcesShell shellData={shellData} />;
    }

    if (activeView === 'predictions') {
      return <PredictionsShell shellData={shellData} />;
    }

    return <DashboardShell shellData={shellData} />;
  }, [activeView, shellData]);

  return (
    <div className="nexus-app">
      <AppHeader activeView={activeView} navItems={NAV_ITEMS} onViewChange={setActiveView} />

      <main className="app-main" aria-live="polite">
        {activePage}
      </main>

      <BottomNavigation activeView={activeView} navItems={NAV_ITEMS} onViewChange={setActiveView} />
    </div>
  );
}

export default App;
