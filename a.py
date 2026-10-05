#!/usr/bin/env python3
"""add_manual_and_bi.py - adds (1) an in-app User Manual with per-page help and (2) an interactive
Power BI-style Explorer. Run from the folder that contains frontend_contract.json:  python add_manual_and_bi.py"""
import json, os

PKG = "d2c_weekly_growth"
if os.path.exists("frontend_contract.json"):
    with open("frontend_contract.json", encoding="utf-8") as f:
        PKG = json.load(f)["project"]["client_id"]
if not os.path.isdir(os.path.join(PKG, "src")):
    raise SystemExit("Folder %s/src not found. Run this from the folder that contains it." % PKG)
for need in ("src/hooks/useKPIs.js", "src/hooks/useSegments.js", "src/components/shared/Header.jsx"):
    if not os.path.isfile(os.path.join(PKG, need)):
        raise SystemExit("Missing %s - run apply_fixes.py first." % need)

def w(rel, text):
    full = os.path.join(PKG, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.strip("\n") + "\n")

w("src/bi/model.js", r'''
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
''')

w("src/hooks/useWeekly.js", r'''
import { useEffect, useState } from 'react';
import { fetchJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { buildWeekly } from '../bi/model';

// Joins the pipeline chart files into one weekly table for the Explorer.
export default function useWeekly() {
  const [st, setSt] = useState({ rows: [], channels: [], mixIsShare: false, loading: true, missing: [] });
  useEffect(() => {
    let off = false;
    (async () => {
      const get = async (u) => { try { return await fetchJson(u); } catch (e) { return null; } };
      const [growth, mix, cash, ltv, segs, an] = await Promise.all([
        get(DATA.charts + 'growth_vs_profit.json'), get(DATA.charts + 'channel_mix.json'),
        get(DATA.charts + 'cash_safety.json'), get(DATA.charts + 'ltv_cac.json'),
        get(DATA.segments), get(DATA.anomalies),
      ]);
      const missing = [['growth_vs_profit', growth], ['channel_mix', mix], ['cash_safety', cash], ['ltv_cac', ltv], ['segments', segs], ['anomalies', an]]
        .filter((p) => !p[1]).map((p) => p[0]);
      const out = buildWeekly({
        growth, mix, cash, ltv,
        segs: segs && segs.assignments,
        anomalies: an && (Array.isArray(an) ? an : an.items),
      });
      if (!off) setSt({ ...out, loading: false, missing });
    })();
    return () => { off = true; };
  }, []);
  return st;
}
''')

w("src/utils/extraTabs.js", r'''
export const EXTRA_OUTCOMES = [
  { id: 'explore', label: 'EXPLORE' },
  { id: 'help', label: 'HELP' },
];
export const EXTRA_TABS = [
  { outcome: 'explore', key: 'explorer', label: 'Interactive Explorer', component: 'Explorer' },
  { outcome: 'help', key: 'manual', label: 'User Manual', component: 'Manual' },
];
''')

