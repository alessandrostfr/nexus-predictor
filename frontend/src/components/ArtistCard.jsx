import { ChevronRight, Gauge } from 'lucide-react';

function riskLabel(risk) {
  const labels = {
    very_high: 'Muy alto',
    high: 'Alto',
    medium: 'Medio',
    low: 'Bajo',
  };

  return labels[risk] ?? risk ?? '—';
}

// Ranking row/card. It is clickable so users can navigate to the artist profile.
export function ArtistCard({ artist, isSelected = false, onSelect }) {
  return (
    <button
      type="button"
      className={isSelected ? 'artist-card artist-card-active' : 'artist-card'}
      onClick={() => onSelect(artist.slug)}
    >
      <div className="artist-card-rank">#{artist.rank ?? '—'}</div>
      <div className="artist-card-main">
        <strong>{artist.name}</strong>
        <span>{artist.main_genre}</span>
        <small>{artist.performance_names?.join(' · ') || 'Performance sin nombre específico'}</small>
      </div>
      <div className="artist-card-score">
        <Gauge size={15} />
        <strong>{Math.round(artist.demand_score ?? 0)}</strong>
        <span>{riskLabel(artist.crowd_risk)}</span>
      </div>
      <ChevronRight className="artist-card-arrow" size={17} />
    </button>
  );
}
