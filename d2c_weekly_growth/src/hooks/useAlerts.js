import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useAlerts() {
  const s = useJson(DATA.alerts);
  return { ...s, alerts: asList(s.data, 'alerts', 'items') };
}
