// Small formatting helpers used by the dashboard components.

export function number(value: unknown, fallback = '—') {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return new Intl.NumberFormat('es-ES').format(value);
}

export function score(value: unknown, fallback = '—') {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return value.toFixed(value >= 10 ? 1 : 2);
}

export function compact(value: unknown, fallback = '—') {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return new Intl.NumberFormat('es-ES', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}

export function percent(value: unknown, fallback = '—') {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return `${(value * 100).toFixed(1)}%`;
}

export function normalizedPercent(value: unknown, fallback = '—') {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return `${Math.round(value)}%`;
}

export function title(value: string | undefined | null) {
  if (!value) return 'Unknown';
  return value
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .replace(/\b\w/g, (match) => match.toUpperCase());
}
