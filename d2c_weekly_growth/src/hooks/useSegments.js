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
