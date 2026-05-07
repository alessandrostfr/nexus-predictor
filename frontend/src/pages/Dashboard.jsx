import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { BarChart3, Database, Gauge, LineChart, Music2, Trophy, UsersRound } from 'lucide-react';

import { ArtistCard } from '../components/ArtistCard.jsx';
import { ConnectionBanner } from '../components/ConnectionBanner.jsx';
import { EditionSelector } from '../components/EditionSelector.jsx';
import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { GenreFilter } from '../components/GenreFilter.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { PredictionCard } from '../components/PredictionCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';
import { SkeletonPanel } from '../components/SkeletonPanel.jsx';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

function compactDateRange(edition) {
  if (!edition?.date_start) {
    return 'Fecha pendiente';
  }

  if (!edition.date_end || edition.date_end === edition.date_start) {
    return edition.date_start;
  }

  return `${edition.date_start} → ${edition.date_end}`;
}

function topGenreData(prediction, genreDistribution) {
  const source = prediction?.genre_distribution ?? genreDistribution?.genres ?? genreDistribution?.distribution ?? [];
  return source
    .map((item) => ({
      name: item.name ?? item.main_genre ?? 'Unknown',
      artists: item.artist_count ?? item.count ?? 0,
      percentage: item.percentage ?? 0,
    }))
    .filter((item) => item.artists > 0)
    .slice(0, 8);
}

function getRankingItems(ranking, prediction) {
  return ranking?.items ?? prediction?.top_artist_predictions ?? [];
}

