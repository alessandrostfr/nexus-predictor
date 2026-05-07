import { CheckCircle2, Loader2, TriangleAlert } from 'lucide-react';

// Connection status component shared by every data-heavy page.
export function ConnectionBanner({ isLoading, error, partialErrors = [] }) {
  const hasPartialErrors = partialErrors.length > 0;

  if (isLoading) {
    return (
      <aside className="connection-banner connection-banner-loading" role="status" aria-live="polite">
        <Loader2 className="spin" size={17} />
        Cargando datos reales del backend...
      </aside>
    );
  }

  if (error) {
    return (
      <aside className="connection-banner connection-banner-error" role="alert">
        <TriangleAlert size={17} />
        No se pudo conectar con la API: {error}
      </aside>
    );
  }

  return (
    <aside className={hasPartialErrors ? 'connection-banner connection-banner-warning' : 'connection-banner'} role="status" aria-live="polite">
      {hasPartialErrors ? <TriangleAlert size={17} /> : <CheckCircle2 size={17} />}
      {hasPartialErrors ? 'App conectada con avisos parciales.' : 'Backend conectado · datos actualizados.'}
      {hasPartialErrors ? <small>{partialErrors.join(' · ')}</small> : null}
    </aside>
  );
}
