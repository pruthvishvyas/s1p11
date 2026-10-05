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