w("src/manual/content.js", r'''
// All manual text lives here so it can be edited without touching any component.
export const TAB_HELP = {
  kpis: {
    what: 'The headline numbers for your latest week: revenue, profit, advertising efficiency, customer acquisition and cash.',
    read: 'Each card shows the value and how it changed versus the prior period. A green triangle up is an improvement and a red triangle down is a decline (for CAC and DSO, lower is better, so a fall is shown in green). An orange card means one of your limits has been crossed.',
    act: 'Start here every week. If a card is orange, open Profit & Spend Charts or What\'s Happening to find out why.',
  },
  charts: {
    what: 'Seven charts that answer: Is the business growing profitably? Where does marketing money go? Is customer acquisition paying back? Is cash safe? Do promo weeks make money? Which months are strongest? Which channel\'s spend moves results most?',
    read: 'Dashed red lines are limits. On the cash chart and the LTV to CAC chart, the ratio or days line uses the right-hand axis. The channel chart compares spend with results over time; it shows association, not proof of cause.',
    act: 'Use Week Types to show only one type of week on the time charts. For deeper slicing, use the Interactive Explorer.',
  },
  anomalies: {
    what: 'Weeks whose combination of numbers looked unusual compared with the rest of your history.',
    read: 'The reason column explains which numbers stood out. An unusual week can be good (a record week) or bad (a loss). Click a column title to sort.',
    act: 'Check whether each flagged week had a real cause (a sale, stock-out, billing delay) or a data problem.',
  },
  segments: {
    what: 'Your weeks grouped automatically into a few types based on how they performed (margin, ROAS, CAC, discounting and so on).',
    read: 'Each card summarises one type of week: how many weeks, average margin, ROAS, CAC and profit. Comparing cards shows what separates your best weeks from your worst.',
    act: 'Click a card to filter the time charts to that type. Click it again to clear the filter.',
  },
  insights: {
    what: 'Plain-language findings from the analysis, each with the evidence behind it and a suggested action.',
    read: 'The coloured label shows importance: HIGH needs attention first, then MEDIUM, then LOW. Use the category buttons to narrow the list.',
    act: 'Work through HIGH items first. The yellow box on each card is the suggested next step.',
  },
  recommendations: {
    what: 'Specific actions ranked by priority, each with its evidence and the rule that triggered it, plus a channel-priority table.',
    read: 'The channel table compares each channel\'s recent share of spend with its peers and shows whether extra spend is still giving a good extra return (saturation).',
    act: 'Press Mark done when an action is finished. Completed actions are saved in this browser only and can be undone.',
  },
  simulations: {
    what: 'Pre-calculated what-if estimates: how profit may change if you change promo discount depth, total marketing spend, or move budget between channels.',
    read: 'Moving a slider compares that choice with your current position. A yellow warning means the choice is outside what your history has seen, so the estimate is rougher. These are estimates, not promises.',
    act: 'Use them to compare options before committing budget, then confirm with a small real-world test.',
  },
  goals: {
    what: 'Your weekly profit and revenue targets.',
    read: 'The bar shows the latest week against the target: On track at 100% or more, At risk from 80%, Behind below 80%.',
    act: 'Type your targets in the boxes. They are saved in this browser only, so set them again on a different computer.',
  },
  forecast: {
    what: 'A 13-week outlook for Net Revenue and Net Profit, built from your history.',
    read: 'The solid line is what happened, the dashed line is the forecast, and the shaded band is the 80% range: results are expected to land inside it roughly 8 times out of 10. The table lists every forecast week with its range.',
    act: 'Plan around the range, not just the middle line. Use the toggle to switch between revenue and profit, and Run forecast to read a single week.',
  },
  goal_progress: {
    what: 'How the latest week and the 4-week average compare with your targets and limits for profit, revenue, cash runway and LTV to CAC.',
    read: 'Each card shows the latest value, the target, a progress bar and a status label.',
    act: 'Anything red or orange deserves attention this week. Targets for profit and revenue come from My Targets.',
  },
  alerts: {
    what: 'Warnings raised when a monitored limit is crossed, such as a sharp revenue drop or low cash.',
    read: 'No active alerts means every monitored rule is currently satisfied. The history table lists previous pipeline runs.',
    act: 'Open an active alert, read its message, then check the related page. Your own alert thresholds are saved in this browser.',
  },
  explorer: {
    what: 'An interactive workspace for slicing your weekly data any way you like, similar to a BI tool.',
    read: 'Every number and chart on this page responds to the filters at the top. The small line under each number shows the change versus the previous equal-length period.',
    act: 'Click bars to drill down or filter, change the measure, and download the filtered weeks as a spreadsheet. See the User Manual for a walkthrough.',
  },
};

export const QUICK_START = [
  'Open This Week\'s Numbers. Look for orange cards: they are your limits being crossed.',
  'Open What\'s Happening and read the HIGH items first.',
  'Open This Quarter\'s Actions and pick the actions to do. Press Mark done as you finish them.',
  'Open 13-Week Outlook to see what the coming weeks may look like, including the range.',
  'Use the Interactive Explorer whenever you want to dig into a period, a week type or a channel.',
];

export const EXPLORER_STEPS = [
  'Slicers (top): choose a date range, years, quarters, months, week types, only unusual weeks, or only loss-making weeks. Filters combine, and "Showing X of Y weeks" tells you how many weeks match.',
  'Number cards: totals and ratios for the weeks you selected, with the change versus the previous period of the same length. The comparison is hidden when it cannot be made fairly (for example when a year or month slicer is on).',
  'Main chart: pick a measure, and optionally a second measure as a line. Click a bar to drill down one level: Year, then Quarter, then Month, then Week. Use the Up button to go back.',
  'Week type and month charts: click a bar to filter everything to it, click again to clear. Other bars stay visible but faded, so you can still compare.',
  'Relationship chart: pick any two measures to see each week as a dot, coloured by week type. The r value shows how closely they move together. It does not prove one causes the other.',
  'Table: click a column title to sort, use Previous/Next to page, and Download CSV to take the filtered weeks into Excel.',
  'Reset all filters clears everything and returns to the full history.',
];

export const EXPLORER_EXAMPLE = 'Example: why was a quarter weak? Click that year, then that quarter in the main chart, set the measure to Net Profit, then sort the table by Net Profit (low to high) to see the worst weeks and their week types.';

export const GLOSSARY = [
  ['Net Revenue', 'Sales revenue kept after deductions such as discounts and returns, as defined in your data pipeline.'],
  ['Net Profit', 'What is left of Net Revenue after the costs counted by the pipeline, including product and marketing costs.'],
  ['Net Margin %', 'Net Profit divided by Net Revenue, times 100. In the Explorer it is calculated from totals, not by averaging weekly percentages.'],
  ['Gross Margin %', 'Share of revenue left after the direct cost of the products sold.'],
  ['ROAS (return on ad spend)', 'Revenue generated per 1 of advertising spend. Below the break-even level shown on the Numbers page, advertising is not paying for itself.'],
  ['CAC (customer acquisition cost)', 'Average marketing cost of winning one new customer. Lower is better.'],
  ['LTV (lifetime value)', 'The value a customer is expected to bring over the whole relationship.'],
  ['LTV to CAC', 'Lifetime value divided by acquisition cost. Higher is better; your minimum is shown under Your current limits below.'],
  ['DSO (days sales outstanding)', 'Average number of days it takes to collect payment after a sale. Lower is better.'],
  ['Receivables (AR outstanding)', 'Money customers owe you but have not yet paid.'],
  ['Cash runway (weeks)', 'How many weeks your cash would last at the current rate of spending. Your minimum is shown under Your current limits.'],
  ['Discount rate %', 'The share of revenue given away in discounts.'],
  ['Return rate %', 'The share of orders or revenue that comes back as returns.'],
  ['Conversion rate %', 'The share of visits that become orders.'],
  ['Marketing % of revenue', 'Marketing spend as a share of Net Revenue.'],
  ['Loss-making week', 'A week in which Net Profit was below zero.'],
  ['Week type (segment)', 'A group of weeks that performed similarly. The grouping is found automatically from the numbers.'],
  ['Unusual week (anomaly)', 'A week whose combination of numbers differs from your normal pattern. It is a prompt to look closer, not automatically a problem.'],
  ['80% range', 'The band around a forecast in which the result is expected to fall about 8 times out of 10.'],
  ['Saturation', 'When extra spend on a channel brings smaller and smaller extra results.'],
  ['Marginal return', 'The extra result gained from one more unit of spend on a channel.'],
  ['Lag (for example "Search, lag 2w")', 'Looks at whether this week\'s spend lines up with results a number of weeks later.'],
  ['Pre-computed what-if', 'An estimate prepared in advance from your history, shown instantly when you move a slider.'],
  ['r (correlation)', 'A number from -1 to +1 showing how closely two measures move together. Near 0 means no clear link. It never proves cause and effect.'],
];

export const FAQ = [
  ['A page says "Run main.py to generate your data".', 'The analysis files for that page are missing or could not be read. Ask your administrator to run the analysis pipeline and refresh the data, then reload this page.'],
  ['The numbers look old.', 'The dashboard shows the results of the most recent pipeline run. It does not update on its own between runs. "Last updated" at the top shows when the data was refreshed, when available.'],
  ['Why does the forecast show a range?', 'Nobody can predict the future exactly. The shaded 80% range shows how much results may reasonably vary. Plan for the range.'],
  ['Why does a what-if show a warning?', 'The choice is outside what your history has seen. The estimate is then less reliable.'],
  ['My targets or "Mark done" ticks disappeared.', 'They are stored in the web browser you used. A different browser, a different computer, or cleared browser data starts fresh.'],
  ['Why do some Explorer comparisons say "-"?', 'A fair comparison needs a full previous period of the same length. When a year, quarter or month slicer is on, or when you view the whole history, there is nothing fair to compare against.'],
  ['How are CAC, LTV to CAC and DSO combined over several weeks?', 'As a simple average of the weekly values. Cash and receivables show the latest week in view. Revenue, profit and spend are summed.'],
  ['Can I trust the channel and what-if numbers as exact?', 'Treat them as informed estimates. They are based on past patterns, and patterns can change.'],
];

export const ACCURACY_NOTES = [
  'Forecasts, what-if results and channel comparisons are estimates built from historical patterns. They guide decisions; they do not guarantee outcomes.',
  'Two measures moving together (correlation) does not prove one causes the other.',
  'Explorer totals are sums of weekly values. Ratios such as Net Margin % are computed from those totals.',
  'Definitions follow your analysis pipeline. If you are unsure of an exact definition, ask the person who set up the analysis.',
];
''')

