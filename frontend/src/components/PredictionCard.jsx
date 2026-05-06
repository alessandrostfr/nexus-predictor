import { Gauge, TrendingUp } from 'lucide-react';

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '—';
  }

  return new Intl.NumberFormat('es-ES').format(value);
}

// Attendance prediction summary. It keeps low/mid/high values explicit.
export function PredictionCard({ prediction }) {
  const attendance = prediction?.attendance;

  if (!attendance) {
    return (
      <article className="prediction-card prediction-card-empty">
        <Gauge size={20} />
        <strong>Predicción no disponible</strong>
        <p>Este año todavía no tiene snapshot predictivo.</p>
      </article>
    );
  }

  return (
    <article className="prediction-card">
      <div className="prediction-card-header">
        <span>
          <TrendingUp size={17} />
          Asistencia estimada
        </span>
        <strong>{attendance.confidence}</strong>
      </div>
      <div className="prediction-main-value">{formatNumber(attendance.predicted_mid)}</div>
      <div className="prediction-range">
        <span>Bajo {formatNumber(attendance.predicted_low)}</span>
        <span>Alto {formatNumber(attendance.predicted_high)}</span>
      </div>
      <p>{attendance.notes?.[0] ?? 'Predicción interpretable basada en histórico y fuerza del cartel.'}</p>
    </article>
  );
}
