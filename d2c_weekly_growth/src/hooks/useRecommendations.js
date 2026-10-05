import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList } from '../utils/formatters';

export default function useRecommendations() {
  const s = useJson(DATA.recommendations);
  return { ...s, recs: asList(s.data, 'recommendations'), channels: asList(s.data, 'channel_priority') };
}
