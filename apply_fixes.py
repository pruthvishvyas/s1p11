#!/usr/bin/env python3
"""
apply_fixes.py - aligns the React SaaS with the REAL pipeline output schema.
Run from the folder that contains frontend_contract.json (your s1p11 folder):
    python apply_fixes.py
Then:  python a.py   (or sync_data.py)   ->   cd <pkg>  ->  npm run dev
"""
import json
import os

PKG = "d2c_weekly_growth"
if os.path.exists("frontend_contract.json"):
    with open("frontend_contract.json", encoding="utf-8") as f:
        PKG = json.load(f)["project"]["client_id"]
if not os.path.isdir(PKG):
    raise SystemExit("Folder '%s' not found. Run this from the folder that contains it." % PKG)

N = [0]


def w(rel, text):
    full = os.path.join(PKG, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.strip("\n") + "\n")
    N[0] += 1


# ---------------------------------------------------------------- 1. sync scripts (forecast lookup was all null)
def patch_sync(path):
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        s = f.read()
    if "Net_Revenue_forecast" in s:
        print("  already patched: " + path)
        return
    pairs = [
        ('REV_K = ("forecast",', 'REV_K = ("Net_Revenue_forecast", "forecast",'),
        ('PRO_K = ("net_profit",', 'PRO_K = ("Net_Profit_forecast", "net_profit",'),
        ('LOW_K = ("lower",', 'LOW_K = ("Net_Revenue_lo80", "lower",'),
        ('UP_K = ("upper",', 'UP_K = ("Net_Revenue_hi80", "upper",'),
        ('"lower": _first(r, LOW_K), "upper": _first(r, UP_K)}',
         '"lower": _first(r, LOW_K), "upper": _first(r, UP_K),\n'
         '                             "profit_lower": _first(r, ("Net_Profit_lo80",)), '
         '"profit_upper": _first(r, ("Net_Profit_hi80",)), "week_start": r.get("Week_Start")}'),
    ]
    miss = 0
    for a, b in pairs:
        if a in s:
            s = s.replace(a, b)
        else:
            miss += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print("  patched: %s%s" % (path, " (%d pattern(s) not found)" % miss if miss else ""))


print("Patching sync scripts:")
for p in ("sync_data.py", "a.py", "build_notebook.py"):
    patch_sync(p)

# ---------------------------------------------------------------- 2. hooks
w("src/hooks/useKPIs.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList } from '../utils/formatters';

export const findKpi = (list, ...ids) =>
  list.find((k) => ids.includes(String(k.key).toLowerCase().replace(/[^a-z0-9]/g, '')));

export default function useKPIs() {
  const s = useJson(DATA.kpis);
  const d = s.data && typeof s.data === 'object' ? s.data : {};
  return { ...s, kpis: asList(d, 'kpis'), thresholds: d.thresholds || {} };
}
''')

w("src/hooks/useSegments.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, toNum } from '../utils/formatters';

export default function useSegments() {
  const s = useJson(DATA.segments);
  const d = s.data && typeof s.data === 'object' ? s.data : {};
  const assignments = asList(d, 'assignments');
  const tier = {};
  assignments.forEach((a) => { if (a.segment_tier !== undefined) tier[String(a.segment)] = String(a.segment_tier); });
  const items = asList(d, 'profile').map((o) => ({
    id: String(o.segment),
    label: tier[String(o.segment)] || String(o.segment),
    weeks: toNum(o.weeks),
    margin: toNum(o.Net_Margin_pct),
    roas: toNum(o.ROAS),
    cac: toNum(o.CAC),
    profit: toNum(o.Net_Profit),
    revenue: toNum(o.Net_Revenue),
    lossRate: toNum(o.loss_week_rate),
  }));
  return { ...s, items, assignments, report: d.report || {} };
}
''')

w("src/hooks/useRecommendations.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList } from '../utils/formatters';

export default function useRecommendations() {
  const s = useJson(DATA.recommendations);
  return { ...s, recs: asList(s.data, 'recommendations'), channels: asList(s.data, 'channel_priority') };
}
''')

w("src/hooks/useGoals.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { toNum } from '../utils/formatters';

export default function useGoals() {
  const s = useJson(DATA.goals);
  const g = s.data && typeof s.data === 'object' ? s.data : {};
  const v = (k) => toNum(g[k] && g[k].value);
  return {
    ...s,
    targets: { profit: v('net_profit_target'), revenue: v('net_revenue_target') },
    thresholds: { drop: v('alert_revenue_drop_pct'), weeks: v('cash_floor_weeks'), ltv: v('ltv_cac_min') },
  };
}
''')

w("src/hooks/useGoalProgress.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useGoalProgress() {
  const s = useJson(DATA.goal_progress);
  return { ...s, g: s.data && typeof s.data === 'object' ? s.data : {} };
}
''')

w("src/hooks/useForecast.js", r'''
import { useCallback, useState } from 'react';
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, toNum } from '../utils/formatters';