// Main Block 7 dashboard. It handles both the overview and the focused ranking view.
export function Dashboard({
  appData,
  selectedYear,
  availableYears,
  filters,
  selectedArtistSlug,
  mode,
  onYearChange,
  onFiltersChange,
  onArtistSelect,
  onViewChange,
}) {
  const { edition, error, genreDistribution, genreTaxonomy, isLoading, partialErrors, prediction, ranking } = appData;
  const attendance = prediction?.attendance;
  const rankingItems = getRankingItems(ranking, prediction);
  const chartData = topGenreData(prediction, genreDistribution);
  const topArtist = rankingItems[0];
  const isRankingMode = mode === 'ranking';

  return (
    <div className="page-stack">
      <ConnectionBanner isLoading={isLoading} error={error} partialErrors={partialErrors} />

      <section className="hero-panel dashboard-hero">
        <div className="hero-panel-copy">
          <span className="shell-kicker">Bloque 7 · Dashboard real · Nexus Festival</span>
          <h1>{isRankingMode ? 'Ranking de demanda por artista.' : 'Dashboard de edición, demanda y tendencias.'}</h1>
          <p>
            Selector de año, resumen de edición, predicción de asistencia, ranking filtrable y acceso directo a fichas
            de artista con histórico y metadatos.
          </p>
        </div>
        <PredictionCard prediction={prediction} />
      </section>

      <EditionSelector years={availableYears} selectedYear={selectedYear} onYearChange={onYearChange} />

      {isLoading && rankingItems.length === 0 ? <SkeletonPanel variant="dashboard" rows={4} /> : null}

      <section className="metric-grid">
        <MetricCard
          icon={Music2}
          label="Artistas / actuaciones"
          value={formatNumber(edition?.artist_count ?? prediction?.total_artist_predictions)}
          description={edition?.name ?? `Edición ${selectedYear}`}
        />
        <MetricCard
          icon={Gauge}
          label="Asistencia media"
          value={formatNumber(attendance?.predicted_mid)}
          description={attendance ? `${formatNumber(attendance.predicted_low)} - ${formatNumber(attendance.predicted_high)}` : 'Sin predicción'}
          tone="accent"
        />
        <MetricCard
          icon={UsersRound}
          label="Artista destacado"
          value={topArtist?.name ?? '—'}
          description={topArtist ? `${Math.round(topArtist.demand_score)} pts · riesgo ${topArtist.crowd_risk}` : 'Ranking pendiente'}
        />
        <MetricCard
          icon={Database}
          label="Fecha y venue"
          value={compactDateRange(edition)}
          description={edition?.venue ?? 'Fabrik Madrid'}
        />
      </section>

      {!isRankingMode ? (
        <section className="dashboard-grid">
          <ShellCard
            eyebrow="Resumen de edición"
            title={edition?.name ?? `Edición ${selectedYear}`}
            description="Datos base de lineup e histórico conectados al backend."
          >
            <div className="edition-summary-list">
              <div>
                <span>Ciudad</span>
                <strong>{edition?.city ?? 'Humanes de Madrid, Madrid'}</strong>
              </div>
              <div>
                <span>Duración</span>
                <strong>{edition?.duration_hours ? `${edition.duration_hours} h` : 'Pendiente'}</strong>
              </div>
              <div>
                <span>Escenarios</span>
                <strong>{edition?.stage_count ?? 'Pendiente'}</strong>
              </div>
              <div>
                <span>Estado</span>
                <strong>{edition?.status ?? 'Sin datos'}</strong>
              </div>
            </div>
          </ShellCard>

          <ShellCard
            eyebrow="Subgéneros"
            title="Distribución del cartel"
            description="Gráfica compacta pensada para móvil."
            className="chart-card"
          >
            {chartData.length > 0 ? (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} />
                    <YAxis dataKey="name" type="category" width={108} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => [`${value} artistas`, 'Total']} />
                    <Bar dataKey="artists" radius={[0, 10, 10, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyPanel title="Sin distribución" message="No hay distribución de géneros para esta edición." />
            )}
          </ShellCard>
        </section>
      ) : null}

      <ShellCard
        eyebrow="Ranking"
        title={isRankingMode ? 'Ranking completo filtrable' : 'Top artistas por demanda'}
        description="Haz clic en cualquier artista para abrir su ficha individual."
      >
        <GenreFilter
          filters={filters}
          genreTaxonomy={genreTaxonomy}
          prediction={prediction}
          onFiltersChange={onFiltersChange}
        />

        {isLoading && rankingItems.length === 0 ? (
          <SkeletonPanel variant="ranking" rows={5} />
        ) : rankingItems.length > 0 ? (
          <div className="ranking-layout">
            <div className="artist-ranking-list">
              {rankingItems.slice(0, isRankingMode ? 80 : 12).map((artist) => (
                <ArtistCard
                  key={artist.slug}
                  artist={artist}
                  isSelected={selectedArtistSlug === artist.slug}
                  onSelect={onArtistSelect}
                />
              ))}
            </div>

            {!isRankingMode ? (
              <aside className="ranking-aside">
                <div className="aside-icon">
                  <Trophy size={20} />
                </div>
                <h3>Ranking completo</h3>
                <p>Consulta más artistas, usa filtros por subgénero y búsqueda, y abre fichas individuales.</p>
                <button className="secondary-action" type="button" onClick={() => onViewChange('ranking')}>
                  <BarChart3 size={16} />
                  Ver ranking completo
                </button>
              </aside>
            ) : null}
          </div>
        ) : (
          <EmptyPanel
            title="Sin artistas para este filtro"
            message="Prueba a limpiar la búsqueda o seleccionar otro subgénero."
          />
        )}
      </ShellCard>

      <ShellCard
        eyebrow="Comparativa histórica"
        title="Lectura rápida del histórico"
        description="Base para comparar ediciones sin entrar todavía en salas ni timetable, que corresponde al Bloque 8."
      >
        <div className="history-strip">
          {availableYears.map((year) => {
            const editionMatch = appData.editions.find((item) => item.year === year);
            const isCurrent = Number(year) === Number(selectedYear);

            return (
              <button
                key={year}
                type="button"
                className={isCurrent ? 'history-year history-year-active' : 'history-year'}
                onClick={() => onYearChange(year)}
              >
                <span>{year}</span>
                <strong>{formatNumber(editionMatch?.artist_count)}</strong>
                <small>{editionMatch?.stage_count ?? '—'} escenarios</small>
              </button>
            );
          })}
        </div>
        <div className="history-note">
          <LineChart size={16} />
          El comparador usa años, lineup y predicción; el riesgo por sala queda reservado para el Bloque 8.
        </div>
      </ShellCard>
    </div>
  );
}
