const PREFIX = 'd2c_weekly_growth:';

export function readStore(key, fallback) {
  try {
    const v = window.localStorage.getItem(PREFIX + key);
    return v === null ? fallback : JSON.parse(v);
  } catch (e) {
    return fallback;
  }
}

export function writeStore(key, value) {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value));
    return true;
  } catch (e) {
    return false;
  }
}
