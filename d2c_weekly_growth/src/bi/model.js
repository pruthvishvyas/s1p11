// Pure data logic for the Explorer (no React). Tested with plain Node.
const day = (v) => String(v).slice(0, 10);
const num = (v) => (typeof v === 'number' && isFinite(v) ? v : null);
const pad = (n) => String(n).padStart(2, '0');

export const LEVELS = ['year', 'quarter', 'month', 'week'];
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const EMPTY_FILTERS = { from: '', to: '', years: [], quarters: [], months: [], segments: [], unusual: false, lossOnly: false };

// agg: sum | avg | last | ratio (sum(num)/sum(den)*mult) | count
export const METRICS = {
  net_revenue: { label: 'Net Revenue', fmt: 'currency', agg: 'sum', f: 'net_revenue', better: 'up' },
  net_profit: { label: 'Net Profit', fmt: 'currency', agg: 'sum', f: 'net_profit', better: 'up' },
  total_spend: { label: 'Marketing spend', fmt: 'currency', agg: 'sum', f: 'total_spend', better: 'neutral' },
  net_margin: { label: 'Net Margin %', fmt: 'percent', agg: 'ratio', num: 'net_profit', den: 'net_revenue', mult: 100, better: 'up' },
  rev_per_spend: { label: 'Net Revenue per \u20b91 of spend', fmt: 'ratio', agg: 'ratio', num: 'net_revenue', den: 'total_spend', mult: 1, better: 'up' },
  loss_weeks: { label: 'Loss-making weeks', fmt: 'number', agg: 'count', pred: (r) => r.loss === true, better: 'down' },
  cash_balance: { label: 'Cash balance (latest week)', fmt: 'currency', agg: 'last', f: 'cash_balance', better: 'up' },
  ar_outstanding: { label: 'Receivables outstanding (latest week)', fmt: 'currency', agg: 'last', f: 'ar_outstanding', better: 'down' },
  dso_days: { label: 'DSO, days (average)', fmt: 'number1', agg: 'avg', f: 'dso_days', better: 'down' },
  ltv_to_cac: { label: 'LTV to CAC (average)', fmt: 'ratio', agg: 'avg', f: 'ltv_to_cac', better: 'up' },
  cac: { label: 'CAC (average)', fmt: 'currency', agg: 'avg', f: 'cac', better: 'down' },
  weeks: { label: 'Weeks in view', fmt: 'number', agg: 'count', better: 'neutral' },
};

export function addChannelMetrics(channels, isShare) {
  channels.forEach((c) => {
    METRICS['spend_' + c] = isShare
      ? { label: c + ' share of spend %', fmt: 'percent', agg: 'avg', f: 'spend_' + c, better: 'neutral' }
      : { label: c + ' spend', fmt: 'currency', agg: 'sum', f: 'spend_' + c, better: 'neutral' };
  });
}

function colMap(c) {
  const m = {};
  if (!c || !Array.isArray(c.x)) return m;
  const names = Object.keys(c.series || {}).filter((k) => Array.isArray(c.series[k]));
  c.x.forEach((x, i) => {
    const o = (m[day(x)] = m[day(x)] || {});
    names.forEach((n) => { o[n] = num(c.series[n][i]); });
  });
  return m;
}

// Joins the column-oriented chart files into one weekly table.
export function buildWeekly({ growth, mix, cash, ltv, segs, anomalies }) {
  const g = colMap(growth);
  const mx = colMap(mix);
  const cs = colMap(cash);
  const lc = colMap(ltv);
  const segBy = {};
  (segs || []).forEach((a) => { segBy[day(a.Week_Start)] = String(a.segment_tier ?? a.segment); });
  const anom = new Set((anomalies || []).map((a) => day(a.Week_Start)));
  const channels = mix && mix.series ? Object.keys(mix.series).filter((k) => Array.isArray(mix.series[k])) : [];
  const dates = Object.keys(g).sort();

  // Detect whether channel_mix holds money or percentage shares (weekly totals of ~100 or ~1).
  const sums = dates.map((d) => channels.reduce((a, c) => a + (((mx[d] || {})[c]) || 0), 0)).filter((s) => s > 0).sort((a, b) => a - b);
  const med = sums.length ? sums[Math.floor(sums.length / 2)] : 0;
  let mixIsShare = false;
  let scale = 1;
  if (med >= 99 && med <= 101) mixIsShare = true;
  else if (med >= 0.99 && med <= 1.01) { mixIsShare = true; scale = 100; }
  addChannelMetrics(channels, mixIsShare);

  const rows = dates.map((d) => {
    const r = { date: d, year: Number(d.slice(0, 4)), month: Number(d.slice(5, 7)) };
    r.quarter = Math.ceil(r.month / 3);
    r.net_revenue = g[d].net_revenue ?? null;
    r.net_profit = g[d].net_profit ?? null;
    let tot = null;
    channels.forEach((c) => {
      const v = (mx[d] || {})[c];
      r['spend_' + c] = v === null || v === undefined ? null : v * scale;
      if (r['spend_' + c] !== null) tot = (tot || 0) + r['spend_' + c];
    });
    r.total_spend = mixIsShare ? null : tot;
    r.cash_balance = (cs[d] || {}).cash_balance ?? null;
    r.ar_outstanding = (cs[d] || {}).ar_outstanding ?? null;
    r.dso_days = (cs[d] || {}).dso_days ?? null;
    r.ltv_to_cac = (lc[d] || {}).ltv_to_cac ?? null;
    r.cac = (lc[d] || {}).cac ?? null;
    r.segment = segBy[d] || 'Unassigned';
    r.unusual = anom.has(d);
    r.loss = r.net_profit !== null && r.net_profit < 0;
    return r;
  });
  return { rows, channels, mixIsShare };
}

