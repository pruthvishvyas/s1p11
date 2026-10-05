import { useEffect, useState } from 'react';

export const dataErrors = {};

export async function fetchJson(url) {
  let res;
  try {
    res = await fetch(url);
  } catch (e) {
    dataErrors[url] = 'network error';
    throw e;
  }
  if (!res.ok) {
    dataErrors[url] = 'HTTP ' + res.status;
    throw new Error('HTTP ' + res.status + ' for ' + url);
  }
  try {
    const d = await res.json();
    delete dataErrors[url];
    return d;
  } catch (e) {
    dataErrors[url] = 'not valid JSON (file missing, or contains NaN)';
    throw e;
  }
}

export function useJson(url) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  useEffect(() => {
    let off = false;
    setState({ data: null, loading: true, error: null });
    (async () => {
      try {
        const data = await fetchJson(url);
        if (!off) setState({ data, loading: false, error: null });
      } catch (error) {
        if (!off) setState({ data: null, loading: false, error });
      }
    })();
    return () => { off = true; };
  }, [url]);
  return state;
}

// Directories are read through the index.json manifest written by the scaffold script.
export function useDir(dirUrl) {
  const [state, setState] = useState({ items: [], loading: true, error: null });
  useEffect(() => {
    let off = false;
    (async () => {
      try {
        const files = await fetchJson(dirUrl + 'index.json');
        const items = [];
        for (const f of files) {
          try {
            items.push({ name: f.replace(/\.json$/, ''), data: await fetchJson(dirUrl + f) });
          } catch (e) { /* skip unreadable file */ }
        }
        if (!off) setState({ items, loading: false, error: null });
      } catch (error) {
        if (!off) setState({ items: [], loading: false, error });
      }
    })();
    return () => { off = true; };
  }, [dirUrl]);
  return state;
}