w("src/components/explore/Explorer.jsx", r'''
import { useMemo, useState } from 'react';
import useWeekly from '../../hooks/useWeekly';
import EmptyState from '../shared/EmptyState';
import { fmtValue, isNum } from '../../utils/formatters';
import {
  LEVELS, METRICS, MONTHS, EMPTY_FILTERS, aggregate, applyFilters, groupBy, perWeek, rowValue, pearson, delta, toCsv,
} from '../../bi/model';
import {
  ResponsiveContainer, ComposedChart, BarChart, Bar, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid, Cell,
  ScatterChart, Scatter,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;
const color = (i) => cssVar('--chart-' + ((i % 6) + 1));
const compact = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 });
const axisFmt = (kind) => (v) => {
  if (!isNum(v)) return '';
  if (kind === 'currency') return '\u20b9' + compact.format(v);
  if (kind === 'percent') return compact.format(v) + '%';
  return compact.format(v);
};
const LEVEL_LABEL = { year: 'Year', quarter: 'Quarter', month: 'Month', week: 'Week' };
const KPI_KEYS = ['net_revenue', 'net_profit', 'net_margin', 'total_spend', 'rev_per_spend', 'loss_weeks', 'cash_balance', 'ltv_to_cac', 'cac', 'dso_days'];
const TABLE_COLS = [
  ['date', 'Week'], ['segment', 'Week type'], ['net_revenue', 'Net Revenue'], ['net_profit', 'Net Profit'],
  ['net_margin', 'Net Margin %'], ['total_spend', 'Spend'], ['rev_per_spend', 'Net Rev / Spend'],
  ['cash_balance', 'Cash'], ['cac', 'CAC'], ['ltv_to_cac', 'LTV:CAC'], ['unusual', 'Unusual'],
];
const PAGE = 15;

const Chip = ({ on, onClick, children }) => (
  <button className={'chip' + (on ? ' on' : '')} onClick={onClick}>{children}</button>
);

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function Explorer() {
  const { rows, channels, mixIsShare, loading, missing } = useWeekly();
  const [f, setF] = useState(EMPTY_FILTERS);
  const [level, setLevel] = useState('year');
  const [metric, setMetric] = useState('net_profit');
  const [overlay, setOverlay] = useState('net_revenue');
  const [sx, setSx] = useState('total_spend');
  const [sy, setSy] = useState('net_profit');
  const [sort, setSort] = useState({ key: 'date', dir: 'desc' });
  const [page, setPage] = useState(0);

  const upd = (fn) => { setF(fn); setPage(0); };
  const toggle = (field, v) => upd((p) => ({ ...p, [field]: p[field].includes(v) ? p[field].filter((x) => x !== v) : [...p[field], v] }));

  const years = useMemo(() => [...new Set(rows.map((r) => r.year))].sort(), [rows]);
  const segNames = useMemo(() => [...new Set(rows.map((r) => r.segment))].sort(), [rows]);
  const available = useMemo(
    () => Object.keys(METRICS).filter((k) => k === 'weeks' || k === 'loss_weeks' || aggregate(rows, k) !== null),
    [rows, channels, mixIsShare]); // eslint-disable-line react-hooks/exhaustive-deps
  const chartMetrics = available.filter((k) => k !== 'weeks');
  const scatterMetrics = available.filter((k) => METRICS[k].agg !== 'count');

  const sel = useMemo(() => applyFilters(rows, f), [rows, f]);
  const calendarOn = f.years.length > 0 || f.quarters.length > 0 || f.months.length > 0;
  const prevRows = useMemo(() => {
    if (!sel.length || calendarOn) return null;
    const base = applyFilters(rows, f, ['date', 'years', 'quarters', 'months']);
    const before = base.filter((r) => r.date < sel[0].date).slice(-sel.length);
    return before.length === sel.length ? before : null;
  }, [rows, f, sel, calendarOn]);

  const M = METRICS[metric] || METRICS.net_profit;
  const O = overlay && overlay !== metric ? METRICS[overlay] : null;

  const trend = useMemo(() => groupBy(sel, level).map((g) => ({
    key: g.key, v: aggregate(g.rows, metric), o: O ? aggregate(g.rows, overlay) : null,
  })), [sel, level, metric, overlay]); // eslint-disable-line react-hooks/exhaustive-deps
  const mix = useMemo(() => groupBy(sel, level).map((g) => {
    const o = { key: g.key };
    channels.forEach((c) => { o[c] = aggregate(g.rows, 'spend_' + c); });
    return o;
  }), [sel, level, channels]);
  const segData = useMemo(() => {
    const base = applyFilters(rows, f, ['segments']);
    return segNames.map((s) => {
      const rs = base.filter((r) => r.segment === s);
      return { name: s, v: perWeek(rs, metric), n: rs.length };
    }).filter((d) => d.n > 0);
  }, [rows, f, segNames, metric]);
  const monData = useMemo(() => {
    const base = applyFilters(rows, f, ['months']);
    return MONTHS.map((m, i) => {
      const rs = base.filter((r) => r.month === i + 1);
      return { name: m, month: i + 1, v: perWeek(rs, metric), n: rs.length };
    }).filter((d) => d.n > 0);
  }, [rows, f, metric]);
  const pts = useMemo(() => sel.map((r) => ({ date: r.date, segment: r.segment, x: rowValue(r, sx), y: rowValue(r, sy) }))
    .filter((p) => p.x !== null && p.y !== null), [sel, sx, sy]);
  const corr = pearson(pts);

  const sorted = useMemo(() => {
    const val = (r) => (['date', 'segment', 'unusual'].includes(sort.key) ? r[sort.key] : rowValue(r, sort.key));
    const a = [...sel];
    const dir = sort.dir === 'asc' ? 1 : -1;
    a.sort((p, q) => {
      const x = val(p);
      const y = val(q);
      if (x === null || x === undefined) return 1;
      if (y === null || y === undefined) return -1;
      return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y))) * dir;
    });
    return a;
  }, [sel, sort]);

  if (loading) return <div className="note">Loading...</div>;
  if (!rows.length) return <EmptyState message="No weekly data found. Run the pipeline and sync the data first." />;

  const perWeekNote = M.agg === 'sum' ? ' (average per week)' : '';
  const pages = Math.max(1, Math.ceil(sorted.length / PAGE));
  const view = sorted.slice(page * PAGE, page * PAGE + PAGE);
  const dates = rows.map((r) => r.date);

  const drill = (key) => {
    if (!key) return;
    const y = Number(String(key).slice(0, 4));
    if (level === 'year') upd((p) => ({ ...p, years: [y] }));
    else if (level === 'quarter') upd((p) => ({ ...p, years: [y], quarters: [Number(String(key).slice(-1))] }));
    else if (level === 'month') upd((p) => ({ ...p, years: [y], months: [Number(String(key).slice(5, 7))] }));
    else return;
    setLevel(LEVELS[LEVELS.indexOf(level) + 1]);
  };
  const up = () => {
    const clears = { quarter: 'years', month: 'quarters', week: 'months' };
    if (!clears[level]) return;
    upd((p) => ({ ...p, [clears[level]]: [] }));
    setLevel(LEVELS[LEVELS.indexOf(level) - 1]);
  };
  const reset = () => { setF(EMPTY_FILTERS); setLevel('year'); setPage(0); };
  const keyOf = (d) => d && (d.key !== undefined ? d.key : d.payload && d.payload.key);

  const active = [];
  if (f.from || f.to) active.push(['Dates ' + (f.from || 'start') + ' to ' + (f.to || 'end'), () => upd((p) => ({ ...p, from: '', to: '' }))]);
  f.years.forEach((y) => active.push(['Year ' + y, () => toggle('years', y)]));
  f.quarters.forEach((q) => active.push(['Q' + q, () => toggle('quarters', q)]));
  f.months.forEach((m) => active.push([MONTHS[m - 1], () => toggle('months', m)]));
  f.segments.forEach((s) => active.push(['Type: ' + s, () => toggle('segments', s)]));
  if (f.unusual) active.push(['Unusual weeks only', () => upd((p) => ({ ...p, unusual: false }))]);
  if (f.lossOnly) active.push(['Loss-making weeks only', () => upd((p) => ({ ...p, lossOnly: false }))]);

  const sortBy = (key) => setSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }));
  const cell = (r, k) => {
    if (k === 'date' || k === 'segment') return r[k];
    if (k === 'unusual') return r.unusual ? 'Yes' : '';
    return fmtValue(METRICS[k].fmt, rowValue(r, k));
  };
  const tip = (kind) => (v, n) => [fmtValue(kind, v), n];

  return (
    <div>
      {missing.length > 0 && <div className="notice">Some data files could not be read ({missing.join(', ')}). Related measures will be empty.</div>}

      <div className="card chart-card">
        <div className="slicers">
          <div className="field">
            <label>From week</label>
            <select value={f.from} onChange={(e) => upd((p) => ({ ...p, from: e.target.value }))}>
              <option value="">Start</option>{dates.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div className="field">
            <label>To week</label>
            <select value={f.to} onChange={(e) => upd((p) => ({ ...p, to: e.target.value }))}>
              <option value="">End</option>{dates.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>
        <div className="muted">Year</div>
        <div className="chips">{years.map((y) => <Chip key={y} on={f.years.includes(y)} onClick={() => toggle('years', y)}>{y}</Chip>)}</div>
        <div className="muted">Quarter</div>
        <div className="chips">{[1, 2, 3, 4].map((q) => <Chip key={q} on={f.quarters.includes(q)} onClick={() => toggle('quarters', q)}>Q{q}</Chip>)}</div>
        <div className="muted">Month</div>
        <div className="chips">{MONTHS.map((m, i) => <Chip key={m} on={f.months.includes(i + 1)} onClick={() => toggle('months', i + 1)}>{m}</Chip>)}</div>
        <div className="muted">Week type</div>
        <div className="chips">{segNames.map((s) => <Chip key={s} on={f.segments.includes(s)} onClick={() => toggle('segments', s)}>{s}</Chip>)}</div>
        <div className="chips">
          <Chip on={f.unusual} onClick={() => upd((p) => ({ ...p, unusual: !p.unusual }))}>Only unusual weeks</Chip>
          <Chip on={f.lossOnly} onClick={() => upd((p) => ({ ...p, lossOnly: !p.lossOnly }))}>Only loss-making weeks</Chip>
          <button className="btn alt" onClick={reset}>Reset all filters</button>
        </div>
        <div className="muted">
          Showing {sel.length} of {rows.length} weeks
          {active.length > 0 && ' | '}
          {active.map((a, i) => <button key={i} className="chip on" style={{ marginLeft: 6 }} onClick={a[1]}>{a[0]} &times;</button>)}
        </div>
      </div>

      {!sel.length ? <div className="card"><EmptyState message="No weeks match these filters. Try removing one." /></div> : (
        <>
          <div className="grid kpis" style={{ marginBottom: 16 }}>
            {KPI_KEYS.filter((k) => available.includes(k)).map((k) => {
              const m = METRICS[k];
              const cur = aggregate(sel, k);
              const d = prevRows ? delta(m, cur, aggregate(prevRows, k)) : null;
              const good = d === null || m.better === 'neutral' ? null : (d.value >= 0) === (m.better === 'up');
              return (
                <div key={k} className="card">
                  <div className="kpi-label">{m.label}</div>
                  <div className="kpi-value">{fmtValue(m.fmt, cur)}</div>
                  <div className={good === null ? 'muted' : good ? 'up' : 'down'}>
                    {d === null ? 'no fair comparison' : (d.value >= 0 ? '\u25B2 ' : '\u25BC ') + Math.abs(d.value).toFixed(1) + (d.unit === 'pp' ? ' pts' : '%') + ' vs previous ' + sel.length + ' weeks'}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card chart-card">
            <div className="slicers">
              <div className="field">
                <label>Measure</label>
                <select value={metric} onChange={(e) => setMetric(e.target.value)}>{chartMetrics.map((k) => <option key={k} value={k}>{METRICS[k].label}</option>)}</select>
              </div>
              <div className="field">
                <label>Overlay line</label>
                <select value={overlay} onChange={(e) => setOverlay(e.target.value)}>
                  <option value="">None</option>{chartMetrics.map((k) => <option key={k} value={k}>{METRICS[k].label}</option>)}
                </select>
              </div>
              <div className="field">
                <label>Level: {LEVEL_LABEL[level]}</label>
                <div className="chips" style={{ marginBottom: 0 }}>
                  <button className="btn alt" disabled={level === 'year'} onClick={up}>Up</button>
                  {LEVELS.map((l) => <Chip key={l} on={level === l} onClick={() => setLevel(l)}>{LEVEL_LABEL[l]}</Chip>)}
                </div>
              </div>
            </div>
            <h3>{M.label} by {LEVEL_LABEL[level].toLowerCase()}</h3>
            <div className="muted" style={{ marginBottom: 6 }}>Click a bar to drill down into it.</div>
            <div className="chart-box">
              <ResponsiveContainer>
                <ComposedChart data={trend} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                  <XAxis dataKey="key" tick={{ fontSize: 10 }} minTickGap={24} />
                  <YAxis yAxisId="l" tick={{ fontSize: 11 }} tickFormatter={axisFmt(M.fmt)} />
                  {O && <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11 }} tickFormatter={axisFmt(O.fmt)} />}
                  <Tooltip formatter={(v, n, item) => [fmtValue(item && item.dataKey === 'o' && O ? O.fmt : M.fmt, v), n]} />
                  <Legend />
                  <Bar yAxisId="l" dataKey="v" name={M.label} fill={color(0)} cursor="pointer" onClick={(d) => drill(keyOf(d))} />
                  {O && <Line yAxisId="r" type="monotone" dataKey="o" name={O.label} stroke={color(1)} strokeWidth={2} dot={false} />}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {channels.length > 0 && (
            <div className="card chart-card">
              <h3>{mixIsShare ? 'Channel mix (% share)' : 'Marketing spend by channel'} by {LEVEL_LABEL[level].toLowerCase()}</h3>
              <div className="chart-box">
                <ResponsiveContainer>
                  <BarChart data={mix} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                    <XAxis dataKey="key" tick={{ fontSize: 10 }} minTickGap={24} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={axisFmt(mixIsShare ? 'percent' : 'currency')} />
                    <Tooltip formatter={tip(mixIsShare ? 'percent' : 'currency')} />
                    <Legend />
                    {channels.map((c, i) => <Bar key={c} dataKey={c} stackId="s" fill={color(i)} cursor="pointer" onClick={(d) => drill(keyOf(d))} />)}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="two">
            <div className="card chart-card">
              <h3>{M.label} by week type{perWeekNote}</h3>
              <div className="muted" style={{ marginBottom: 6 }}>Click a bar to filter everything to that week type.</div>
              <div className="chart-box">
                <ResponsiveContainer>
                  <BarChart data={segData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={axisFmt(M.fmt)} />
                    <Tooltip formatter={tip(M.fmt)} />
                    <Bar dataKey="v" name={M.label} cursor="pointer" onClick={(d) => d && toggle('segments', d.name !== undefined ? d.name : d.payload.name)}>
                      {segData.map((d, i) => <Cell key={d.name} fill={color(i)} fillOpacity={f.segments.length && !f.segments.includes(d.name) ? 0.3 : 1} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            <div className="card chart-card">
              <h3>{M.label} by month of year{perWeekNote}</h3>
              <div className="muted" style={{ marginBottom: 6 }}>Click a bar to filter to that month.</div>
              <div className="chart-box">
                <ResponsiveContainer>
                  <BarChart data={monData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={axisFmt(M.fmt)} />
                    <Tooltip formatter={tip(M.fmt)} />
                    <Bar dataKey="v" name={M.label} cursor="pointer" onClick={(d) => d && toggle('months', d.month !== undefined ? d.month : d.payload.month)}>
                      {monData.map((d) => <Cell key={d.name} fill={color(0)} fillOpacity={f.months.length && !f.months.includes(d.month) ? 0.3 : 1} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="card chart-card">
            <h3>Relationship between two measures (one dot per week)</h3>
            <div className="slicers">
              <div className="field">
                <label>Horizontal</label>
                <select value={sx} onChange={(e) => setSx(e.target.value)}>{scatterMetrics.map((k) => <option key={k} value={k}>{METRICS[k].label}</option>)}</select>
              </div>
              <div className="field">
                <label>Vertical</label>
                <select value={sy} onChange={(e) => setSy(e.target.value)}>{scatterMetrics.map((k) => <option key={k} value={k}>{METRICS[k].label}</option>)}</select>
              </div>
            </div>
            <div className="muted" style={{ marginBottom: 6 }}>
              {corr === null ? 'Not enough variation to measure a relationship.' : 'r = ' + corr.toFixed(2) + ' across ' + pts.length + ' weeks. Moving together does not prove one causes the other.'}
            </div>
            <div className="chart-box">
              <ResponsiveContainer>
                <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                  <XAxis type="number" dataKey="x" name={METRICS[sx] && METRICS[sx].label} tick={{ fontSize: 11 }} tickFormatter={axisFmt(METRICS[sx] && METRICS[sx].fmt)} />
                  <YAxis type="number" dataKey="y" name={METRICS[sy] && METRICS[sy].label} tick={{ fontSize: 11 }} tickFormatter={axisFmt(METRICS[sy] && METRICS[sy].fmt)} />
                  <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
                    if (!active || !payload || !payload.length) return null;
                    const p = payload[0].payload;
                    return (
                      <div className="card" style={{ padding: 8 }}>
                        <div><strong>{p.date}</strong> ({p.segment})</div>
                        <div>{METRICS[sx].label}: {fmtValue(METRICS[sx].fmt, p.x)}</div>
                        <div>{METRICS[sy].label}: {fmtValue(METRICS[sy].fmt, p.y)}</div>
                      </div>
                    );
                  }} />
                  <Legend />
                  {[...new Set(pts.map((p) => p.segment))].sort().map((s, i) => (
                    <Scatter key={s} name={s} data={pts.filter((p) => p.segment === s)} fill={color(i)} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card chart-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <h3>Weekly detail ({sel.length} weeks)</h3>
              <button className="btn alt" onClick={() => download('weekly_selection.csv', toCsv(sorted, Object.keys(rows[0])))}>Download CSV</button>
            </div>
            <div className="heat">
              <table>
                <thead>
                  <tr>{TABLE_COLS.filter((c) => c[0] === 'date' || c[0] === 'segment' || c[0] === 'unusual' || available.includes(c[0]))
                    .map((c) => <th key={c[0]} onClick={() => sortBy(c[0])}>{c[1]}{sort.key === c[0] ? (sort.dir === 'asc' ? ' \u25B2' : ' \u25BC') : ''}</th>)}</tr>
                </thead>
                <tbody>
                  {view.map((r) => (
                    <tr key={r.date} className={r.loss ? 'high' : ''}>
                      {TABLE_COLS.filter((c) => c[0] === 'date' || c[0] === 'segment' || c[0] === 'unusual' || available.includes(c[0]))
                        .map((c) => <td key={c[0]}>{cell(r, c[0])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <button className="btn alt" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {page + 1} of {pages}</span>
              <button className="btn alt" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
            <p className="muted">
              Totals add up the weekly values. Net Margin % and Net Revenue per spend are calculated from those totals. CAC, LTV to CAC and DSO are simple averages of weekly values. Cash and receivables show the latest week in view. Rows with a red bar on the left lost money.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
''')