const HIST_WEEKS = 26;
const day = (v) => String(v).slice(0, 10);

export default function useForecast() {
  const s = useJson(DATA.forecast);
  const h = useJson(DATA.charts + 'growth_vs_profit.json');
  const [pred, setPred] = useState({ loading: false, error: null, result: null });

  const fut = asList(s.data, 'forecast');
  const report = (s.data && s.data.report) || {};
  const hx = h.data && Array.isArray(h.data.x) ? h.data.x : [];
  const hs = (h.data && h.data.series) || {};
  const start = Math.max(0, hx.length - HIST_WEEKS);

  // metric: 'Net_Revenue' | 'Net_Profit'
  const rowsFor = (metric) => {
    const col = metric === 'Net_Profit' ? 'net_profit' : 'net_revenue';
    const rows = hx.slice(start).map((x, j) => ({
      x: day(x), actual: toNum((hs[col] || [])[start + j]), forecast: null, band: null,
    }));
    if (rows.length) rows[rows.length - 1].forecast = rows[rows.length - 1].actual;
    fut.forEach((f) => {
      const lo = toNum(f[metric + '_lo80']);
      const hi = toNum(f[metric + '_hi80']);
      rows.push({ x: day(f.Week_Start), actual: null, forecast: toNum(f[metric + '_forecast']),
        band: lo !== null && hi !== null ? [lo, hi] : null });
    });
    return rows;
  };

  const runForecast = useCallback(async (weeksAhead) => {
    setPred({ loading: true, error: null, result: null });
    try {
      const res = await fetch('/api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weeks_ahead: weeksAhead }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      setPred({ loading: false, error: null, result: await res.json() });
    } catch (error) {
      setPred({ loading: false, error, result: null });
    }
  }, []);

  return { loading: s.loading, error: s.error, fut, report, rowsFor, pred, runForecast };
}
''')

# ---------------------------------------------------------------- 3. UNDERSTAND
w("src/components/understand/KPICards.jsx", r'''
import useKPIs from '../../hooks/useKPIs';
import EmptyState from '../shared/EmptyState';
import { fmtValue, humanize, isNum, toNum } from '../../utils/formatters';

function kindOf(k) {
  const u = String(k.unit || '').toLowerCase();
  const key = String(k.key || '').toLowerCase();
  if (/%|pct|percent/.test(u) || /margin|rate|pct/.test(key)) return 'percent';
  if (/week|day/.test(u) || /runway|dso/.test(key)) return 'number1';
  if (/^x$|ratio|\u00d7/.test(u) || /roas|ltv/.test(key)) return 'ratio';
  if (/\u20b9|inr|currency|rupee|\$/.test(u) || /revenue|profit|cac|cash|spend|receivable|ar_/.test(key)) return 'currency';
  return 'number1';
}

function warnOf(k, v, th) {
  const key = String(k.key || '').toLowerCase();
  if (v === null) return null;
  if (/ltv/.test(key) && isNum(th.LTV_CAC_MIN) && v < th.LTV_CAC_MIN) return 'Below the ' + th.LTV_CAC_MIN + ' target';
  if (/runway/.test(key) && isNum(th.CASH_FLOOR_WEEKS) && v < th.CASH_FLOOR_WEEKS) return 'Under ' + th.CASH_FLOOR_WEEKS + ' weeks of cash';
  if (/^roas/.test(key) && isNum(th.ROAS_BREAKEVEN) && v < th.ROAS_BREAKEVEN) return 'Below break-even ROAS of ' + th.ROAS_BREAKEVEN;
  if (/dso/.test(key) && isNum(th.DSO_MAX_DAYS) && v > th.DSO_MAX_DAYS) return 'Above the ' + th.DSO_MAX_DAYS + ' day limit';
  return null;
}

export default function KPICards() {
  const { kpis, thresholds, loading } = useKPIs();
  if (loading) return <div className="note">Loading...</div>;
  if (!kpis.length) return <EmptyState />;
  return (
    <div className="grid kpis">
      {kpis.map((k) => {
        const v = toNum(k.value);
        const ch = toNum(k.change_pct);
        const lowerIsBetter = /cac|dso/.test(String(k.key).toLowerCase());
        const good = ch === null ? true : lowerIsBetter ? ch <= 0 : ch >= 0;
        const warn = warnOf(k, v, thresholds);
        return (
          <div key={k.key} className={'card' + (warn ? ' kpi-warn' : '')}>
            <div className="kpi-label">{k.label || humanize(k.key)}</div>
            <div className="kpi-value">{fmtValue(kindOf(k), v)}</div>
            {ch !== null && (
              <div className={good ? 'up' : 'down'}>
                {ch >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(ch).toFixed(1)}% vs prior {k.period ? '(' + k.period + ')' : 'period'}
              </div>
            )}
            {warn && <div className="warn-text">{warn}</div>}
          </div>
        );
      })}
    </div>
  );
}
''')

w("src/components/understand/ChartPanel.jsx", r'''
import { useMemo } from 'react';
import useCharts from '../../hooks/useCharts';
import useSegments from '../../hooks/useSegments';
import { useOutcome } from '../../contexts/OutcomeContext';
import EmptyState from '../shared/EmptyState';
import { humanize, isNum, toNum } from '../../utils/formatters';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;
const color = (i) => cssVar('--chart-' + ((i % 6) + 1));
const compact = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 });
const tick = (v) => (isNum(v) ? compact.format(v) : v);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const KIND = { channel_mix: 'area', seasonality_heatmap: 'heat', promo_profitability: 'bar', channel_lag_correlation: 'bar' };
const RIGHT = /dso|ltv_to_cac|^weeks$/i; // series on a different scale get a right-hand axis

