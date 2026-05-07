// Reusable release-state skeletons.
// They keep the final MVP from looking broken while backend data is loading.
export function SkeletonPanel({ variant = 'default', rows = 4 }) {
  const rowItems = Array.from({ length: rows }, (_, index) => index);

  return (
    <div className={`skeleton-panel skeleton-panel-${variant}`.trim()} aria-label="Cargando contenido">
      <div className="skeleton-line skeleton-title" />
      <div className="skeleton-grid">
        {rowItems.map((item) => (
          <div key={item} className="skeleton-card">
            <span className="skeleton-dot" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line-short" />
          </div>
        ))}
      </div>
    </div>
  );
}
