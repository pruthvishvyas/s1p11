import { useDir } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useCharts() {
  const s = useDir(DATA.charts);
  return { ...s, charts: s.items };
}
