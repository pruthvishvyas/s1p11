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
