export function pnlTextClass(value: number | null | undefined): string {
  if (value == null || value === 0) return 'text-slate-300';
  return value > 0 ? 'text-emerald-300' : 'text-rose-300';
}

export function pnlBadgeClass(value: number | null | undefined): string {
  if (value == null || value === 0) return 'bg-slate-800/70 text-slate-300 border border-slate-600/60';
  return value > 0
    ? 'bg-emerald-950/70 text-emerald-300 border border-emerald-700/60'
    : 'bg-rose-950/70 text-rose-300 border border-rose-700/60';
}

export function pnlRowClass(value: number | null | undefined): string {
  if (value == null || value === 0) return 'hover:bg-slate-800/40';
  return value > 0
    ? 'bg-emerald-950/20 hover:bg-emerald-950/40'
    : 'bg-rose-950/20 hover:bg-rose-950/40';
}

export function formatSignedPnl(value: number): string {
  const amount = Math.abs(value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}₹${amount}`;
}

export function formatSignedPercent(value: number): string {
  return `${value > 0 ? '+' : value < 0 ? '−' : ''}${Math.abs(value).toFixed(2)}%`;
}
