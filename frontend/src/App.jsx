import { BarChart3, LayoutDashboard, UserRound } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import {
  getArtistPrediction,
  getArtistPredictions,
  getArtistProfile,
  getEdition,
  getEditionGenreDistribution,
  getEditionPrediction,
  getEditions,
  getGenreTaxonomy,
  getHealthStatus,
} from './api/client.js';
import { AppHeader } from './components/AppHeader.jsx';
import { BottomNavigation } from './components/BottomNavigation.jsx';
import { ArtistProfile } from './pages/ArtistProfile.jsx';
import { Dashboard } from './pages/Dashboard.jsx';

const DEFAULT_YEAR = 2026;

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'ranking', label: 'Ranking', icon: BarChart3 },
  { id: 'artist', label: 'Ficha', icon: UserRound },
];

const EMPTY_APP_DATA = {
  health: null,
  editions: [],
  genreTaxonomy: null,
  edition: null,
  prediction: null,
  ranking: null,
  genreDistribution: null,
  isLoading: true,
  error: null,
  partialErrors: [],
};

const EMPTY_ARTIST_DATA = {
  profile: null,
  prediction: null,
  isLoading: false,
  error: null,
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

function uniqueYears(editions) {
  const years = editions.map((edition) => edition.year).filter(Boolean);
  return years.length > 0 ? [...new Set(years)].sort((a, b) => a - b) : [2022, 2023, 2024, 2025, 2026];
}

function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [selectedYear, setSelectedYear] = useState(DEFAULT_YEAR);
  const [selectedArtistSlug, setSelectedArtistSlug] = useState(null);
  const [filters, setFilters] = useState({ genre: '', query: '' });
  const [appData, setAppData] = useState(EMPTY_APP_DATA);
  const [artistData, setArtistData] = useState(EMPTY_ARTIST_DATA);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardData() {
      setAppData((current) => ({ ...current, isLoading: true, error: null, partialErrors: [] }));

      // The Block 7 dashboard pulls real backend data for the selected year and filters.
      const [healthResult, editionsResult, taxonomyResult, editionResult, predictionResult, rankingResult, genreResult] =
        await Promise.allSettled([
          getHealthStatus(),
          getEditions(),
          getGenreTaxonomy(),
          getEdition(selectedYear),
          getEditionPrediction(selectedYear, 12),
          getArtistPredictions(selectedYear, {
            genre: filters.genre,
            q: filters.query,
            limit: 80,
          }),
          getEditionGenreDistribution(selectedYear),
        ]);

      if (!isMounted) {
        return;
      }

      const healthError = readSettledError(healthResult, 'Health');
      const partialErrors = [
        readSettledError(editionsResult, 'Editions'),
        readSettledError(taxonomyResult, 'Genre taxonomy'),
        readSettledError(editionResult, 'Edition detail'),
        readSettledError(predictionResult, 'Prediction'),
        readSettledError(rankingResult, 'Ranking'),
        readSettledError(genreResult, 'Genre distribution'),
      ].filter(Boolean);

      const ranking = readSettledData(rankingResult, null);
      const rankingItems = ranking?.items ?? [];

      setAppData({
        health: readSettledData(healthResult, null),
        editions: readSettledData(editionsResult, []),
        genreTaxonomy: readSettledData(taxonomyResult, null),
        edition: readSettledData(editionResult, null),
        prediction: readSettledData(predictionResult, null),
        ranking,
        genreDistribution: readSettledData(genreResult, null),
        isLoading: false,
        error: healthError,
        partialErrors,
      });

      // Select a useful default profile so the artist page never starts empty.
      if (!selectedArtistSlug && rankingItems.length > 0) {
        setSelectedArtistSlug(rankingItems[0].slug);
      }
    }

    loadDashboardData();

    return () => {
      isMounted = false;
    };
  }, [selectedYear, filters.genre, filters.query, selectedArtistSlug]);

  useEffect(() => {
    let isMounted = true;

    async function loadArtistData() {
      if (!selectedArtistSlug) {
        setArtistData(EMPTY_ARTIST_DATA);
        return;
      }

      setArtistData((current) => ({ ...current, isLoading: true, error: null }));

      const [profileResult, predictionResult] = await Promise.allSettled([
        getArtistProfile(selectedArtistSlug),
        getArtistPrediction(selectedYear, selectedArtistSlug),
      ]);

      if (!isMounted) {
        return;
      }

      const profile = readSettledData(profileResult, null);
      const artistPrediction = readSettledData(predictionResult, null);
      const errors = [readSettledError(profileResult, 'Artist profile'), readSettledError(predictionResult, 'Artist score')]
        .filter(Boolean)
        .join(' · ');

      setArtistData({
        profile,
        prediction: artistPrediction,
        isLoading: false,
        error: errors || null,
      });
    }

    loadArtistData();

    return () => {
      isMounted = false;
    };
  }, [selectedArtistSlug, selectedYear]);

  const availableYears = useMemo(() => uniqueYears(appData.editions), [appData.editions]);

  function handleArtistSelect(slug) {
    setSelectedArtistSlug(slug);
    setActiveView('artist');
  }

  const sharedDashboardProps = {
    appData,
    selectedYear,
    availableYears,
    filters,
    selectedArtistSlug,
    onYearChange: setSelectedYear,
    onFiltersChange: setFilters,
    onArtistSelect: handleArtistSelect,
    onViewChange: setActiveView,
  };

  const activePage = useMemo(() => {
    if (activeView === 'artist') {
      return (
        <ArtistProfile
          artistData={artistData}
          selectedYear={selectedYear}
          availableYears={availableYears}
          ranking={appData.ranking}
          onYearChange={setSelectedYear}
          onBackToRanking={() => setActiveView('ranking')}
          onArtistSelect={handleArtistSelect}
        />
      );
    }

    return <Dashboard {...sharedDashboardProps} mode={activeView === 'ranking' ? 'ranking' : 'overview'} />;
  }, [activeView, appData, artistData, availableYears, filters, selectedArtistSlug, selectedYear]);

  return (
    <div className="nexus-app">
      <AppHeader
        activeView={activeView}
        navItems={NAV_ITEMS}
        selectedYear={selectedYear}
        onViewChange={setActiveView}
      />

      <main className="app-main" aria-live="polite">
        {activePage}
      </main>

      <BottomNavigation activeView={activeView} navItems={NAV_ITEMS} onViewChange={setActiveView} />
    </div>
  );
}

export default App;
