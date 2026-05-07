// Small display helpers shared by the V2 frontend.
// They deliberately tolerate undefined values because several API sections can be empty during local seeding.

export function number(value: number | string | null | undefined, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback;
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return new Intl.NumberFormat('es-ES').format(numeric);
}

export function score(value: number | string | null | undefined, digits = 1, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback;
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return numeric.toFixed(digits).replace(/\.0$/, '');
}

export function percent(value: number | string | null | undefined, digits = 0, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback;
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${(numeric * 100).toFixed(digits).replace(/\.0$/, '')}%`;
}

export function normalizedPercent(value: number | string | null | undefined, digits = 0, fallback = '—') {
  if (value === null || value === undefined || value === '') return fallback;
  const numeric = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${Math.max(0, Math.min(100, numeric)).toFixed(digits).replace(/\.0$/, '')}%`;
}

export function title(value: string | null | undefined, fallback = '—') {
  if (!value) return fallback;
  return value
    .replaceAll('_', ' ')
    .replaceAll('-', ' ')
    .split(' ')
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
