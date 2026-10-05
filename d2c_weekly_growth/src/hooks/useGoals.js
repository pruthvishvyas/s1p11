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
