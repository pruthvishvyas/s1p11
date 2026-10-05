import { useDir } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useSimulations() {
  const s = useDir(DATA.simulations);
  return { ...s, sims: s.items };
}
