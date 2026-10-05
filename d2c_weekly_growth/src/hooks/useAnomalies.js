import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useAnomalies() {
  const s = useJson(DATA.anomalies);
  const rows = asList(s.data, 'rows', 'anomalies', 'items');
  const total = toNum(pick(Array.isArray(s.data) ? null : s.data, 'total_weeks', 'n_weeks', 'total'));
  return { ...s, rows, total };
}
