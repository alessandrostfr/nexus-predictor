import { RefreshCw, TriangleAlert } from 'lucide-react';

// Release-ready error panel for recoverable API failures.
// The retry action is optional so it can be reused in static documentation states.
export function ErrorPanel({ title = 'No se pudo cargar esta sección', message, onRetry }) {
  return (
    <div className="error-panel" role="alert">
      <div className="error-panel-icon">
        <TriangleAlert size={20} />
      </div>
      <div>
        <strong>{title}</strong>
        {message ? <p>{message}</p> : null}
        {onRetry ? (
          <button className="secondary-action compact-action" type="button" onClick={onRetry}>
            <RefreshCw size={15} />
            Reintentar
          </button>
        ) : null}
      </div>
    </div>
  );
}
