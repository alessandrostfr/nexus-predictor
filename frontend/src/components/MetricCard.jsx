// Compact metric card. Values can be real API data or clear placeholders.
export function MetricCard({ icon: Icon, label, value, description, tone = 'default' }) {
  return (
    <article className={`metric-card metric-card-${tone}`}>
      <div className="metric-card-icon">{Icon ? <Icon size={19} /> : null}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {description ? <p>{description}</p> : null}
      </div>
    </article>
  );
}