export function applyFilters(rows, f, skip = []) {
  const s = (k) => skip.includes(k);
  return rows.filter((r) =>
    (s('date') || ((!f.from || r.date >= f.from) && (!f.to || r.date <= f.to))) &&
    (s('years') || !f.years.length || f.years.includes(r.year)) &&
    (s('quarters') || !f.quarters.length || f.quarters.includes(r.quarter)) &&
    (s('months') || !f.months.length || f.months.includes(r.month)) &&
    (s('segments') || !f.segments.length || f.segments.includes(r.segment)) &&
    (!f.unusual || r.unusual) && (!f.lossOnly || r.loss));
}

const present = (v) => v !== null && v !== undefined;

export function aggregate(rows, key) {
  const m = METRICS[key];
  if (!m || !rows.length) return null;
  switch (m.agg) {
    case 'sum': {
      const v = rows.map((r) => r[m.f]).filter(present);
      return v.length ? v.reduce((a, b) => a + b, 0) : null;
    }
    case 'avg': {
      const v = rows.map((r) => r[m.f]).filter(present);
      return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
    }
    case 'last': {
      for (let i = rows.length - 1; i >= 0; i -= 1) if (present(rows[i][m.f])) return rows[i][m.f];
      return null;
    }
    case 'ratio': {
      let n = 0;
      let d = 0;
      rows.forEach((r) => { if (present(r[m.num]) && present(r[m.den])) { n += r[m.num]; d += r[m.den]; } });
      return d ? (n / d) * m.mult : null;
    }
    case 'count': return rows.filter(m.pred || (() => true)).length;
    default: return null;
  }
}

// For comparing groups of different size: sums become "average per week".
export function perWeek(rows, key) {
  const m = METRICS[key];
  if (m && m.agg === 'sum') {
    const v = aggregate(rows, key);
    return v === null || !rows.length ? null : v / rows.length;
  }
  return aggregate(rows, key);
}

// One weekly value (used by the scatter and the table).
export function rowValue(r, key) {
  const m = METRICS[key];
  if (!m) return null;
  if (m.agg === 'ratio') return present(r[m.num]) && present(r[m.den]) && r[m.den] !== 0 ? (r[m.num] / r[m.den]) * m.mult : null;
  if (m.agg === 'count') return m.pred ? (m.pred(r) ? 1 : 0) : 1;
  return present(r[m.f]) ? r[m.f] : null;
}

const KEY = {
  year: (r) => String(r.year),
  quarter: (r) => r.year + '-Q' + r.quarter,
  month: (r) => r.year + '-' + pad(r.month),
  week: (r) => r.date,
};

export function groupBy(rows, level) {
  const out = [];
  const idx = {};
  rows.forEach((r) => {
    const k = KEY[level](r);
    if (idx[k] === undefined) { idx[k] = out.length; out.push({ key: k, rows: [] }); }
    out[idx[k]].rows.push(r);
  });
  return out;
}

export function delta(m, cur, prev) {
  if (cur === null || prev === null || cur === undefined || prev === undefined) return null;
  if (m.fmt === 'percent') return { value: cur - prev, unit: 'pp' };
  if (prev === 0) return null;
  return { value: ((cur - prev) / Math.abs(prev)) * 100, unit: '%' };
}

export function pearson(pts) {
  const n = pts.length;
  if (n < 3) return null;
  const mx = pts.reduce((a, p) => a + p.x, 0) / n;
  const my = pts.reduce((a, p) => a + p.y, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  pts.forEach((p) => { sxy += (p.x - mx) * (p.y - my); sxx += (p.x - mx) ** 2; syy += (p.y - my) ** 2; });
  return sxx === 0 || syy === 0 ? null : sxy / Math.sqrt(sxx * syy);
}

export function toCsv(rows, cols) {
  const esc = (v) => {
    if (v === null || v === undefined) return '';
    const s = String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  return [cols.join(',')].concat(rows.map((r) => cols.map((c) => esc(r[c])).join(','))).join('\n');
}
