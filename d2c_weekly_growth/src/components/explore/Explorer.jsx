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
