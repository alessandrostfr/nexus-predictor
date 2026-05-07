import type { LucideIcon } from 'lucide-react';

export function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone = 'cyan',
}: {
  label: string;
  value: string | number;
  note: string;
  icon: LucideIcon;
  tone?: 'cyan' | 'acid' | 'violet' | 'pink' | 'orange';
}) {
  return (
    <article className={`stat-card stat-${tone}`}>
      <div className="stat-icon">
        <Icon size={18} />
      </div>
      <small>{label}</small>
      <div className="stat-value">{value}</div>
      <p className="stat-note">{note}</p>
    </article>
  );
}
