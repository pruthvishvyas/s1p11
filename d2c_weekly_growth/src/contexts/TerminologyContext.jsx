import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { fetchJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { humanize } from '../utils/formatters';

const DEFAULTS = {"revenue": "Net Revenue", "customer": "Customer", "product": "Order", "transaction": "Order"};
const Ctx = createContext({ map: DEFAULTS, t: (s) => s });

export function TerminologyProvider({ children }) {
  const [map, setMap] = useState(DEFAULTS);

  useEffect(() => {
    fetchJson(DATA.terminology)
      .then((d) => {
        const src = d && typeof d === 'object' ? d.terminology || d : {};
        const clean = {};
        Object.keys(src).forEach((k) => { if (typeof src[k] === 'string') clean[k] = src[k]; });
        setMap({ ...DEFAULTS, ...clean });
      })
      .catch(() => { /* defaults already match the contract */ });
  }, []);

  const value = useMemo(() => {
    const t = (text) => {
      if (typeof text !== 'string') return text;
      if (typeof map[text] === 'string') return map[text];
      return text.replace(/\{(\w+)\}/g, (m, k) => (typeof map[k] === 'string' ? map[k] : m));
    };
    t.header = (col) => {
      const h = humanize(col);
      if (/^(net )?revenue$/i.test(h)) return map.revenue;
      if (/^customers?$/i.test(h)) return map.customer;
      if (/^(orders?|transactions?)$/i.test(h)) return map.transaction;
      return h;
    };
    t.map = map;
    return { map, t };
  }, [map]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useTerm = () => useContext(Ctx).t;
