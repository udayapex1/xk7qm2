export const numberFmt = new Intl.NumberFormat('en-GB', {
  maximumFractionDigits: 1,
});
export function formatNumber(value: number | null | undefined, unit = '') {
  return value == null || !Number.isFinite(value)
    ? '—'
    : `${numberFmt.format(value)}${unit ? ` ${unit}` : ''}`;
}
export function formatBias(value: number | null | undefined) {
  return value == null || !Number.isFinite(value)
    ? '—'
    : `${value > 0 ? '+' : ''}${numberFmt.format(value)} MW`;
}
export function formatPct(value: number | null | undefined) {
  return value == null || !Number.isFinite(value)
    ? '—'
    : `${numberFmt.format(value)}%`;
}
export function formatTime(value: string | null | undefined, withUtc = false) {
  if (!value) return '—';
  const d = new Date(value);
  return `${new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/London', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short', hourCycle: 'h23' }).format(d)} London${withUtc ? ` · UTC ${d.toISOString().slice(11, 16)}` : ''}`;
}
