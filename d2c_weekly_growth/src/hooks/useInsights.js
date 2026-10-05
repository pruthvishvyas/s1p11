import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useInsights() {
  const s = useJson(DATA.insights);
  return { ...s, insights: asList(s.data, 'insights', 'items') };
}
