import { Activity, CalendarDays, Database, Github, Music2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getEditions, getHealthStatus } from './api/client.js';

function App() {
  const [apiStatus, setApiStatus] = useState('Checking API...');
  const [editions, setEditions] = useState([]);

  useEffect(() => {
    async function loadInitialData() {
      try {
        // Block 0 only verifies that frontend and backend can talk to each other.
        const health = await getHealthStatus();
        const editionResponse = await getEditions();

        setApiStatus(health.data.status === 'ok' ? 'API connected' : 'API response received');
        setEditions(editionResponse.data ?? []);
      } catch (error) {
        console.error(error);
        setApiStatus('API not connected yet');
        setEditions([]);
      }
    }

    loadInitialData();
  }, []);

  return (
    <main className="app-shell">
      <section className="hero-card">
        <div className="eyebrow">
          <Music2 size={16} />
          Nexus Predictor
        </div>

        <h1>Festival intelligence for Nexus at Fabrik Madrid.</h1>

        <p className="hero-copy">
          Minimal, responsive dashboard foundation for researching historical editions,
          enriching artists and predicting attendance, demand and crowd pressure.
        </p>

        <div className="status-pill">
          <Activity size={16} />
          {apiStatus}
        </div>
      </section>

      <section className="grid-section">
        <article className="info-card">
          <CalendarDays size={22} />
          <h2>Edition selector</h2>
          <p>Seed files are ready for 2022, 2023, 2024, 2025 and 2026.</p>
          <div className="year-list">
            {editions.length > 0
              ? editions.map((edition) => <span key={edition.year}>{edition.year}</span>)
              : ['2022', '2023', '2024', '2025', '2026'].map((year) => <span key={year}>{year}</span>)}
          </div>
        </article>

        <article className="info-card">
          <Database size={22} />
          <h2>Data-first roadmap</h2>
          <p>
            The next block will replace placeholders with researched public sources,
            artist lineups, venue capacity and attendance signals.
          </p>
        </article>

        <article className="info-card">
          <Github size={22} />
          <h2>Git-ready structure</h2>
          <p>
            Backend, frontend, docs and research folders are separated so every block
            can close with a clean commit.
          </p>
        </article>
      </section>
    </main>
  );
}

export default App;
