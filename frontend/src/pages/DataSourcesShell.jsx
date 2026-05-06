import { Database, FileJson, Music2, Warehouse } from 'lucide-react';

import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';

// Data shell page. It validates API reachability without adding admin/data-editing scope.
export function DataSourcesShell({ shellData }) {
  const { editions, genres, venue } = shellData;
  const roomCount = venue?.rooms?.length ?? 0;
  const knownGenres = genres.filter((genre) => genre.name !== 'Unknown');

  return (
    <div className="page-stack">
      <section className="page-heading">
        <span className="shell-kicker">Data shell</span>
        <h1>Fuentes conectadas, edición visual todavía controlada.</h1>
        <p>
          Esta pantalla deja preparadas las secciones de datos que después usará el dashboard,
          manteniendo el alcance del Bloque 6 como shell visual.
        </p>
      </section>

      <section className="metric-grid">
        <MetricCard
          icon={FileJson}
          label="Ediciones API"
          value={editions.length || '—'}
          description="Endpoint /api/editions conectado."
          tone="mint"
        />
        <MetricCard
          icon={Music2}
          label="Géneros"
          value={knownGenres.length || '—'}
          description="Taxonomía usable en frontend."
        />
        <MetricCard
          icon={Warehouse}
          label="Salas Fabrik"
          value={roomCount || '—'}
          description="Vista de riesgo queda para Bloque 8."
        />
        <MetricCard
          icon={Database}
          label="Estado"
          value="Ready"
          description="Shell preparada para datos reales."
          tone="violet"
        />
      </section>

      <section className="content-grid content-grid-two">
        <ShellCard
          eyebrow="Ediciones"
          title="Años versionados"
          description="La app ya puede mostrar años reales desde el backend."
        >
          <div className="edition-list">
            {editions.map((edition) => (
              <article key={edition.year} className="edition-row">
                <strong>{edition.year}</strong>
                <span>{edition.edition_name ?? edition.name ?? 'Nexus Festival'}</span>
              </article>
            ))}
            {editions.length === 0 ? (
              <EmptyPanel title="Sin ediciones cargadas" description="Arranca el backend para ver los años disponibles." />
            ) : null}
          </div>
        </ShellCard>

        <ShellCard
          eyebrow="Fabrik"
          title="Venue preparado"
          description="La estructura visual ya separa datos reales de estimaciones."
        >
          <div className="room-preview-list">
            {(venue?.rooms ?? []).slice(0, 5).map((room) => (
              <article key={room.name} className="room-row">
                <span>{room.name}</span>
                <strong>{room.estimated_capacity ? `${room.estimated_capacity} pax` : 'estimado'}</strong>
              </article>
            ))}
          </div>
          {roomCount === 0 ? (
            <EmptyPanel title="Venue sin datos visibles" description="La API de salas se conectará aquí cuando esté disponible." />
          ) : null}
        </ShellCard>
      </section>
    </div>
  );
}
