import { CheckCircle2, Loader2, TriangleAlert } from 'lucide-react';

// Connection status component shared by every shell page.
export function ConnectionBanner({ isLoading, error, partialErrors = [] }) {
  const hasPartialErrors = partialErrors.length > 0;

  if (isLoading) {
    return (
      <section className="connection-banner connection-banner-loading">
        <Loader2 className="spin" size={18} />
        <div>
          <strong>Conectando con la API</strong>
          <span>Estamos cargando salud, ediciones, géneros y predicciones.</span>
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="connection-banner connection-banner-error">
        <TriangleAlert size={18} />
        <div>
          <strong>API no disponible</strong>
          <span>{error}</span>
        </div>
      </section>
    );
  }

  return (
    <section className={hasPartialErrors ? 'connection-banner connection-banner-warning' : 'connection-banner'}>
      {hasPartialErrors ? <TriangleAlert size={18} /> : <CheckCircle2 size={18} />}
      <div>
        <strong>{hasPartialErrors ? 'API conectada con avisos' : 'API conectada'}</strong>
        <span>
          {hasPartialErrors
            ? 'La shell sigue funcionando aunque algún endpoint secundario haya fallado.'
            : 'Backend y frontend están comunicando correctamente.'}
        </span>
      </div>
    </section>
  );
}