w("src/components/help/Manual.jsx", r'''
import { useMemo, useState } from 'react';
import { TABS } from '../../utils/tabs';
import { EXTRA_TABS } from '../../utils/extraTabs';
import useKPIs from '../../hooks/useKPIs';
import useGoals from '../../hooks/useGoals';
import { fmtCurrency, isNum } from '../../utils/formatters';
import {
  TAB_HELP, QUICK_START, EXPLORER_STEPS, EXPLORER_EXAMPLE, GLOSSARY, FAQ, ACCURACY_NOTES,
} from '../../manual/content';

const LIMITS = [
  ['LTV_CAC_MIN', 'LTV to CAC should stay at or above', ''],
  ['ROAS_BREAKEVEN', 'ROAS break-even (below this, advertising does not pay for itself)', ''],
  ['DSO_MAX_DAYS', 'Customers should pay within (days)', ''],
  ['CASH_FLOOR_WEEKS', 'Cash should cover at least (weeks)', ''],
  ['DISCOUNT_RATE_MAX_PCT', 'Average discount should stay below (%)', ''],
  ['RETURN_RATE_MAX_PCT', 'Return rate should stay below (%)', ''],
];

export default function Manual() {
  const [q, setQ] = useState('');
  const { thresholds } = useKPIs();
  const { targets } = useGoals();
  const pages = TABS.concat(EXTRA_TABS).filter((t) => TAB_HELP[t.key]);
  const needle = q.trim().toLowerCase();
  const hit = (...parts) => !needle || parts.join(' ').toLowerCase().includes(needle);

  const sections = useMemo(() => [
    { id: 'start', title: 'Quick start', show: hit('quick start', ...QUICK_START) },
    { id: 'pages', title: 'Page by page', show: pages.some((t) => hit(t.label, TAB_HELP[t.key].what, TAB_HELP[t.key].read, TAB_HELP[t.key].act)) },
    { id: 'explorer', title: 'Using the Interactive Explorer', show: hit('explorer', ...EXPLORER_STEPS, EXPLORER_EXAMPLE) },
    { id: 'glossary', title: 'Glossary', show: GLOSSARY.some((g) => hit(g[0], g[1])) },
    { id: 'limits', title: 'Your current limits', show: hit('limits thresholds targets', ...LIMITS.map((l) => l[1])) },
    { id: 'faq', title: 'Questions and troubleshooting', show: FAQ.some((f) => hit(f[0], f[1])) },
    { id: 'accuracy', title: 'Reading the numbers responsibly', show: hit('accuracy', ...ACCURACY_NOTES) },
  ], [needle]); // eslint-disable-line react-hooks/exhaustive-deps
  const visible = sections.filter((s) => s.show);

  return (
    <div className="manual">
      <div className="no-print" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <input type="text" style={{ width: 280 }} placeholder="Search the manual (for example: DSO)" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn alt" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <div className="chips no-print">
        {visible.map((s) => <a key={s.id} className="chip" href={'#m-' + s.id} onClick={(e) => { e.preventDefault(); const el = document.getElementById('m-' + s.id); if (el) el.scrollIntoView({ behavior: 'smooth' }); }}>{s.title}</a>)}
      </div>
      {!visible.length && <div className="card">Nothing in the manual matches "{q}".</div>}

      {sections.find((s) => s.id === 'start').show && (
        <section id="m-start" className="card man-sec">
          <h3>Quick start</h3>
          <p>This dashboard answers three questions: what happened (UNDERSTAND), what should I do (DECIDE), and what should I watch (MONITOR). Data is refreshed each time your analysis pipeline runs.</p>
          <ol>{QUICK_START.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <p className="muted">Colour guide: green means good or improving, orange means watch, red means a problem or decline.</p>
        </section>
      )}

      {sections.find((s) => s.id === 'pages').show && (
        <section id="m-pages" className="card man-sec">
          <h3>Page by page</h3>
          {pages.filter((t) => hit(t.label, TAB_HELP[t.key].what, TAB_HELP[t.key].read, TAB_HELP[t.key].act)).map((t) => (
            <div key={t.key} className="man-item">
              <h4>{t.label}</h4>
              <p><strong>What it shows.</strong> {TAB_HELP[t.key].what}</p>
              <p><strong>How to read it.</strong> {TAB_HELP[t.key].read}</p>
              <p><strong>What to do.</strong> {TAB_HELP[t.key].act}</p>
            </div>
          ))}
        </section>
      )}

      {sections.find((s) => s.id === 'explorer').show && (
        <section id="m-explorer" className="card man-sec">
          <h3>Using the Interactive Explorer</h3>
          <ol>{EXPLORER_STEPS.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <p>{EXPLORER_EXAMPLE}</p>
        </section>
      )}

      {sections.find((s) => s.id === 'glossary').show && (
        <section id="m-glossary" className="card man-sec">
          <h3>Glossary</h3>
          <dl>
            {GLOSSARY.filter((g) => hit(g[0], g[1])).map((g) => (
              <div key={g[0]} className="man-item"><dt><strong>{g[0]}</strong></dt><dd>{g[1]}</dd></div>
            ))}
          </dl>
        </section>
      )}

      {sections.find((s) => s.id === 'limits').show && (
        <section id="m-limits" className="card man-sec">
          <h3>Your current limits</h3>
          <p className="muted">These values are read live from your analysis, so they always match what the dashboard uses to colour cards and raise alerts.</p>
          <table>
            <tbody>
              {LIMITS.map((l) => (
                <tr key={l[0]}><td>{l[1]}</td><td><strong>{isNum(thresholds[l[0]]) ? thresholds[l[0]] : 'not available'}</strong></td></tr>
              ))}
              <tr><td>Weekly Net Profit target</td><td><strong>{isNum(targets.profit) ? fmtCurrency(targets.profit) : 'set by you in My Targets'}</strong></td></tr>
              <tr><td>Weekly Net Revenue target</td><td><strong>{isNum(targets.revenue) ? fmtCurrency(targets.revenue) : 'set by you in My Targets'}</strong></td></tr>
            </tbody>
          </table>
        </section>
      )}

      {sections.find((s) => s.id === 'faq').show && (
        <section id="m-faq" className="card man-sec">
          <h3>Questions and troubleshooting</h3>
          {FAQ.filter((f) => hit(f[0], f[1])).map((f) => (
            <div key={f[0]} className="man-item"><p><strong>{f[0]}</strong></p><p>{f[1]}</p></div>
          ))}
        </section>
      )}

      {sections.find((s) => s.id === 'accuracy').show && (
        <section id="m-accuracy" className="card man-sec">
          <h3>Reading the numbers responsibly</h3>
          <ul>{ACCURACY_NOTES.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
''')

