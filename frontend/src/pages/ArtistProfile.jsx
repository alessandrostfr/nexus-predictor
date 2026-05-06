import { ArrowLeft, Clock3, ExternalLink, Headphones, Info, ListMusic, Music2, Radio, ShieldAlert, UserRound } from 'lucide-react';

import { ArtistCard } from '../components/ArtistCard.jsx';
import { EditionSelector } from '../components/EditionSelector.jsx';
import { EmptyPanel } from '../components/EmptyPanel.jsx';
import { MetricCard } from '../components/MetricCard.jsx';
import { ShellCard } from '../components/ShellCard.jsx';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

function getInitials(name) {
  return (name ?? 'NP')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

function riskLabel(risk) {
  const labels = {
    very_high: 'Muy alto',
    high: 'Alto',
    medium: 'Medio',
    low: 'Bajo',
  };

  return labels[risk] ?? risk ?? '—';
}

function externalLinks(profile) {
  return Object.entries(profile?.external_links ?? {}).filter(([, url]) => Boolean(url));
}

// Artist detail page. It deliberately stays light so missing enrichment never breaks the UI.
export function ArtistProfile({
  artistData,
  selectedYear,
  availableYears,
  ranking,
  onYearChange,
  onBackToRanking,
  onArtistSelect,
}) {
  const { error, isLoading, prediction, profile } = artistData;
  const displayName = profile?.name ?? prediction?.name ?? 'Selecciona un artista';
  const genre = prediction?.main_genre ?? profile?.primary_genre_seed ?? 'Unknown';
  const topTracks = profile?.top_tracks ?? [];
  const latestReleases = profile?.latest_releases ?? [];
  const appearances = profile?.appearances ?? [];
  const links = externalLinks(profile);
  const relatedRanking = ranking?.items?.slice(0, 6) ?? [];

  if (!profile && !prediction && !isLoading) {
    return (
      <div className="page-stack">
        <EditionSelector years={availableYears} selectedYear={selectedYear} onYearChange={onYearChange} />
        <EmptyPanel
          title="Ficha pendiente"
          message="Selecciona un artista desde el ranking para abrir su ficha individual."
        />
      </div>
    );
  }

  return (
    <div className="page-stack">
      <EditionSelector years={availableYears} selectedYear={selectedYear} onYearChange={onYearChange} />

      <button className="ghost-action" type="button" onClick={onBackToRanking}>
        <ArrowLeft size={16} />
        Volver al ranking
      </button>

      {error ? (
        <aside className="connection-banner connection-banner-warning">
          <ShieldAlert size={17} />
          La ficha se ha cargado parcialmente: {error}
        </aside>
      ) : null}

      <section className="artist-profile-hero">
        <div className="artist-avatar" aria-hidden="true">
          {profile?.image_url ? <img src={profile.image_url} alt="" /> : <span>{getInitials(displayName)}</span>}
        </div>
        <div className="artist-profile-copy">
          <span className="shell-kicker">Ficha de artista · {selectedYear}</span>
          <h1>{isLoading ? 'Cargando ficha...' : displayName}</h1>
          <p>{profile?.bio ?? 'Bio externa pendiente. La app usa datos internos hasta activar enriquecimiento real.'}</p>
          <div className="artist-pill-row">
            <span>{genre}</span>
            <span>{prediction?.artist_kind ?? 'artist'}</span>
            <span>{prediction?.confidence ?? profile?.data_status ?? 'pending'}</span>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        <MetricCard
          icon={Radio}
          label="Demand score"
          value={prediction ? Math.round(prediction.demand_score) : '—'}
          description={prediction ? `Riesgo ${riskLabel(prediction.crowd_risk)}` : 'Sin score para este año'}
          tone="accent"
        />
        <MetricCard
          icon={Clock3}
          label="Apariciones Nexus"
          value={formatNumber(profile?.appearance_count ?? prediction?.appearance_count)}
          description={(profile?.appearance_years ?? prediction?.previous_appearance_years ?? []).join(', ') || 'Nuevo o sin histórico'}
        />
        <MetricCard
          icon={Music2}
          label="Performance"
          value={prediction?.performance_types?.join(', ') || '—'}
          description={prediction?.performance_names?.join(' · ') || 'Sin performance vinculada'}
        />
        <MetricCard
          icon={Info}
          label="Estado ficha"
          value={profile?.data_status ?? 'pending'}
          description={profile?.manual_review ? 'Revisión manual activa' : 'Perfil generado desde dataset'}
        />
      </section>

      <section className="profile-grid">
        <ShellCard eyebrow="Histórico" title="Apariciones y comparador" description="Resumen de apariciones detectadas en el dataset Nexus.">
          {appearances.length > 0 ? (
            <div className="appearance-list">
              {appearances.map((appearance, index) => (
                <article key={`${appearance.year}-${appearance.performance_display_name}-${index}`} className="appearance-item">
                  <strong>{appearance.year}</strong>
                  <div>
                    <span>{appearance.performance_display_name ?? appearance.display_name ?? displayName}</span>
                    <small>{appearance.performance_type ?? 'performance'} · {appearance.source_key ?? 'dataset interno'}</small>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyPanel title="Sin histórico detallado" message="El perfil no tiene apariciones enriquecidas todavía." />
          )}
        </ShellCard>

        <ShellCard eyebrow="Scoring" title="Por qué puntúa así" description="Factores interpretables del motor predictivo.">
          {prediction?.factors?.length > 0 ? (
            <div className="factor-list">
              {prediction.factors.map((factor) => (
                <article key={factor.key} className="factor-item">
                  <div>
                    <strong>{factor.label}</strong>
                    <span>{factor.explanation}</span>
                  </div>
                  <b>{factor.contribution}/{factor.max_contribution}</b>
                </article>
              ))}
            </div>
          ) : (
            <EmptyPanel title="Sin factores" message="No hay score disponible para este artista en la edición seleccionada." />
          )}
        </ShellCard>
      </section>

      <section className="profile-grid">
        <ShellCard eyebrow="Top tracks" title="Top 10 canciones" description="Se rellena automáticamente cuando el enriquecimiento externo aporta datos.">
          {topTracks.length > 0 ? (
            <div className="track-list">
              {topTracks.slice(0, 10).map((track, index) => (
                <a key={`${track.title}-${index}`} href={track.external_url ?? '#'} className="track-item">
                  <span>#{index + 1}</span>
                  <div>
                    <strong>{track.title}</strong>
                    <small>{track.listeners ? `${formatNumber(track.listeners)} listeners` : track.source}</small>
                  </div>
                  <Headphones size={15} />
                </a>
              ))}
            </div>
          ) : (
            <EmptyPanel
              title="Top tracks pendientes"
              message="La ficha no rompe si no hay canciones. Activa Spotify/Last.fm para completar esta sección."
            />
          )}
        </ShellCard>

        <ShellCard eyebrow="Lanzamientos" title="Últimos 5 lanzamientos" description="Preparado para Spotify y MusicBrainz.">
          {latestReleases.length > 0 ? (
            <div className="track-list">
              {latestReleases.slice(0, 5).map((release, index) => (
                <a key={`${release.title}-${index}`} href={release.external_url ?? '#'} className="track-item">
                  <ListMusic size={15} />
                  <div>
                    <strong>{release.title}</strong>
                    <small>{release.release_date ?? release.release_type ?? release.source}</small>
                  </div>
                  <ExternalLink size={14} />
                </a>
              ))}
            </div>
          ) : (
            <EmptyPanel
              title="Lanzamientos pendientes"
              message="No hay últimos lanzamientos en cache local para este artista."
            />
          )}
        </ShellCard>
      </section>

      <ShellCard eyebrow="Enlaces y artistas destacados" title="Explora más artistas">
        {links.length > 0 ? (
          <div className="external-link-row">
            {links.map(([label, url]) => (
              <a key={label} href={url} target="_blank" rel="noreferrer">
                <ExternalLink size={14} />
                {label}
              </a>
            ))}
          </div>
        ) : null}

        {relatedRanking.length > 0 ? (
          <div className="compact-ranking-grid">
            {relatedRanking.map((artist) => (
              <ArtistCard key={artist.slug} artist={artist} isSelected={artist.slug === prediction?.slug} onSelect={onArtistSelect} />
            ))}
          </div>
        ) : (
          <EmptyPanel title="Ranking no disponible" message="Vuelve al dashboard para cargar artistas destacados." />
        )}
      </ShellCard>
    </div>
  );
}
