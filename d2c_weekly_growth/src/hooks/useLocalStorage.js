import { useCallback, useState } from 'react';
import { readStore, writeStore } from '../utils/storage';

export default function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => readStore(key, initial));
  const set = useCallback((next) => {
    setValue(next);
    writeStore(key, next);
  }, [key]);
  return [value, set];
}
