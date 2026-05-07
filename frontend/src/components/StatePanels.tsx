export function LoadingPanel({ label = 'Cargando datos V2...' }: { label?: string }) {
  return (
    <div className="loading-panel">
      <span className="loading-orb" />
      {label}
    </div>
  );
}

export function ErrorPanel({ message }: { message: string }) {
  return <div className="error-panel">{message}</div>;
}

export function EmptyPanel({ label = 'No hay datos para mostrar todavía.' }: { label?: string }) {
  return <div className="status-panel">{label}</div>;
}
