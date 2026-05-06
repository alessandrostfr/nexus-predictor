import { CalendarDays, Database, Gauge, LineChart, UsersRound } from 'lucide-react';

import { ConnectionBanner } from '../components/ConnectionBanner.jsx';
import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

// Landing dashboard shell. It previews data without becoming the full Block 7 dashboard.
export function DashboardShell({ shellData }) {
  const { editions, error, isLoading, partialErrors, prediction } = shellData;
  const attendance = prediction?.attendance;
  const topArtists = prediction?.top_artist_predictions ?? [];
  const years = editions.length > 0 ? editions.map((edition) => edition.year) : [2022, 2023, 2024, 2025, 2026];

  return (
    <div className="page-stack">
      <ConnectionBanner isLoading={isLoading} error={error} partialErrors={partialErrors} />

      <section className="hero-panel">
        <div className="hero-panel-copy">
          <span className="shell-kicker">MVP · Nexus Festival · Fabrik Madrid</span>
          <h1>Una shell limpia para analizar ediciones, demanda y predicciones.</h1>
          <p>
            Base visual mobile-first para conectar el backend ya construido con una interfaz oscura,
            minimalista y preparada para el dashboard completo del siguiente bloque.
          </p>
        </div>

        <div className="hero-panel-card" aria-label="Current prediction preview">
          <span>Predicción 2026</span>
          <strong>{formatNumber(attendance?.predicted_mid)}</strong>
          <small>
            rango {formatNumber(attendance?.predicted_low)} - {formatNumber(attendance?.predicted_high)} asistentes
          </small>
        </div>
      </section>

      <section className="metric-grid" aria-label="Dashboard shell metrics">
        <MetricCard
          icon={CalendarDays}
          label="Ediciones"
          value={years.length}
          description="Selector preparado para 2022-2026."
          tone="mint"
        />
        <MetricCard
          icon={UsersRound}
          label="Artistas rankeados"
          value={formatNumber(prediction?.total_artist_predictions)}
          description="Datos del motor predictivo del Bloque 5."
        />
        <MetricCard
          icon={Gauge}
          label="Confianza asistencia"
          value={attendance?.confidence ?? '—'}
          description="Se muestra como estimación, no como dato oficial."
        />
        <MetricCard
          icon={LineChart}
          label="Top preview"
          value={topArtists[0]?.name ?? '—'}
          description="Ranking completo queda para el Bloque 7."
          tone="violet"
        />
      </section>

      <section className="content-grid content-grid-two">
        <ShellCard
          eyebrow="Selector preparado"
          title="Ediciones disponibles"
          description="El shell deja lista la navegación por año, sin implementar todavía el dashboard completo por edición."
        >
          <div className="year-chip-list">
            {years.map((year) => (
              <span key={year}>{year}</span>
            ))}
          </div>
        </ShellCard>

        <ShellCard
          eyebrow="Siguiente paso"
          title="Bloque 7 listo para construir encima"
          description="Esta base ya tiene cards, navegación, estados de carga/error y cliente API centralizado."
        >
          <EmptyPanel
            title="Ranking y fichas pendientes"
            description="Los rankings completos, filtros avanzados y fichas individuales de artista se implementarán en el Bloque 7."
          />
        </ShellCard>
      </section>

      <ShellCard
        eyebrow="Arquitectura visual"
        title="Base responsive validable"
        description="El layout usa una columna en móvil, grids fluidos en desktop y una navegación inferior fija para uso cómodo en pantalla pequeña."
      >
        <div className="readiness-list">
          <span>Layout base</span>
          <span>Navegación mobile-first</span>
          <span>Cards reutilizables</span>
          <span>Loading states</span>
          <span>Error states</span>
          <span>Cliente API</span>
        </div>
      </ShellCard>
    </div>
  );
}