w("src/components/shared/HelpBar.jsx", r'''
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TAB_HELP } from '../../manual/content';
import useLocalStorage from '../../hooks/useLocalStorage';

export default function HelpBar({ helpKey }) {
  const [open, setOpen] = useState(false);
  const h = TAB_HELP[helpKey];
  if (!h) return null;
  return (
    <div className="help-bar no-print">
      <button className="link" onClick={() => setOpen(!open)}>{open ? 'Hide help for this page' : 'How to read this page'}</button>
      {open && (
        <div className="help-box">
          <p><strong>What it shows.</strong> {h.what}</p>
          <p><strong>How to read it.</strong> {h.read}</p>
          <p><strong>What to do.</strong> {h.act}</p>
          <Link to="/help/manual">Open the full User Manual</Link>
        </div>
      )}
    </div>
  );
}

export function Welcome() {
  const [seen, setSeen] = useLocalStorage('welcome_seen', false);
  if (seen) return null;
  return (
    <div className="notice no-print" style={{ marginBottom: 16 }}>
      <strong>Welcome.</strong> Each page has a "How to read this page" link under its title, and a full{' '}
      <Link to="/help/manual">User Manual</Link> is in the HELP section of the menu.{' '}
      <button className="link" onClick={() => setSeen(true)}>Got it</button>
    </div>
  );
}
''')

