import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useGoalProgress() {
  const s = useJson(DATA.goal_progress);
  return { ...s, g: s.data && typeof s.data === 'object' ? s.data : {} };
}