// Pipeline charts are column-oriented: {x: [...], series: {name: [...]}}
function toRows(c) {
  const x = Array.isArray(c.x) ? c.x : [];
  const s = c.series && typeof c.series === 'object' ? c.series : {};
  const names = Object.keys(s).filter((k) => Array.isArray(s[k]));
  const rows = x.map((xv, i) => {
    const r = { x: xv };
    names.forEach((n) => { r[n] = toNum(s[n][i]); });
    return r;
  });
  return { rows, names };
}

function Heat({ c }) {
  const years = Array.isArray(c.x) ? c.x : [];
  const s = c.series || {};
  const keys = Object.keys(s).sort((a, b) => Number(a) - Number(b));
  const vals = keys.flatMap((k) => (s[k] || []).map(toNum)).filter(isNum);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  return (
    <div className="heat">
      <table>
        <thead><tr><th>Month</th>{years.map((y) => <th key={y}>{y}</th>)}</tr></thead>
        <tbody>
          {keys.map((k) => (
            <tr key={k}>
              <td>{MONTHS[Number(k) - 1] || k}</td>
              {years.map((y, i) => {
                const v = toNum((s[k] || [])[i]);
                const a = v === null || hi === lo ? 0 : (v - lo) / (hi - lo);
                return <td key={y} style={{ background: 'rgba(245,158,11,' + (0.1 + a * 0.7).toFixed(2) + ')' }}>{v === null ? '-' : v.toFixed(1)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OneChart({ name, c, weeks }) {
  const kind = KIND[c.id || name] || 'line';
  const head = (
    <>
      <h3>{c.title || humanize(name)}</h3>
      {c.question && <div className="muted" style={{ marginBottom: 8 }}>{c.question}</div>}
    </>
  );
  if (kind === 'heat') return <div className="card chart-card">{head}<Heat c={c} /></div>;

  let { rows, names } = toRows(c);
  if (weeks && rows.length && /^\d{4}-\d{2}-\d{2}/.test(String(rows[0].x))) {
    rows = rows.filter((r) => weeks.has(String(r.x).slice(0, 10)));
  }
  if (!rows.length || !names.length) return <div className="card chart-card">{head}<EmptyState message="No data for this selection" /></div>;

  const hasR = names.some((n) => RIGHT.test(n));
  const ax = (n) => (RIGHT.test(n) ? 'r' : 'l');
  const refs = [];
  if (isNum(c.floor)) refs.push({ y: c.floor, label: 'Minimum ' + c.floor });
  if (isNum(c.dso_limit)) refs.push({ y: c.dso_limit, label: 'DSO limit ' + c.dso_limit });
  const bar = kind === 'bar';
  const common = { data: rows, margin: { top: 8, right: 16, left: 0, bottom: bar ? 24 : 0 } };
  const axes = [
    <CartesianGrid key="g" strokeDasharray="3 3" stroke={cssVar('--color-border')} />,
    <XAxis key="x" dataKey="x" tick={{ fontSize: 10 }} minTickGap={bar ? 0 : 40}
      interval={bar ? 0 : 'preserveStartEnd'} angle={bar ? -25 : 0} textAnchor={bar ? 'end' : 'middle'} height={bar ? 70 : 30} />,
    <YAxis key="yl" yAxisId="l" tick={{ fontSize: 11 }} tickFormatter={tick} />,
    hasR ? <YAxis key="yr" yAxisId="r" orientation="right" tick={{ fontSize: 11 }} tickFormatter={tick} /> : null,
    <Tooltip key="t" />,
    <Legend key="lg" />,
    ...refs.map((r, i) => (
      <ReferenceLine key={'r' + i} yAxisId={hasR ? 'r' : 'l'} y={r.y} stroke={cssVar('--color-danger')}
        strokeDasharray="4 4" label={{ value: r.label, fontSize: 11 }} />
    )),
  ];
  let chart;
  if (kind === 'area') {
    chart = <AreaChart {...common}>{axes}{names.map((n, i) => <Area key={n} yAxisId="l" type="monotone" dataKey={n} name={humanize(n)} stackId="1" stroke={color(i)} fill={color(i)} fillOpacity={0.6} />)}</AreaChart>;
  } else if (bar) {
    chart = <BarChart {...common}>{axes}{names.map((n, i) => <Bar key={n} yAxisId={ax(n)} dataKey={n} name={humanize(n)} fill={color(i)} />)}</BarChart>;
  } else {
    chart = <LineChart {...common}>{axes}{names.map((n, i) => <Line key={n} yAxisId={ax(n)} type="monotone" dataKey={n} name={humanize(n)} stroke={color(i)} dot={false} strokeWidth={2} />)}</LineChart>;
  }
  return (
    <div className="card chart-card">
      {head}
      {isNum(c.discount_limit_pct) && <div className="notice">Promo discounts above {c.discount_limit_pct}% have historically lost money.</div>}
      <div className="chart-box"><ResponsiveContainer>{chart}</ResponsiveContainer></div>
    </div>
  );
}

export default function ChartPanel() {
  const { charts, loading } = useCharts();
  const { assignments } = useSegments();
  const { segment } = useOutcome();
  const weeks = useMemo(() => {
    if (!segment) return null;
    return new Set(assignments
      .filter((a) => String(a.segment_tier) === segment || String(a.segment) === segment)
      .map((a) => String(a.Week_Start).slice(0, 10)));
  }, [assignments, segment]);
  if (loading) return <div className="note">Loading...</div>;
  if (!charts.length) return <EmptyState />;
  return (
    <div>
      {segment && <p className="muted">Showing only "{segment}" weeks on the time-series charts.</p>}
      {charts.map((c) => <OneChart key={c.name} name={c.name} c={c.data || {}} weeks={weeks} />)}
    </div>
  );
}
''')

w("src/components/understand/SegmentExplorer.jsx", r'''
import useSegments from '../../hooks/useSegments';
import { useOutcome } from '../../contexts/OutcomeContext';
import EmptyState from '../shared/EmptyState';
import { fmtCurrency, fmtNumber, fmtPercent, fmtRatio, isNum } from '../../utils/formatters';

export default function SegmentExplorer() {
  const { items, report, loading } = useSegments();
  const { segment, setSegment } = useOutcome();
  if (loading) return <div className="note">Loading...</div>;
  if (!items.length) return <EmptyState />;
  return (
    <div>
      <p className="muted">
        Click a week type to filter the charts on the "Profit &amp; Spend Charts" tab.
        {isNum(report.silhouette) ? ' Cluster quality (silhouette): ' + report.silhouette.toFixed(2) + '.' : ''}
      </p>
      <div className="grid cols3">
        {items.map((s) => (
          <div key={s.id} className={'card seg' + (segment === s.label ? ' on' : '')}
            onClick={() => setSegment(segment === s.label ? null : s.label)}>
            <h3>{s.label} weeks</h3>
            <div>Weeks: <strong>{fmtNumber(s.weeks)}</strong></div>
            <div>Net margin: <strong>{fmtPercent(s.margin)}</strong></div>
            <div>ROAS: <strong>{fmtRatio(s.roas)}</strong></div>
            <div>CAC: <strong>{fmtCurrency(s.cac)}</strong></div>
            <div>Net profit: <strong>{fmtCurrency(s.profit)}</strong></div>
            <div>Net revenue: <strong>{fmtCurrency(s.revenue)}</strong></div>
            <div>Loss-week rate: <strong>{fmtNumber(s.lossRate, 2)}</strong></div>
          </div>
        ))}
      </div>
    </div>
  );
}
''')

# ---------------------------------------------------------------- 4. DECIDE
w("src/components/decide/InsightCards.jsx", r'''
import { useState } from 'react';
import useInsights from '../../hooks/useInsights';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { SEV_RANK, humanize, sevOf } from '../../utils/formatters';

export default function InsightCards() {
  const { insights, loading } = useInsights();
  const [cat, setCat] = useState('All');
  if (loading) return <div className="note">Loading...</div>;
  if (!insights.length) return <EmptyState />;
  const cats = ['All', ...new Set(insights.map((i) => String(i.category || 'Other')))];
  const list = insights
    .filter((i) => cat === 'All' || String(i.category || 'Other') === cat)
    .sort((a, b) => (SEV_RANK[sevOf(a)] ?? 3) - (SEV_RANK[sevOf(b)] ?? 3));
  return (
    <div>
      <div className="chips">
        {cats.map((c) => (
          <button key={c} className={'chip' + (cat === c ? ' on' : '')} onClick={() => setCat(c)}>{c === 'All' ? c : humanize(c)}</button>
        ))}
      </div>
      <div className="grid cols3">
        {list.map((i, n) => (
          <div key={i.id || n} className="card">
            <div style={{ marginBottom: 8 }}>
              <SeverityBadge level={sevOf(i)} />{' '}
              <span className="muted">{humanize(i.category || '')}</span>
            </div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{i.finding}</div>
            {i.evidence && <div style={{ color: '#4A5160', marginBottom: 10 }}>{i.evidence}</div>}
            {i.action && <div style={{ background: '#FFF8E6', color: '#7A4B00', padding: 8, borderRadius: 6 }}>{i.action}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
''')

w("src/components/decide/RecommendationEngine.jsx", r'''
import useRecommendations from '../../hooks/useRecommendations';
import useLocalStorage from '../../hooks/useLocalStorage';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { fmtNumber, humanize, sevOf } from '../../utils/formatters';

const cell = (v) => (typeof v === 'number' ? fmtNumber(v, 2) : v === null || v === undefined ? '-' : String(v));

export default function RecommendationEngine() {
  const { recs, channels, loading } = useRecommendations();
  const [done, setDone] = useLocalStorage('recs_done', []);
  if (loading) return <div className="note">Loading...</div>;
  if (!recs.length && !channels.length) return <EmptyState />;
  const all = recs.map((r) => ({ r, id: [r.scope, r.subject, r.rule, r.action].join('|') }));
  const open = all.filter((x) => !done.includes(x.id));
  const closed = all.filter((x) => done.includes(x.id));
  const body = (r) => (
    <>
      <div className="muted">{humanize(r.scope || '')}{r.subject ? ' \u00B7 ' + r.subject : ''}</div>
      <div style={{ margin: '4px 0' }}><strong>{r.action}</strong></div>
      {r.evidence && <div>{r.evidence}</div>}
      {r.rule && <div className="muted">Rule: {r.rule}</div>}
    </>
  );
  const cols = channels.length ? Object.keys(channels[0]).filter((k) => k !== 'rule') : [];
  return (
    <div>
      <div className="grid">
        {open.map(({ r, id }) => (
          <div key={id} className="card">
            <SeverityBadge level={sevOf(r)} />
            <div style={{ margin: '8px 0' }}>{body(r)}</div>
            <button className="btn" onClick={() => setDone([...done, id])}>Mark done</button>
          </div>
        ))}
      </div>
      {closed.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Completed</h3>
          <div className="grid">
            {closed.map(({ r, id }) => (
              <div key={id} className="card done">{body(r)}{' '}
                <button className="link" onClick={() => setDone(done.filter((d) => d !== id))}>Undo</button>
              </div>
            ))}
          </div>
        </div>
      )}
      {channels.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Channel priority</h3>
          <div className="heat">
            <table>
              <thead><tr>{cols.map((c) => <th key={c}>{humanize(c)}</th>)}</tr></thead>
              <tbody>{channels.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{cell(r[c])}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
''')

w("src/components/decide/WhatIfSimulator.jsx", r'''
import { useState } from 'react';
import useSimulations from '../../hooks/useSimulations';
import EmptyState from '../shared/EmptyState';
import { fmtNumber, fmtValue, toNum } from '../../utils/formatters';

const isExtra = (v) => v === true || (typeof v === 'string' && v !== '' && !/^(false|no|none|inside)$/i.test(v));

function nearest(list, f, target) {
  const tg = toNum(target);
  if (tg === null) return Math.floor(list.length / 2);
  let b = 0;
  list.forEach((s, i) => {
    if (Math.abs((toNum(s[f]) ?? 0) - tg) < Math.abs((toNum(list[b][f]) ?? 0) - tg)) b = i;
  });
  return b;
}

const CFG = {
  promo_discount_depth: {
    title: 'Promo discount depth', field: 'discount_rate_pct', label: 'Discount rate', unit: '%',
    base: (m, l) => nearest(l, 'discount_rate_pct', m.baseline_discount_rate_pct),
    outs: [['orders', 'Orders', 'number'], ['net_revenue', 'Net Revenue', 'currency'], ['net_profit', 'Net Profit', 'currency']],
  },
  cac_cap_scenarios: {
    title: 'Marketing spend level', field: 'spend_multiplier', label: 'Spend vs today', unit: 'x',
    base: (m, l) => nearest(l, 'spend_multiplier', 1),
    outs: [['weekly_spend', 'Weekly spend', 'currency'], ['net_revenue', 'Net Revenue', 'currency'],
      ['new_customers', 'New customers', 'number'], ['net_profit', 'Net Profit', 'currency'],
      ['marketing_pct_of_revenue', 'Marketing % of revenue', 'percent']],
  },
};

function Meta({ meta }) {
  const r2 = toNum(meta.model_r2 ?? meta.elasticity_model_r2);
  return (
    <>
      {r2 !== null && <div className="muted">Model fit (R&sup2;): {r2.toFixed(2)}</div>}
      {meta.caveat && <p className="muted">{meta.caveat}</p>}
    </>
  );
}

function SliderPanel({ cfg, meta, list }) {
  const rows = [...list].sort((a, b) => (toNum(a[cfg.field]) ?? 0) - (toNum(b[cfg.field]) ?? 0));
  const baseIdx = cfg.base(meta, rows);
  const [i, setI] = useState(baseIdx);
  const cur = rows[i] || rows[0];
  const base = rows[baseIdx];
  return (
    <div className="card">
      <h3>{cfg.title}</h3>
      <div className="field">
        <label>{cfg.label}: <strong>{fmtNumber(toNum(cur[cfg.field]), 2)}{cfg.unit}</strong>{i === baseIdx ? ' (current)' : ''}</label>
        <input type="range" min={0} max={rows.length - 1} step={1} value={i} onChange={(e) => setI(Number(e.target.value))} />
      </div>
      {isExtra(cur.extrapolation) && <div className="notice">Outside the range seen in your history, so treat this as a rough estimate.</div>}
      {cfg.outs.map(([k, lab, f]) => {
        const v = toNum(cur[k]);
        const b = toNum(base[k]);
        const d = v !== null && b !== null ? v - b : null;
        return (
          <div key={k}>{lab}: <strong>{fmtValue(f, v)}</strong>
            {d !== null && i !== baseIdx && <span className={d >= 0 ? 'up' : 'down'}> ({d >= 0 ? '+' : ''}{fmtValue(f, d)} vs current)</span>}
          </div>
        );
      })}
      <Meta meta={meta} />
    </div>
  );
}

function ShiftPanel({ meta, list }) {
  const pairs = [...new Set(list.map((s) => s.pair))];
  const [p, setP] = useState(pairs[0]);
  const rows = list.filter((s) => s.pair === p).sort((a, b) => (toNum(a.signed_step) ?? 0) - (toNum(b.signed_step) ?? 0));
  const ok = list.filter((s) => s.feasible !== false && !isExtra(s.extrapolation) && toNum(s.delta_net_profit) !== null)
    .sort((a, b) => b.delta_net_profit - a.delta_net_profit);
  const best = ok[0];
  return (
    <div className="card">
      <h3>Shift budget between channels</h3>
      {best && best.delta_net_profit > 0 && (
        <div className="notice">Best in-range move: shift {best.shift_pct_of_budget}% of budget from {best.from} to {best.to} ({fmtValue('currency', best.delta_net_profit)} weekly Net Profit).</div>
      )}
      <div className="field">
        <label>Channel pair</label>
        <select value={p} onChange={(e) => setP(e.target.value)}>{pairs.map((x) => <option key={x}>{x}</option>)}</select>
      </div>
      <div className="heat">
        <table>
          <thead><tr><th>Shift % of budget</th><th>Feasible</th><th>&Delta; Net Revenue</th><th>&Delta; Net Profit</th><th>Driver-model &Delta; profit</th><th>Note</th></tr></thead>
          <tbody>
            {rows.map((s, i) => (
              <tr key={i}>
                <td>{fmtNumber(toNum(s.signed_step) !== null ? toNum(s.signed_step) : toNum(s.shift_pct_of_budget), 1)}</td>
                <td>{s.feasible === false ? 'No' : 'Yes'}</td>
                <td>{fmtValue('currency', toNum(s.delta_net_revenue))}</td>
                <td>{fmtValue('currency', toNum(s.delta_net_profit))}</td>
                <td>{fmtValue('currency', toNum(s.driver_model_delta_net_profit))}</td>
                <td>{isExtra(s.extrapolation) ? 'Outside observed range' : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Meta meta={meta} />
    </div>
  );
}

export default function WhatIfSimulator() {
  const { sims, loading } = useSimulations();
  if (loading) return <div className="note">Loading...</div>;
  if (!sims.length) return <EmptyState />;
  return (
    <div className="grid">
      {sims.map((s) => {
        const d = s.data || {};
        const meta = d.meta || {};
        const list = Array.isArray(d.scenarios) ? d.scenarios : [];
        if (!list.length) return <div key={s.name} className="card"><EmptyState /></div>;
        if (s.name === 'channel_budget_shift') return <ShiftPanel key={s.name} meta={meta} list={list} />;
        const cfg = CFG[s.name];
        return cfg ? <SliderPanel key={s.name} cfg={cfg} meta={meta} list={list} /> : null;
      })}
    </div>
  );
}
''')

w("src/components/decide/GoalTracker.jsx", r'''
import useGoals from '../../hooks/useGoals';
import useGoalProgress from '../../hooks/useGoalProgress';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import { fmtCurrency, toNum } from '../../utils/formatters';

function Row({ label, target, actual, onChange }) {
  const tgt = toNum(target);
  const pct = tgt && actual !== null ? Math.max(0, (actual / tgt) * 100) : null;
  const status = pct === null ? null : pct >= 100 ? 'On track' : pct >= 80 ? 'At risk' : 'Behind';
  const sc = { 'On track': '#27AE60', 'At risk': '#E67E22', Behind: '#C0392B' };
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="field">
        <label>{label}</label>
        <input type="number" value={target ?? ''} onChange={(e) => onChange(e.target.value)} />
      </div>
      {status === null ? (
        <div className="muted">Set your target to track progress</div>
      ) : (
        <>
          <div className="progress"><div style={{ width: Math.min(100, pct) + '%' }} /></div>
          <div style={{ marginTop: 6 }}>
            Latest week {fmtCurrency(actual)} of {fmtCurrency(tgt)} ({pct.toFixed(0)}%){' '}
            <strong style={{ color: sc[status] }}>{status}</strong>
          </div>
        </>
      )}
    </div>
  );
}

export default function GoalTracker() {
  const t = useTerm();
  const { targets } = useGoals();
  const { g } = useGoalProgress();
  const [stored, setStored] = useLocalStorage('targets', null);
  const eff = stored || { profit: targets.profit, revenue: targets.revenue };
  const profit = toNum(g.net_profit_target && g.net_profit_target.actual_last_week);
  const revenue = toNum(g.net_revenue_target && g.net_revenue_target.actual_last_week);
  return (
    <div style={{ maxWidth: 560 }}>
      <Row label="Weekly Net Profit target" target={eff.profit} actual={profit}
        onChange={(v) => setStored({ ...eff, profit: v })} />
      <Row label={t('Weekly {revenue} target')} target={eff.revenue} actual={revenue}
        onChange={(v) => setStored({ ...eff, revenue: v })} />
    </div>
  );
}
''')

# ---------------------------------------------------------------- 5. MONITOR
w("src/components/monitor/Forecaster.jsx", r'''
import { useState } from 'react';
import useForecast from '../../hooks/useForecast';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtCurrency, toNum } from '../../utils/formatters';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;
const compact = new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 });
const show = (v) => (v === null || v === undefined ? '-' : typeof v === 'object' ? JSON.stringify(v) : String(v));
const range = (lo, hi) => (lo !== null && hi !== null ? fmtCurrency(lo) + ' to ' + fmtCurrency(hi) : '-');

export default function Forecaster() {
  const t = useTerm();
  const { loading, fut, report, rowsFor, pred, runForecast } = useForecast();
  const [metric, setMetric] = useState('Net_Revenue');
  const [weeks, setWeeks] = useState(4);
  const n = Math.min(13, Math.max(1, Math.round(Number(weeks) || 1)));
  const r = pred.result;
  const rows = rowsFor(metric);
  const revLabel = t('{revenue}');

  return (
    <div>
      <div className="chips">
        <button className={'chip' + (metric === 'Net_Revenue' ? ' on' : '')} onClick={() => setMetric('Net_Revenue')}>{revLabel}</button>
        <button className={'chip' + (metric === 'Net_Profit' ? ' on' : '')} onClick={() => setMetric('Net_Profit')}>Net Profit</button>
      </div>
      <div className="card chart-card">
        <h3>{(metric === 'Net_Revenue' ? revLabel : 'Net Profit') + ': last 26 weeks and 13-week outlook'}</h3>
        {(report.direction !== undefined || report.next_week_loss_risk !== undefined) && (
          <div className="muted" style={{ marginBottom: 8 }}>
            Direction: {show(report.direction)} | Next-week loss risk: {show(report.next_week_loss_risk)}
          </div>
        )}
        {loading ? <div className="note">Loading...</div> : !fut.length ? <EmptyState /> : (
          <div className="chart-box">
            <ResponsiveContainer>
              <ComposedChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={30} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => compact.format(v)} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="band" name="80% range" stroke="none" fill={cssVar('--color-accent')} fillOpacity={0.2} />
                <Line type="monotone" dataKey="actual" name="Actual" stroke={cssVar('--chart-1')} dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="forecast" name="Forecast" stroke={cssVar('--chart-2')} strokeDasharray="5 5" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {fut.length > 0 && (
        <div className="card chart-card heat">
          <table>
            <thead><tr><th>Week</th><th>{revLabel}</th><th>80% range</th><th>Net Profit</th><th>80% range</th></tr></thead>
            <tbody>
              {fut.map((f, i) => (
                <tr key={i}>
                  <td>{String(f.Week_Start).slice(0, 10)}</td>
                  <td>{fmtCurrency(toNum(f.Net_Revenue_forecast))}</td>
                  <td>{range(toNum(f.Net_Revenue_lo80), toNum(f.Net_Revenue_hi80))}</td>
                  <td>{fmtCurrency(toNum(f.Net_Profit_forecast))}</td>
                  <td>{range(toNum(f.Net_Profit_lo80), toNum(f.Net_Profit_hi80))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="card" style={{ maxWidth: 560 }}>
        <div className="field">
          <label>Weeks ahead (1-13)</label>
          <input type="number" min="1" max="13" value={weeks} onChange={(e) => setWeeks(e.target.value)} />
        </div>
        <button className="btn" disabled={pred.loading} onClick={() => runForecast(n)}>Run forecast</button>
        <div style={{ marginTop: 12 }}>
          {pred.loading && <span className="spinner" />}
          {pred.error && <div className="err">Prediction unavailable. Re-run the sync script and re-set the FORECAST_LOOKUP secret.</div>}
          {r && !pred.loading && (
            <div>
              <div>{t('Expected {revenue}: ')}<strong>{fmtCurrency(toNum(r.net_revenue))}</strong> in week {r.weeks_ahead ?? n}
                {' '}(range {range(toNum(r.lower), toNum(r.upper))})</div>
              <div>Expected Net Profit: <strong>{fmtCurrency(toNum(r.net_profit))}</strong>
                {' '}(range {range(toNum(r.profit_lower), toNum(r.profit_upper))})</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
''')

w("src/components/monitor/GoalProgress.jsx", r'''
import useGoalProgress from '../../hooks/useGoalProgress';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtValue, humanize, toNum } from '../../utils/formatters';

const ROWS = [
  ['net_profit_target', 'Weekly Net Profit', 'currency', 'profit'],
  ['net_revenue_target', 'Weekly {revenue}', 'currency', 'revenue'],
  ['cash_floor_weeks', 'Cash runway (weeks)', 'number1', null],
  ['ltv_cac_min', 'LTV to CAC (4-week avg)', 'ratio', null],
];

const statusColor = (s) => {
  const x = String(s || '');
  if (/behind|off|miss|fail|breach|below|low|critical/i.test(x)) return '#C0392B';
  if (/risk|watch|warn|monitor|near/i.test(x)) return '#E67E22';
  if (/track|ok|met|ahead|good|safe|healthy/i.test(x)) return '#27AE60';
  return '#7A8190';
};

export default function GoalProgress() {
  const t = useTerm();
  const { g, loading } = useGoalProgress();
  const [stored] = useLocalStorage('targets', null);
  if (loading) return <div className="note">Loading...</div>;
  if (!Object.keys(g).length) return <EmptyState />;
  return (
    <div className="grid cols3">
      {ROWS.map(([key, label, kind, local]) => {
        const x = g[key];
        if (!x) return null;
        const target = (local && stored && toNum(stored[local])) || toNum(x.target);
        const actual = toNum(x.actual_last_week ?? x.actual ?? x.actual_4w_avg);
        let pct = toNum(x.progress_pct);
        if (local && stored && toNum(stored[local]) && actual !== null) pct = (actual / toNum(stored[local])) * 100;
        const status = x.status ? humanize(String(x.status)) : null;
        return (
          <div key={key} className="card">
            <h3>{t(label)}</h3>
            <div className="kpi-value">{fmtValue(kind, actual)}</div>
            <div className="muted">Target: {target === null ? 'not set (see My Targets)' : fmtValue(kind, target)}
              {toNum(x.actual_4w_avg) !== null && key.includes('_target') ? ' | 4-week avg: ' + fmtValue(kind, toNum(x.actual_4w_avg)) : ''}</div>
            {pct !== null && <div className="progress" style={{ margin: '8px 0' }}><div style={{ width: Math.min(100, Math.max(0, pct)) + '%' }} /></div>}
            {pct !== null && <div>{pct.toFixed(0)}% of target</div>}
            {status && <strong style={{ color: statusColor(x.status) }}>{status}</strong>}
          </div>
        );
      })}
    </div>
  );
}
''')

# AlertCenter: only two small edits (defaults from the real goals schema, no false "Run main.py" message)
p = os.path.join(PKG, "src/components/monitor/AlertCenter.jsx")
if os.path.isfile(p):
    with open(p, encoding="utf-8") as f:
        s = f.read()
    a1 = s.index("  const eff = stored || {")
    a2 = s.index("  };", a1) + 4
    s = s[:a1] + "  const eff = stored || { drop: thresholds.drop ?? 15, weeks: thresholds.weeks ?? 8 };" + s[a2:]
    s = s.replace("      {!loading && !alerts.length && <EmptyState />}\n", "")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    N[0] += 1

print("\nFiles written/patched: %d" % N[0])
print("Next:  python a.py   (re-syncs data + rebuilds forecast_lookup.json)")
print("       cd %s && npm run dev     (hard refresh with Ctrl+F5)" % PKG)
print("       Production: npx wrangler secret put FORECAST_LOOKUP  (paste new forecast_lookup.json)")