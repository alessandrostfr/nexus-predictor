import { Gauge, LineChart, ShieldAlert, UsersRound } from 'lucide-react';

import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

// Prediction shell page. It proves the API works, while the full ranking UX remains Block 7.
export function PredictionsShell({ shellData }) {
  const { prediction } = shellData;
  const attendance = prediction?.attendance;
  const topArtists = prediction?.top_artist_predictions ?? [];
  const genreDistribution = prediction?.genre_distribution ?? [];

  return (
    <div className="page-stack">
      <section className="page-heading">
        <span className="shell-kicker">Prediction shell</span>
        <h1>Predicciones visibles sin convertir aún esto en dashboard completo.</h1>
        <p>
          El Bloque 6 valida que React consume el motor predictivo. Rankings completos, filtros y perfiles
          entran en el Bloque 7.
        </p>
      </section>

      <section className="metric-grid">
        <MetricCard
          icon={UsersRound}
          label="Asistencia media"
          value={formatNumber(attendance?.predicted_mid)}
          description="Predicción interpretable del Bloque 5."
          tone="mint"
        />
        <MetricCard
          icon={Gauge}
          label="Rango bajo"
          value={formatNumber(attendance?.predicted_low)}
          description="Estimación, no cifra oficial."
        />
        <MetricCard
          icon={LineChart}
          label="Rango alto"
          value={formatNumber(attendance?.predicted_high)}
          description="Sensibilidad del modelo actual."
        />
        <MetricCard
          icon={ShieldAlert}
          label="Confianza"
          value={attendance?.confidence ?? '—'}
          description="Se reforzará con horarios/salas."
          tone="violet"
        />
      </section>

      <section className="content-grid content-grid-two">
        <ShellCard
          eyebrow="Top preview"
          title="Primeras señales de demanda"
          description="Solo una previsualización para validar integración; el ranking completo se diseñará en el Bloque 7."
        >
          <div className="artist-preview-list">
            {topArtists.slice(0, 6).map((artist) => (
              <article key={artist.slug} className="artist-preview-row">
                <div>
                  <strong>{artist.rank}. {artist.name}</strong>
                  <span>{artist.main_genre} · {artist.crowd_risk}</span>
                </div>
                <b>{artist.demand_score}</b>
              </article>
            ))}
          </div>
          {topArtists.length === 0 ? (
            <EmptyPanel title="Sin ranking todavía" description="Genera predicciones o arranca el backend para alimentar esta vista." />
          ) : null}
        </ShellCard>

        <ShellCard
          eyebrow="Géneros"
          title="Distribución preparada"
          description="El diseño ya puede recibir distribución por subgénero sin montar todavía gráficas completas."
        >
          <div className="genre-preview-list">
            {genreDistribution.slice(0, 6).map((genre) => (
              <article key={genre.name} className="genre-preview-row">
                <span>{genre.name}</span>
                <strong>{genre.percentage}%</strong>
              </article>
            ))}
          </div>
          {genreDistribution.length === 0 ? (
            <EmptyPanel title="Sin distribución cargada" description="El endpoint de predicciones alimentará esta zona." />
          ) : null}
        </ShellCard>
      </section>
    </div>
  );
}
