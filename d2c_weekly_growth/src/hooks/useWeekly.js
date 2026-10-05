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
