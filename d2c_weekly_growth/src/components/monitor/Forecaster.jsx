import { Component, useState } from 'react';
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

class Boundary extends Component {
  constructor(p) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err) { return { err }; }
  render() {
    if (this.state.err) return <div className="card err">Forecaster error: {String(this.state.err.message || this.state.err)}</div>;
    return this.props.children;
  }
}

function Inner() {
  const t = useTerm();
  const { loading, fut, report, rowsFor } = useForecast();
  const [metric, setMetric] = useState('Net_Revenue');
  const [weeks, setWeeks] = useState(4);
  const [shown, setShown] = useState(null);
  const n = Math.min(13, Math.max(1, Math.round(Number(weeks) || 1)));
  const f = shown ? fut[shown - 1] : null;
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
        {loading ? <div className="note">Loading...</div> : !fut.length ? <EmptyState message="forecast.json has no 'forecast' rows" /> : (
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
              {fut.map((r, i) => (
                <tr key={i}>
                  <td>{String(r.Week_Start).slice(0, 10)}</td>
                  <td>{fmtCurrency(toNum(r.Net_Revenue_forecast))}</td>
                  <td>{range(toNum(r.Net_Revenue_lo80), toNum(r.Net_Revenue_hi80))}</td>
                  <td>{fmtCurrency(toNum(r.Net_Profit_forecast))}</td>
                  <td>{range(toNum(r.Net_Profit_lo80), toNum(r.Net_Profit_hi80))}</td>
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
        <button className="btn" disabled={!fut.length} onClick={() => setShown(n)}>Run forecast</button>
        <div style={{ marginTop: 12 }}>
          {shown && !f && <div className="err">No forecast row for week {shown}. forecast.json has {fut.length} rows.</div>}
          {f && (
            <div>
              <div>{t('Expected {revenue}: ')}<strong>{fmtCurrency(toNum(f.Net_Revenue_forecast))}</strong> in week {shown} ({String(f.Week_Start).slice(0, 10)})
                {' '}(range {range(toNum(f.Net_Revenue_lo80), toNum(f.Net_Revenue_hi80))})</div>
              <div>Expected Net Profit: <strong>{fmtCurrency(toNum(f.Net_Profit_forecast))}</strong>
                {' '}(range {range(toNum(f.Net_Profit_lo80), toNum(f.Net_Profit_hi80))})</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Forecaster() {
  return <Boundary><Inner /></Boundary>;
}
