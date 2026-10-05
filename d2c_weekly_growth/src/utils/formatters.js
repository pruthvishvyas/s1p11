export const CURRENCY = '\u20b9';

const nf = (d) => new Intl.NumberFormat('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

export const isNum = (v) => typeof v === 'number' && isFinite(v);
export const toNum = (v) => {
  const n = typeof v === 'string' ? parseFloat(v) : v;
  return isNum(n) ? n : null;
};
export const fmtCurrency = (v) => (isNum(v) ? (v < 0 ? '-' : '') + CURRENCY + nf(0).format(Math.abs(v)) : '-');
export const fmtRatio = (v) => (isNum(v) ? nf(2).format(v) : '-');
export const fmtPercent = (v) => (isNum(v) ? nf(1).format(v) + '%' : '-');
export const fmtNumber = (v, d = 0) => (isNum(v) ? nf(d).format(v) : '-');

export function fmtValue(kind, v) {
  switch (kind) {
    case 'currency': return fmtCurrency(v);
    case 'percent': return fmtPercent(v);
    case 'ratio': return fmtRatio(v);
    case 'number1': return fmtNumber(v, 1);
    default: return fmtNumber(v, 0);
  }
}

export function pick(obj, ...keys) {
  if (!obj || typeof obj !== 'object') return undefined;
  for (const k of keys) {
    if (obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
}

export function asList(d, ...keys) {
  if (Array.isArray(d)) return d;
  if (d && typeof d === 'object') {
    for (const k of keys) if (Array.isArray(d[k])) return d[k];
  }
  return [];
}

export const humanize = (s) => String(s).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
export const SEV_RANK = { HIGH: 0, MEDIUM: 1, LOW: 2 };
export const sevOf = (o) => String(pick(o, 'severity', 'Severity', 'priority') || 'LOW').toUpperCase();

export function timeAgo(ts) {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return 'unknown';
  const hours = Math.floor((Date.now() - d.getTime()) / 3600000);
  if (hours < 1) return 'just now';
  if (hours < 48) return hours + (hours === 1 ? ' hour ago' : ' hours ago');
  return Math.floor(hours / 24) + ' days ago';
}