w("src/components/shared/Sidebar.jsx", r'''
import { NavLink } from 'react-router-dom';
import { PROJECT, TABS, OUTCOMES } from '../../utils/tabs';
import { EXTRA_OUTCOMES, EXTRA_TABS } from '../../utils/extraTabs';

export default function Sidebar() {
  const groups = OUTCOMES.concat(EXTRA_OUTCOMES);
  const tabs = TABS.concat(EXTRA_TABS);
  return (
    <aside className="sidebar">
      <div className="brand">{PROJECT.name}</div>
      {groups.map((o) => (
        <div key={o.id}>
          <div className="nav-group">{o.label}</div>
          {tabs.filter((t) => t.outcome === o.id).map((t) => (
            <NavLink key={t.key} to={'/' + t.outcome + '/' + t.key}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
              {t.label}
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}
''')

w("src/pages/Dashboard.jsx", r'''
import { useParams } from 'react-router-dom';
import Sidebar from '../components/shared/Sidebar';
import Header from '../components/shared/Header';
import HelpBar, { Welcome } from '../components/shared/HelpBar';
import KPICards from '../components/understand/KPICards';
import ChartPanel from '../components/understand/ChartPanel';
import AnomalyTable from '../components/understand/AnomalyTable';
import SegmentExplorer from '../components/understand/SegmentExplorer';
import InsightCards from '../components/decide/InsightCards';
import RecommendationEngine from '../components/decide/RecommendationEngine';
import WhatIfSimulator from '../components/decide/WhatIfSimulator';
import GoalTracker from '../components/decide/GoalTracker';
import Forecaster from '../components/monitor/Forecaster';
import GoalProgress from '../components/monitor/GoalProgress';
import AlertCenter from '../components/monitor/AlertCenter';
import Explorer from '../components/explore/Explorer';
import Manual from '../components/help/Manual';
import { TABS } from '../utils/tabs';
import { EXTRA_TABS } from '../utils/extraTabs';

const REGISTRY = {
  KPICards, ChartPanel, AnomalyTable, SegmentExplorer, InsightCards, RecommendationEngine,
  WhatIfSimulator, GoalTracker, Forecaster, GoalProgress, AlertCenter, Explorer, Manual,
};

export default function Dashboard() {
  const { outcome, tab } = useParams();
  const all = TABS.concat(EXTRA_TABS);
  const cur = all.find((t) => t.outcome === outcome && t.key === tab) || TABS[0];
  const Comp = REGISTRY[cur.component];
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <Header />
        <main className="content">
          <Welcome />
          <h2>{cur.label}</h2>
          {cur.key !== 'manual' && <HelpBar key={cur.key} helpKey={cur.key} />}
          <Comp />
        </main>
      </div>
    </div>
  );
}
''')

