import { CircleDashed } from 'lucide-react';

// Friendly empty state for missing API, missing enrichment or empty filters.
export function EmptyPanel({ title = 'Sin datos disponibles', message }) {
  return (
    <div className="empty-panel">
      <CircleDashed size={20} />
      <strong>{title}</strong>
      {message ? <p>{message}</p> : null}
    </div>
  );
}
