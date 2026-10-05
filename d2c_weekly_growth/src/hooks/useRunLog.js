import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useRunLog() {
  const s = useJson(DATA.run_log);
  const runs = asList(s.data, 'runs', 'history', 'log');
  const last = runs[runs.length - 1];
  const lastUpdated =
    pick(last, 'timestamp', 'run_at', 'finished_at', 'time') ||
    pick(Array.isArray(s.data) ? null : s.data, 'timestamp', 'last_run', 'run_at');
  return { ...s, runs, lastUpdated };
}