css_path = os.path.join(PKG, "src/index.css")
css = open(css_path, encoding="utf-8").read()
CSS = r'''
/* BI-EXPLORER-AND-MANUAL */
select { padding: 8px; border: 1px solid var(--color-border); border-radius: 6px; background: var(--color-surface); max-width: 200px; }
.slicers { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
.two .chart-card { margin-bottom: 16px; }
a.chip { text-decoration: none; color: inherit; display: inline-block; }
.help-bar { margin: -8px 0 16px; }
.help-box { background: #FFF8E6; border: 1px solid var(--color-accent); border-radius: 8px; padding: 10px 14px; margin-top: 8px; }
.help-box p { margin: 6px 0; }
.manual { max-width: 900px; }
.man-sec { margin-bottom: 16px; }
.man-sec h4 { margin: 12px 0 4px; font-family: var(--font-head); }
.man-item { margin-bottom: 10px; }
.man-sec dd { margin: 2px 0 0 0; color: var(--color-text-2); }
.man-sec li { margin-bottom: 6px; }
@media print { .sidebar, .header, .no-print { display: none !important; } .shell { display: block; } .card { break-inside: avoid; } }
'''
if "BI-EXPLORER-AND-MANUAL" not in css:
    open(css_path, "a", encoding="utf-8", newline="\n").write("\n" + CSS)
print("Done: 9 files written.")
print("Next: cd %s && npm run dev   (Ctrl+F5). New menu groups: EXPLORE and HELP." % PKG)