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
