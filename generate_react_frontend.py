#!/usr/bin/env python3
"""generate_react_frontend.py - Specialized Skill 3: Weekly Growth & Profit React SaaS scaffold."""
import os
import sys
import json
import shutil
import textwrap
import datetime


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def load_contract():
    for p in ("frontend_contract.json", os.path.join("output", "frontend_contract.json")):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f), p
    die("frontend_contract.json not found (looked in ./ and ./output/)")


contract, CONTRACT_PATH = load_contract()
if contract.get("saas_ready") is not True:
    die("frontend_contract.json: 'saas_ready' is not true")

# (outcome, key, tab label, component) - sidebar order and labels live ONLY here.
TABS = [
    ("understand", "kpis", "This Week's Numbers", "KPICards"),
    ("understand", "charts", "Profit & Spend Charts", "ChartPanel"),
    ("understand", "anomalies", "Unusual Weeks", "AnomalyTable"),
    ("understand", "segments", "Week Types", "SegmentExplorer"),
    ("decide", "insights", "What's Happening", "InsightCards"),
    ("decide", "recommendations", "This Quarter's Actions", "RecommendationEngine"),
    ("decide", "simulations", "What If I...", "WhatIfSimulator"),
    ("decide", "goals", "My Targets", "GoalTracker"),
    ("monitor", "forecast", "13-Week Outlook", "Forecaster"),
    ("monitor", "goal_progress", "Target Progress", "GoalProgress"),
    ("monitor", "alerts", "My Alerts", "AlertCenter"),
]
OUTCOME_LABELS = [("understand", "UNDERSTAND"), ("decide", "DECIDE"), ("monitor", "MONITOR")]

REQUIRED = [("project", "name"), ("project", "domain"), ("project", "client_id"),
            ("terminology", "revenue"), ("terminology", "customer"),
            ("terminology", "product"), ("terminology", "transaction")]
REQUIRED += [("outcomes", o, k) for (o, k, _l, _c) in TABS]
for path in REQUIRED:
    node = contract
    for key in path:
        if not isinstance(node, dict) or key not in node:
            die("frontend_contract.json: missing field '%s'" % ".".join(path))
        node = node[key]

fields = contract.get("model", {}).get("input_fields")
if fields != ["weeks_ahead"]:
    print("WARNING: model.input_fields is %s; Skill 3 expects ['weeks_ahead']. "
          "The Forecaster UI and Worker use weeks_ahead (1-13) regardless." % (fields,))

PKG = contract["project"]["client_id"]
NAME = contract["project"]["name"]
DOMAIN = contract["project"]["domain"]
TERM = {k: contract["terminology"][k] for k in ("revenue", "customer", "product", "transaction")}
TODAY = datetime.date.today().isoformat()
REPL = {"__PKG__": PKG, "__NAME__": NAME, "__DATE__": TODAY, "__TERM_JSON__": json.dumps(TERM)}
COUNT = [0]


def write_file(rel, content):
    full = os.path.join(PKG, rel)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    text = textwrap.dedent(content).lstrip("\n")
    for k, v in REPL.items():
        text = text.replace(k, v)
    if not text.endswith("\n"):
        text += "\n"
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    COUNT[0] += 1


def data_url(p):
    p = p.replace("\\", "/")
    if p.startswith("output/"):
        p = p[len("output/"):]
    return "/data/" + p.lstrip("/")


DATA = {}
for _o, _k, _l, _c in TABS:
    DATA[_k] = data_url(contract["outcomes"][_o][_k])
for _k in ("charts", "simulations"):
    if not DATA[_k].endswith("/"):
        DATA[_k] += "/"
DATA["run_log"] = "/data/meta/run_log.json"
DATA["terminology"] = "/data/meta/terminology.json"
# ---- config files ----
write_file(".gitignore", r'''
node_modules/
dist/
.env
.wrangler/
''')

write_file(".env", r'''
VITE_DEV_AUTH=true
''')

write_file(".env.example", r'''
# Local development only. Never set this in production.
VITE_DEV_AUTH=true
''')


write_file("package.json", json.dumps({
    "name": PKG,
    "private": True,
    "version": "1.0.0",
    "type": "module",
    "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview",
                "deploy": "npm run build && wrangler deploy"},
    "dependencies": {"react": "^18.3.1", "react-dom": "^18.3.1", "react-router-dom": "^6.26.0",
                     "recharts": "^2.12.7", "@cloudflare/kv-asset-handler": "^0.3.4"},
    "devDependencies": {"@vitejs/plugin-react": "^4.3.1", "vite": "^5.4.0", "wrangler": "^3.78.0"},
}, indent=2))

write_file("wrangler.toml", r'''
name = "__PKG__"
main = "worker/forecaster.js"
compatibility_date = "__DATE__"

[site]
bucket = "./dist"
''')

write_file("vite.config.js", r'''
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

// Dev-only stand-in for the Worker /api route. Reads forecast_lookup.json from the project root.
function devForecastApi() {
  return {
    name: 'dev-forecast-api',
    configureServer(server) {
      server.middlewares.use('/api', (req, res) => {
        const send = (code, body) => {
          res.statusCode = code;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify(body));
        };
        if (req.method !== 'POST') return send(405, { error: 'POST only' });
        let raw = '';
        req.on('data', (c) => { raw += c; });
        req.on('end', () => {
          try {
            const weeks = Number(JSON.parse(raw || '{}').weeks_ahead);
            const p = path.resolve('forecast_lookup.json');
            if (!fs.existsSync(p)) return send(500, { error: 'forecast_lookup.json missing' });
            const table = JSON.parse(fs.readFileSync(p, 'utf-8'));
            const keys = Object.keys(table).map(Number).filter((n) => isFinite(n));
            if (!keys.length || !isFinite(weeks)) return send(400, { error: 'bad request or empty lookup' });
            let best = keys[0];
            for (const k of keys) if (Math.abs(k - weeks) < Math.abs(best - weeks)) best = k;
            return send(200, { weeks_ahead: best, ...table[String(best)] });
          } catch (e) {
            return send(500, { error: String(e) });
          }
        });
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), devForecastApi()],
  server: { port: 5173 },
});
''')

write_file("index.html", r'''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>__NAME__</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
''')

write_file("README.md", r'''
# __NAME__

Private weekly dashboard (React + Recharts) with a Cloudflare Worker for the 13-week forecaster.

## Local
    npm install
    npm run dev          # http://localhost:5173  (VITE_DEV_AUTH=true in .env)

## Forecast lookup
The Worker reads the secret FORECAST_LOOKUP, a JSON object keyed by weeks ahead:

    {"1": {"net_revenue": 0, "net_profit": 0, "lower": 0, "upper": 0}, "...": {}, "13": {}}

    npx wrangler secret put FORECAST_LOOKUP

## Cloudflare settings
- Root directory: `__PKG__/`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy`

`npm install` must be run once locally and `package-lock.json` committed, otherwise the Cloudflare build fails.
Spend and discount what-ifs are pre-computed JSON (DECIDE > What If I...), not Worker calls.
Currency symbol: change `CURRENCY` in `src/utils/formatters.js`.
''')
# ---- worker/forecaster.js ----
write_file("worker/forecaster.js", r'''
import { getAssetFromKV } from '@cloudflare/kv-asset-handler';
import manifestJSON from '__STATIC_CONTENT_MANIFEST';

const assetManifest = JSON.parse(manifestJSON);

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}

async function handleForecast(request, env) {
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
  if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

  let weeks;
  try {
    const body = await request.json();
    weeks = Number(body.weeks_ahead);
  } catch (e) {
    return json({ error: 'Invalid JSON body' }, 400);
  }
  if (!isFinite(weeks)) return json({ error: 'weeks_ahead must be a number between 1 and 13' }, 400);

  let table;
  try {
    table = JSON.parse(env.FORECAST_LOOKUP || '{}');
  } catch (e) {
    return json({ error: 'FORECAST_LOOKUP secret is not valid JSON' }, 500);
  }
  const keys = Object.keys(table).map(Number).filter((n) => isFinite(n));
  if (!keys.length) {
    return json({ error: 'FORECAST_LOOKUP is empty. Run: npx wrangler secret put FORECAST_LOOKUP' }, 500);
  }
  let best = keys[0];
  for (const k of keys) {
    if (Math.abs(k - weeks) < Math.abs(best - weeks)) best = k;
  }
  return json({ weeks_ahead: best, ...table[String(best)] });
}

async function serveAsset(request, env, ctx) {
  const options = { ASSET_NAMESPACE: env.__STATIC_CONTENT, ASSET_MANIFEST: assetManifest };
  const waitUntil = (p) => ctx.waitUntil(p);
  try {
    return await getAssetFromKV({ request, waitUntil }, options);
  } catch (e) {
    const url = new URL(request.url);
    if (/\.[A-Za-z0-9]+$/.test(url.pathname)) return new Response('Not found', { status: 404 });
    try {
      return await getAssetFromKV({ request: new Request(url.origin + '/index.html', request), waitUntil }, options);
    } catch (e2) {
      return new Response('Not found', { status: 404 });
    }
  }
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/api') return handleForecast(request, env);
    return serveAsset(request, env, ctx);
  },
};
''')
# ---- src/utils ----

tabs_js = (
    "export const PROJECT = %s;\n" % json.dumps({"name": NAME, "domain": DOMAIN, "client_id": PKG}, indent=2)
    + "export const DATA = %s;\n" % json.dumps(DATA, indent=2)
    + "export const OUTCOMES = %s;\n" % json.dumps(
        [{"id": i, "label": l} for i, l in OUTCOME_LABELS], indent=2)
    + "export const TABS = %s;\n" % json.dumps(
        [{"outcome": o, "key": k, "label": l, "component": c,
          "path": contract["outcomes"][o][k], "dataUrl": DATA[k]} for (o, k, l, c) in TABS], indent=2)
)
write_file("src/utils/tabs.js", tabs_js)

write_file("src/utils/formatters.js", r'''
export const CURRENCY = '\u20b9';

const nf = (d) => new Intl.NumberFormat('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });

export const isNum = (v) => typeof v === 'number' && isFinite(v);
export const toNum = (v) => {
  const n = typeof v === 'string' ? parseFloat(v) : v;
  return isNum(n) ? n : null;
};
export const fmtCurrency = (v) => (isNum(v) ? (v < 0 ? '-' : '') + CURRENCY + nf(0).format(Math.abs(v)) : '-');
export const fmtRatio = (v) => (isNum(v) ? nf(2).format(v) : '-');
export const fmtPercent = (v) => (isNum(v) ? nf(1).format(v) + '%' : '-');
export const fmtNumber = (v, d = 0) => (isNum(v) ? nf(d).format(v) : '-');

export function fmtValue(kind, v) {
  switch (kind) {
    case 'currency': return fmtCurrency(v);
    case 'percent': return fmtPercent(v);
    case 'ratio': return fmtRatio(v);
    case 'number1': return fmtNumber(v, 1);
    default: return fmtNumber(v, 0);
  }
}

export function pick(obj, ...keys) {
  if (!obj || typeof obj !== 'object') return undefined;
  for (const k of keys) {
    if (obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
}

export function asList(d, ...keys) {
  if (Array.isArray(d)) return d;
  if (d && typeof d === 'object') {
    for (const k of keys) if (Array.isArray(d[k])) return d[k];
  }
  return [];
}

export const humanize = (s) => String(s).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
export const SEV_RANK = { HIGH: 0, MEDIUM: 1, LOW: 2 };
export const sevOf = (o) => String(pick(o, 'severity', 'Severity', 'priority') || 'LOW').toUpperCase();

export function timeAgo(ts) {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return 'unknown';
  const hours = Math.floor((Date.now() - d.getTime()) / 3600000);
  if (hours < 1) return 'just now';
  if (hours < 48) return hours + (hours === 1 ? ' hour ago' : ' hours ago');
  return Math.floor(hours / 24) + ' days ago';
}
''')

write_file("src/utils/api.js", r'''
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
''')

write_file("src/utils/storage.js", r'''
const PREFIX = '__PKG__:';

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
''')
# ---- src/contexts ----
write_file("src/contexts/TerminologyContext.jsx", r'''
import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { fetchJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { humanize } from '../utils/formatters';

const DEFAULTS = __TERM_JSON__;
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
''')

write_file("src/contexts/OutcomeContext.jsx", r'''
import { createContext, useContext, useState } from 'react';

const Ctx = createContext({ segment: null, setSegment: () => {} });

export function OutcomeProvider({ children }) {
  const [segment, setSegment] = useState(null);
  return <Ctx.Provider value={{ segment, setSegment }}>{children}</Ctx.Provider>;
}

export const useOutcome = () => useContext(Ctx);
''')

write_file("src/contexts/AuthContext.jsx", r'''
import { createContext, useContext, useEffect, useState } from 'react';

const Ctx = createContext({ user: null, loading: true });

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // WARNING: without VITE_DEV_AUTH=true in .env, local dev has no Cloudflare Access identity
    // endpoint. The fetch fails, user stays null and protected routes bounce to /login
    // repeatedly (infinite-loop risk). Keep VITE_DEV_AUTH=true for local development only.
    if (import.meta.env.VITE_DEV_AUTH === 'true') {
      setUser({ email: 'dev@local' });
      setLoading(false);
      return undefined;
    }
    let off = false;
    (async () => {
      try {
        const res = await fetch('/cdn-cgi/access/get-identity');
        if (res.ok) {
          const d = await res.json();
          if (!off) setUser({ email: d.email || 'user' });
        }
      } catch (e) {
        if (!off) setUser(null);
      } finally {
        if (!off) setLoading(false);
      }
    })();
    return () => { off = true; };
  }, []);

  return <Ctx.Provider value={{ user, loading }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
''')
# ---- src/hooks ----
write_file("src/hooks/useKPIs.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, '');

export function findKpi(list, ...ids) {
  return list.find((k) => ids.includes(slug(k.key)));
}

function norm(d) {
  if (Array.isArray(d)) {
    return d.map((o) => ({ key: String(pick(o, 'key', 'name', 'metric', 'kpi') || ''), ...o }));
  }
  if (d && typeof d === 'object') {
    return Object.entries(d).map(([k, v]) =>
      v && typeof v === 'object' && !Array.isArray(v) ? { key: k, ...v } : { key: k, value: v });
  }
  return [];
}

export default function useKPIs() {
  const s = useJson(DATA.kpis);
  return { ...s, kpis: norm(s.data) };
}
''')

write_file("src/hooks/useCharts.js", r'''
import { useDir } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useCharts() {
  const s = useDir(DATA.charts);
  return { ...s, charts: s.items };
}
''')

write_file("src/hooks/useSegments.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


function norm(d) {
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.segments)) return d.segments;
  if (d && typeof d === 'object') {
    return Object.entries(d).filter(([, v]) => v && typeof v === 'object').map(([k, v]) => ({ segment: k, ...v }));
  }
  return [];
}

export default function useSegments() {
  const s = useJson(DATA.segments);
  const items = norm(s.data).map((o) => ({
    name: String(pick(o, 'segment', 'name', 'week_type', 'label', 'Week_Type') || ''),
    weeks: toNum(pick(o, 'weeks', 'n_weeks', 'count', 'week_count')),
    margin: toNum(pick(o, 'mean_net_margin', 'mean_net_margin_pct', 'net_margin', 'Net_Margin_pct')),
    roas: toNum(pick(o, 'mean_roas', 'roas', 'ROAS')),
    cac: toNum(pick(o, 'mean_cac', 'cac', 'CAC')),
  }));
  return { ...s, items };
}
''')

write_file("src/hooks/useAnomalies.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useAnomalies() {
  const s = useJson(DATA.anomalies);
  const rows = asList(s.data, 'rows', 'anomalies', 'items');
  const total = toNum(pick(Array.isArray(s.data) ? null : s.data, 'total_weeks', 'n_weeks', 'total'));
  return { ...s, rows, total };
}
''')

write_file("src/hooks/useInsights.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useInsights() {
  const s = useJson(DATA.insights);
  return { ...s, insights: asList(s.data, 'insights', 'items') };
}
''')

write_file("src/hooks/useRecommendations.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useRecommendations() {
  const s = useJson(DATA.recommendations);
  return { ...s, recs: asList(s.data, 'recommendations', 'items') };
}
''')

write_file("src/hooks/useSimulations.js", r'''
import { useDir } from '../utils/api';
import { DATA } from '../utils/tabs';

export default function useSimulations() {
  const s = useDir(DATA.simulations);
  return { ...s, sims: s.items };
}
''')

write_file("src/hooks/useGoals.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useGoals() {
  const s = useJson(DATA.goals);
  const g = s.data && typeof s.data === 'object' ? s.data : {};
  const targets = {
    profit: toNum(pick(g, 'weekly_net_profit_target', 'net_profit_target', 'profit_target')),
    revenue: toNum(pick(g, 'weekly_net_revenue_target', 'net_revenue_target', 'revenue_target')),
  };
  const thresholds = g.thresholds || g.alerts || g;
  return { ...s, targets, thresholds };
}
''')

write_file("src/hooks/useForecast.js", r'''
import { useCallback, useState } from 'react';
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { pick, toNum } from '../utils/formatters';

const X = (r) => pick(r, 'week', 'date', 'Week', 'week_start', 'label');

function buildRows(d) {
  if (!d) return [];
  const hist = Array.isArray(d) ? d : d.history || [];
  const fut = Array.isArray(d) ? [] : d.forecast || [];
  const rows = hist.map((r) => ({
    x: X(r),
    actual: toNum(pick(r, 'actual', 'net_revenue', 'Net_Revenue', 'value')),
    forecast: toNum(pick(r, 'forecast', 'predicted', 'yhat')),
    lower: toNum(pick(r, 'lower', 'lower_bound', 'yhat_lower')),
    upper: toNum(pick(r, 'upper', 'upper_bound', 'yhat_upper')),
  })).concat(fut.map((r) => ({
    x: X(r),
    actual: null,
    forecast: toNum(pick(r, 'forecast', 'net_revenue', 'Net_Revenue', 'predicted', 'yhat', 'value')),
    lower: toNum(pick(r, 'lower', 'lower_bound', 'yhat_lower')),
    upper: toNum(pick(r, 'upper', 'upper_bound', 'yhat_upper')),
  })));
  return rows.map((r) => ({ ...r, band: r.lower !== null && r.upper !== null ? [r.lower, r.upper] : null }));
}

export default function useForecast() {
  const s = useJson(DATA.forecast);
  const [pred, setPred] = useState({ loading: false, error: null, result: null });

  const runForecast = useCallback(async (weeksAhead) => {
    setPred({ loading: true, error: null, result: null });
    try {
      const res = await fetch('/api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weeks_ahead: weeksAhead }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const result = await res.json();
      setPred({ loading: false, error: null, result });
    } catch (error) {
      setPred({ loading: false, error, result: null });
    }
  }, []);

  return { ...s, rows: buildRows(s.data), pred, runForecast };
}
''')

write_file("src/hooks/useGoalProgress.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useGoalProgress() {
  const s = useJson(DATA.goal_progress);
  const rows = asList(s.data, 'rows', 'data', 'series').map((r) => ({
    x: pick(r, 'week', 'date', 'month', 'label'),
    actual: toNum(pick(r, 'actual', 'net_revenue')),
    target: toNum(pick(r, 'target')),
    projection: toNum(pick(r, 'projection', 'projected')),
  }));
  let behind = toNum(pick(Array.isArray(s.data) ? null : s.data, 'pct_behind', 'behind_pct'));
  if (behind === null) {
    const last = [...rows].reverse().find((r) => r.actual !== null && r.target);
    if (last) behind = ((last.target - last.actual) / last.target) * 100;
  }
  return { ...s, rows, behind };
}
''')

write_file("src/hooks/useAlerts.js", r'''
import { useJson } from '../utils/api';
import { DATA } from '../utils/tabs';
import { asList, pick, toNum } from '../utils/formatters';


export default function useAlerts() {
  const s = useJson(DATA.alerts);
  return { ...s, alerts: asList(s.data, 'alerts', 'items') };
}
''')

write_file("src/hooks/useRunLog.js", r'''
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
''')

write_file("src/hooks/useLocalStorage.js", r'''
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
''')
# ---- shared components + css ----
write_file("src/components/shared/SeverityBadge.jsx", r'''
const S = {
  HIGH: { bg: '#FDECEA', fg: '#C0392B' },
  MEDIUM: { bg: '#FEF3E2', fg: '#E67E22' },
  LOW: { bg: '#E8F6EE', fg: '#27AE60' },
};

export default function SeverityBadge({ level }) {
  const k = String(level || 'LOW').toUpperCase();
  const c = S[k] || S.LOW;
  return <span className="badge" style={{ background: c.bg, color: c.fg }}>{k}</span>;
}
''')

write_file("src/components/shared/EmptyState.jsx", r'''
import { useTerm } from '../../contexts/TerminologyContext';
import { dataErrors } from '../../utils/api';

export default function EmptyState({ message }) {
  const t = useTerm();
  const errs = Object.entries(dataErrors);
  return (
    <div className="empty" style={{ color: '#4A5160' }}>
      {message ? t(message) : t('Run main.py to generate your {revenue} data')}
      {errs.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#C0392B' }}>
          {errs.map(([u, e]) => <div key={u}>{u}: {e}</div>)}
        </div>
      )}
    </div>
  );
}
''')

write_file("src/components/shared/Header.jsx", r'''
import useRunLog from '../../hooks/useRunLog';
import { useOutcome } from '../../contexts/OutcomeContext';
import { PROJECT } from '../../utils/tabs';
import { timeAgo } from '../../utils/formatters';

export default function Header() {
  const { lastUpdated } = useRunLog();
  const { segment, setSegment } = useOutcome();
  return (
    <header className="header">
      <div>
        <h1>{PROJECT.name}</h1>
        <span className="muted">{lastUpdated ? 'Last updated: ' + timeAgo(lastUpdated) : 'Last updated: unknown'}</span>
      </div>
      {segment && (
        <div className="viewing">
          Viewing: {segment} weeks <button className="link" onClick={() => setSegment(null)}>Clear</button>
        </div>
      )}
    </header>
  );
}
''')

write_file("src/components/shared/Sidebar.jsx", r'''
import { NavLink } from 'react-router-dom';
import { PROJECT, TABS, OUTCOMES } from '../../utils/tabs';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">{PROJECT.name}</div>
      {OUTCOMES.map((o) => (
        <div key={o.id}>
          <div className="nav-group">{o.label}</div>
          {TABS.filter((t) => t.outcome === o.id).map((t) => (
            <NavLink key={t.key} to={'/' + t.outcome + '/' + t.key}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
              {t.label}
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}
''')

write_file("src/index.css", r'''
:root {
  --color-primary: #14213D; --color-accent: #F59E0B; --color-surface: #FFFFFF; --color-bg: #F5F6F8;
  --color-border: #E3E6EC; --color-text: #1A1A1A; --color-text-2: #4A5160; --color-text-3: #7A8190;
  --color-danger: #C0392B; --color-warning: #E67E22; --color-success: #27AE60;
  --chart-1: #14213D; --chart-2: #F59E0B; --chart-3: #27AE60; --chart-4: #E67E22; --chart-5: #C0392B; --chart-6: #7A8190;
  --font-head: 'DM Sans', system-ui, sans-serif; --font-body: 'Inter', system-ui, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); font-size: 14px; }
h1, h2, h3, .brand { font-family: var(--font-head); margin: 0; }
h1 { font-size: 20px; } h2 { font-size: 22px; margin-bottom: 16px; } h3 { font-size: 16px; margin-bottom: 8px; }
.shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
.sidebar { background: var(--color-primary); padding: 20px 12px; }
.brand { color: var(--color-surface); font-size: 18px; font-weight: 700; padding: 0 8px 20px; }
.nav-group { color: var(--color-accent); font-size: 11px; font-weight: 600; letter-spacing: .08em; padding: 16px 8px 6px; }
.nav-link { display: block; color: var(--color-border); text-decoration: none; padding: 8px; border-radius: 6px; }
.nav-link.active, .nav-link:hover { background: var(--color-text-2); color: var(--color-surface); }
.main { min-width: 0; }
.header { display: flex; justify-content: space-between; align-items: center; padding: 14px 24px; background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.content { padding: 24px; }
.muted { color: var(--color-text-3); font-size: 12px; }
.viewing { background: var(--color-bg); border: 1px solid var(--color-border); padding: 6px 10px; border-radius: 6px; color: var(--color-text-2); }
.link { background: none; border: 0; color: var(--color-primary); text-decoration: underline; cursor: pointer; }
.grid { display: grid; gap: 16px; }
.kpis { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); }
.cols3 { grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); }
.card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 10px; padding: 16px; }
.kpi-label { color: var(--color-text-2); font-size: 12px; }
.kpi-value { font-family: var(--font-head); font-size: 26px; font-weight: 700; margin: 4px 0; }
.up { color: var(--color-success); } .down { color: var(--color-danger); }
.kpi-warn { border-color: var(--color-warning); background: #FFF8F0; }
.warn-text { color: var(--color-warning); font-size: 12px; font-weight: 600; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.empty, .note { padding: 24px; text-align: center; }
.err { color: var(--color-danger); }
.chart-card { margin-bottom: 16px; }
.chart-box { width: 100%; height: 280px; }
table { width: 100%; border-collapse: collapse; background: var(--color-surface); }
th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--color-border); }
th { cursor: pointer; font-size: 12px; color: var(--color-text-2); }
tr.high td:first-child { border-left: 4px solid var(--color-danger); }
.pager { display: flex; gap: 8px; align-items: center; margin-top: 12px; }
.btn { background: var(--color-primary); color: var(--color-surface); border: 0; padding: 8px 14px; border-radius: 6px; cursor: pointer; }
.btn:disabled { opacity: .5; cursor: default; }
.btn.alt { background: var(--color-surface); color: var(--color-primary); border: 1px solid var(--color-border); }
input[type=number], input[type=text] { padding: 8px; border: 1px solid var(--color-border); border-radius: 6px; width: 140px; }
.field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
.progress { height: 10px; background: var(--color-border); border-radius: 5px; overflow: hidden; }
.progress > div { height: 100%; background: var(--color-accent); }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.chip { border: 1px solid var(--color-border); background: var(--color-surface); padding: 6px 12px; border-radius: 16px; cursor: pointer; }
.chip.on { background: var(--color-primary); color: var(--color-surface); }
.seg.on { outline: 2px solid var(--color-accent); } .seg { cursor: pointer; }
.notice { background: #FFF8E6; border: 1px solid var(--color-accent); color: var(--color-text); padding: 8px 10px; border-radius: 6px; margin: 8px 0; }
.done { text-decoration: line-through; color: var(--color-text-3); }
.spinner { width: 18px; height: 18px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.heat { overflow-x: auto; } .heat td { text-align: center; }
.center-note { padding: 60px; text-align: center; }
@media (max-width: 800px) { .shell { grid-template-columns: 1fr; } }
''')
# ---- UNDERSTAND components ----
write_file("src/components/understand/KPICards.jsx", r'''
import useKPIs from '../../hooks/useKPIs';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtValue, toNum, pick } from '../../utils/formatters';

const META = [
  { ids: ['netrevenue'], label: '{revenue}', kind: 'currency' },
  { ids: ['netprofit'], label: 'Net Profit', kind: 'currency' },
  { ids: ['netmargin', 'netmarginpct', 'netmarginpercent'], label: 'Net Margin %', kind: 'percent' },
  { ids: ['roas'], label: 'ROAS', kind: 'ratio' },
  { ids: ['cac'], label: '{customer} acquisition cost', kind: 'currency' },
  { ids: ['ltvtocac', 'ltvcac'], label: 'LTV to CAC', kind: 'ratio', warnBelow: 3, warnText: 'Below the 3.0 target' },
  { ids: ['cashbalance'], label: 'Cash Balance', kind: 'currency' },
  { ids: ['cashrunwayweeks', 'cashrunway', 'runwayweeks'], label: 'Cash runway (weeks)', kind: 'number1', warnBelow: 8, warnText: 'Under 8 weeks of cash' },
];
const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]/g, '');

export default function KPICards() {
  const t = useTerm();
  const { kpis, loading } = useKPIs();
  if (loading) return <div className="note">Loading...</div>;
  const cards = META.map((m) => ({ m, k: kpis.find((x) => m.ids.includes(slug(x.key))) })).filter((c) => c.k);
  if (!cards.length) return <EmptyState />;
  return (
    <div className="grid kpis">
      {cards.map(({ m, k }) => {
        const v = toNum(pick(k, 'value', 'current', 'latest'));
        let ch = toNum(pick(k, 'change_pct', 'trend_pct', 'delta_pct'));
        const prev = toNum(pick(k, 'prev_4wk_avg', 'previous', 'prev'));
        if (ch === null && prev !== null && prev !== 0 && v !== null) ch = ((v - prev) / Math.abs(prev)) * 100;
        const warn = m.warnBelow !== undefined && v !== null && v < m.warnBelow;
        return (
          <div key={m.label} className={'card' + (warn ? ' kpi-warn' : '')}>
            <div className="kpi-label">{t(m.label)}</div>
            <div className="kpi-value">{fmtValue(m.kind, v)}</div>
            {ch !== null && (
              <div className={ch >= 0 ? 'up' : 'down'}>
                {ch >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(ch).toFixed(1)}% vs previous 4 weeks
              </div>
            )}
            {warn && <div className="warn-text">{m.warnText}</div>}
          </div>
        );
      })}
    </div>
  );
}
''')

write_file("src/components/understand/ChartPanel.jsx", r'''
import useCharts from '../../hooks/useCharts';
import useGoals from '../../hooks/useGoals';
import { useOutcome } from '../../contexts/OutcomeContext';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { asList, humanize, isNum, pick, toNum } from '../../utils/formatters';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid, ReferenceLine,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;
const color = (i) => cssVar('--chart-' + ((i % 6) + 1));

function kindOf(name, c) {
  const ty = String((c && !Array.isArray(c) && c.type) || '').toLowerCase();
  if (['line', 'area', 'bar', 'heatmap'].includes(ty)) return ty;
  const n = name.toLowerCase();
  if (/heat|season|month/.test(n)) return 'heatmap';
  if (/mix|channel|spend/.test(n)) return 'area';
  if (/promo/.test(n)) return 'bar';
  return 'line';
}

function questionOf(name) {
  const n = name.toLowerCase();
  if (/cash/.test(n)) return 'Is my cash safe?';
  if (/cac|ltv|acquisition/.test(n)) return 'Is my {customer} acquisition paying back?';
  if (/promo/.test(n)) return 'Do promo weeks make or lose money?';
  if (/mix|channel|spend/.test(n)) return 'Where does my marketing money go?';
  if (/heat|season/.test(n)) return 'Which months and years perform best?';
  if (/growth|profit|revenue|trend/.test(n)) return 'Is my business growing profitably?';
  return humanize(name);
}

function Heatmap({ rows }) {
  const r0 = rows[0] || {};
  const long = pick(r0, 'year', 'Year') !== undefined && pick(r0, 'month', 'Month') !== undefined;
  let rowLabels = [];
  let cols = [];
  let cell = () => null;
  if (long) {
    const vk = Object.keys(r0).find((k) => !/^(year|month)$/i.test(k) && isNum(r0[k]));
    rowLabels = [...new Set(rows.map((r) => pick(r, 'month', 'Month')))];
    cols = [...new Set(rows.map((r) => pick(r, 'year', 'Year')))].sort();
    cell = (m, y) => {
      const f = rows.find((r) => pick(r, 'month', 'Month') === m && pick(r, 'year', 'Year') === y);
      return f ? toNum(f[vk]) : null;
    };
  } else {
    const lk = Object.keys(r0)[0];
    cols = Object.keys(r0).slice(1);
    rowLabels = rows.map((r) => r[lk]);
    cell = (m, y) => toNum((rows.find((r) => r[lk] === m) || {})[y]);
  }
  const vals = [];
  rowLabels.forEach((m) => cols.forEach((y) => { const v = cell(m, y); if (v !== null) vals.push(v); }));
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  return (
    <div className="heat">
      <table>
        <thead><tr><th>Month</th>{cols.map((y) => <th key={y}>{y}</th>)}</tr></thead>
        <tbody>
          {rowLabels.map((m) => (
            <tr key={m}>
              <td>{m}</td>
              {cols.map((y) => {
                const v = cell(m, y);
                const a = v === null || hi === lo ? 0 : (v - lo) / (hi - lo);
                return <td key={y} style={{ background: 'rgba(245,158,11,' + (0.1 + a * 0.7).toFixed(2) + ')' }}>{v === null ? '-' : v.toFixed(1)}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OneChart({ name, c, segment, floor }) {
  const t = useTerm();
  const kind = kindOf(name, c);
  const all = asList(c, 'data', 'rows', 'series_data');
  const rows = all.filter((r) => {
    const sv = pick(r, 'segment', 'Segment', 'Week_Type', 'week_type');
    return !segment || sv === undefined || String(sv).toLowerCase() === segment.toLowerCase();
  });
  const title = t(questionOf(name));
  if (!rows.length) return <div className="card chart-card"><h3>{title}</h3><EmptyState /></div>;
  if (kind === 'heatmap') return <div className="card chart-card"><h3>{title}</h3><Heatmap rows={rows} /></div>;

  const meta = Array.isArray(c) ? {} : c;
  const x = pick(meta, 'x', 'x_key') || Object.keys(rows[0])[0];
  const series = pick(meta, 'series', 'y') ||
    Object.keys(rows[0]).filter((k) => k !== x && isNum(rows[0][k]));
  let refs = pick(meta, 'reference_lines') || [];
  if (!refs.length && /ltv|acquisition|cac/i.test(name)) refs = [{ y: 3.0, label: 'LTV to CAC = 3.0' }];
  if (!refs.length && /cash/i.test(name) && isNum(floor)) refs = [{ y: floor, label: 'Runway floor' }];

  const common = { data: rows, margin: { top: 8, right: 16, left: 0, bottom: 0 } };
  const axes = [
    <CartesianGrid key="g" strokeDasharray="3 3" stroke={cssVar('--color-border')} />,
    <XAxis key="x" dataKey={x} tick={{ fontSize: 11 }} />,
    <YAxis key="y" tick={{ fontSize: 11 }} />,
    <Tooltip key="t" />,
    <Legend key="l" />,
    ...refs.map((r, i) => <ReferenceLine key={'r' + i} y={r.y} stroke={cssVar('--color-danger')} strokeDasharray="4 4" label={{ value: r.label, fontSize: 11 }} />),
  ];
  let chart;
  if (kind === 'area') {
    chart = <AreaChart {...common}>{axes}{series.map((s, i) => <Area key={s} type="monotone" dataKey={s} stackId="1" stroke={color(i)} fill={color(i)} fillOpacity={0.6} />)}</AreaChart>;
  } else if (kind === 'bar') {
    chart = <BarChart {...common}>{axes}{series.map((s, i) => <Bar key={s} dataKey={s} fill={color(i)} />)}</BarChart>;
  } else {
    chart = <LineChart {...common}>{axes}{series.map((s, i) => <Line key={s} type="monotone" dataKey={s} stroke={color(i)} dot={false} strokeWidth={2} />)}</LineChart>;
  }
  return (
    <div className="card chart-card">
      <h3>{title}</h3>
      <div className="chart-box"><ResponsiveContainer>{chart}</ResponsiveContainer></div>
    </div>
  );
}

export default function ChartPanel() {
  const { charts, loading } = useCharts();
  const { segment } = useOutcome();
  const { thresholds } = useGoals();
  if (loading) return <div className="note">Loading...</div>;
  if (!charts.length) return <EmptyState />;
  const floor = toNum(pick(thresholds, 'cash_runway_weeks', 'cash_runway_floor', 'runway_floor_weeks')) ?? 8;
  return <div>{charts.map((c) => <OneChart key={c.name} name={c.name} c={c.data} segment={segment} floor={floor} />)}</div>;
}
''')

write_file("src/components/understand/AnomalyTable.jsx", r'''
import { useMemo, useState } from 'react';
import useAnomalies from '../../hooks/useAnomalies';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { SEV_RANK, sevOf } from '../../utils/formatters';

const PAGE = 20;

export default function AnomalyTable() {
  const t = useTerm();
  const { rows, total, loading } = useAnomalies();
  const [sort, setSort] = useState({ key: '__sev', dir: 'desc' });
  const [page, setPage] = useState(0);

  const sorted = useMemo(() => {
    const a = [...rows];
    const f = sort.dir === 'asc' ? 1 : -1;
    a.sort((x, y) => {
      if (sort.key === '__sev') return (SEV_RANK[sevOf(x)] - SEV_RANK[sevOf(y)]) * (sort.dir === 'desc' ? 1 : -1);
      const p = x[sort.key];
      const q = y[sort.key];
      if (typeof p === 'number' && typeof q === 'number') return (p - q) * f;
      return String(p).localeCompare(String(q)) * f;
    });
    return a;
  }, [rows, sort]);

  if (loading) return <div className="note">Loading...</div>;
  if (!rows.length) return <EmptyState />;

  const cols = Object.keys(rows[0]);
  const pages = Math.max(1, Math.ceil(sorted.length / PAGE));
  const view = sorted.slice(page * PAGE, page * PAGE + PAGE);
  const pct = total ? ' , ' + ((rows.length / total) * 100).toFixed(1) + '% of all weeks' : '';
  const toggle = (key) => setSort((s) => ({ key, dir: s.key === key && s.dir === 'desc' ? 'asc' : 'desc' }));

  return (
    <div>
      <p>{rows.length} unusual weeks flagged{pct.replace(' ,', ',')}</p>
      <div className="heat">
        <table>
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c} onClick={() => toggle(/^severity$/i.test(c) ? '__sev' : c)}>
                  {t.header(c)}{sort.key === c || (sort.key === '__sev' && /^severity$/i.test(c)) ? (sort.dir === 'asc' ? ' \u25B2' : ' \u25BC') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {view.map((r, i) => (
              <tr key={i} className={sevOf(r) === 'HIGH' ? 'high' : ''}>
                {cols.map((c) => (
                  <td key={c}>{/^severity$/i.test(c) ? <SeverityBadge level={r[c]} /> : String(r[c])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <button className="btn alt" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page + 1} of {pages}</span>
        <button className="btn alt" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </div>
  );
}
''')

write_file("src/components/understand/SegmentExplorer.jsx", r'''
import useSegments from '../../hooks/useSegments';
import { useOutcome } from '../../contexts/OutcomeContext';
import EmptyState from '../shared/EmptyState';
import { fmtCurrency, fmtPercent, fmtRatio } from '../../utils/formatters';

const NAMES = ['Efficient', 'Steady', 'Burn'];

export default function SegmentExplorer() {
  const { items, loading } = useSegments();
  const { segment, setSegment } = useOutcome();
  if (loading) return <div className="note">Loading...</div>;
  if (!items.length) return <EmptyState />;
  return (
    <div>
      <p className="muted">Click a week type to filter the charts on the "Profit & Spend Charts" tab.</p>
      <div className="grid cols3">
        {NAMES.map((n) => {
          const s = items.find((i) => i.name.toLowerCase().includes(n.toLowerCase()));
          if (!s) return null;
          return (
            <div key={n} className={'card seg' + (segment === n ? ' on' : '')} onClick={() => setSegment(segment === n ? null : n)}>
              <h3>{n} weeks</h3>
              <div>Weeks: <strong>{s.weeks ?? '-'}</strong></div>
              <div>Mean Net Margin: <strong>{fmtPercent(s.margin)}</strong></div>
              <div>Mean ROAS: <strong>{fmtRatio(s.roas)}</strong></div>
              <div>Mean CAC: <strong>{fmtCurrency(s.cac)}</strong></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
''')
# ---- DECIDE components ----
write_file("src/components/decide/InsightCards.jsx", r'''
import { useState } from 'react';
import useInsights from '../../hooks/useInsights';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { SEV_RANK, pick, sevOf } from '../../utils/formatters';

const CATS = ['Channel Performance', 'Promo Profitability', 'Customer Economics', 'Cash & Collections', 'Seasonality'];

export default function InsightCards() {
  const { insights, loading } = useInsights();
  const [cat, setCat] = useState('All');
  if (loading) return <div className="note">Loading...</div>;
  if (!insights.length) return <EmptyState />;
  const list = insights
    .filter((i) => cat === 'All' || String(pick(i, 'category', 'Category')) === cat)
    .sort((a, b) => SEV_RANK[sevOf(a)] - SEV_RANK[sevOf(b)]);
  return (
    <div>
      <div className="chips">
        {['All', ...CATS].map((c) => (
          <button key={c} className={'chip' + (cat === c ? ' on' : '')} onClick={() => setCat(c)}>{c}</button>
        ))}
      </div>
      <div className="grid cols3">
        {list.map((i, n) => (
          <div key={n} className="card" style={{ background: '#FFFFFF' }}>
            <div style={{ marginBottom: 8 }}>
              <SeverityBadge level={sevOf(i)} />{' '}
              <span style={{ color: '#7A8190', fontSize: 12 }}>{pick(i, 'category', 'Category')}</span>
            </div>
            <div style={{ color: '#1A1A1A', fontWeight: 600, marginBottom: 6 }}>{pick(i, 'title', 'headline', 'finding')}</div>
            <div style={{ color: '#4A5160', marginBottom: 10 }}>{pick(i, 'detail', 'description', 'explanation', 'why')}</div>
            {pick(i, 'action', 'recommended_action') && (
              <div style={{ background: '#FFF8E6', color: '#7A4B00', padding: 8, borderRadius: 6 }}>
                {pick(i, 'action', 'recommended_action')}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
''')

write_file("src/components/decide/RecommendationEngine.jsx", r'''
import useRecommendations from '../../hooks/useRecommendations';
import useLocalStorage from '../../hooks/useLocalStorage';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { pick, sevOf } from '../../utils/formatters';

export default function RecommendationEngine() {
  const { recs, loading } = useRecommendations();
  const [done, setDone] = useLocalStorage('recs_done', []);
  if (loading) return <div className="note">Loading...</div>;
  if (!recs.length) return <EmptyState />;
  const idOf = (r, i) => String(pick(r, 'id', 'title', 'action') ?? i);
  const open = recs.map((r, i) => ({ r, id: idOf(r, i) })).filter((x) => !done.includes(x.id));
  const closed = recs.map((r, i) => ({ r, id: idOf(r, i) })).filter((x) => done.includes(x.id));
  const body = (r) => (
    <>
      <strong>{pick(r, 'title', 'action')}</strong>
      {pick(r, 'reason', 'rationale', 'why', 'detail') ? ': ' + pick(r, 'reason', 'rationale', 'why', 'detail') : ''}
    </>
  );
  return (
    <div>
      <div className="grid">
        {open.map(({ r, id }) => (
          <div key={id} className="card">
            <SeverityBadge level={sevOf(r)} /> <div style={{ margin: '8px 0' }}>{body(r)}</div>
            <button className="btn" onClick={() => setDone([...done, id])}>Mark done</button>
          </div>
        ))}
      </div>
      {closed.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Completed</h3>
          <div className="grid">
            {closed.map(({ r, id }) => (
              <div key={id} className="card done">
                {body(r)}{' '}
                <button className="link" onClick={() => setDone(done.filter((d) => d !== id))}>Undo</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
''')

write_file("src/components/decide/WhatIfSimulator.jsx", r'''
import { useMemo, useState } from 'react';
import useSimulations from '../../hooks/useSimulations';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtValue, humanize, isNum, pick, toNum } from '../../utils/formatters';

function Panel({ name, sim }) {
  const t = useTerm();
  const pairs = useMemo(
    () => Object.entries(sim.results || sim.lookup || sim.scenarios || {})
      .map(([k, v]) => [Number(k), v]).filter((p) => isFinite(p[0])).sort((a, b) => a[0] - b[0]),
    [sim]);
  const inp = sim.input || {};
  const [val, setVal] = useState(() =>
    pairs.length ? (toNum(pick(inp, 'default')) ?? pairs[Math.floor(pairs.length / 2)][0]) : 0);
  const title = sim.title || humanize(name);

  if (!pairs.length) return <div className="card"><h3>{title}</h3><EmptyState /></div>;

  const lo = toNum(pick(inp, 'min')) ?? pairs[0][0];
  const hi = toNum(pick(inp, 'max')) ?? pairs[pairs.length - 1][0];
  const step = toNum(pick(inp, 'step')) || (hi - lo) / 100 || 1;
  const unit = pick(inp, 'unit') || '';
  const label = pick(inp, 'label') || humanize(name);
  let best = pairs[0];
  for (const p of pairs) if (Math.abs(p[0] - val) < Math.abs(best[0] - val)) best = p;

  const obs = sim.observed_range;
  const olo = Array.isArray(obs) ? obs[0] : obs && obs.min;
  const ohi = Array.isArray(obs) ? obs[1] : obs && obs.max;
  const outside = isNum(olo) && isNum(ohi) && (val < olo || val > ohi);

  const item = best[1];
  const impact = toNum(item && typeof item === 'object' ? pick(item, 'impact', 'delta', 'net_profit_change', 'net_revenue_change', 'value') : item);
  const impactText = fmtValue(sim.format || 'currency', impact);
  const sentence = sim.sentence
    ? t(sim.sentence).replace('{value}', best[0] + unit).replace('{impact}', impactText)
    : t('With ' + label + ' at ' + best[0] + unit + ', the expected impact on {revenue} is ' + impactText + '.');

  return (
    <div className="card">
      <h3>{title}</h3>
      {sim.description && <p className="muted">{sim.description}</p>}
      <div className="field">
        <label>{label}: <strong>{val}{unit}</strong></label>
        <input type="range" min={lo} max={hi} step={step} value={val} onChange={(e) => setVal(Number(e.target.value))} />
      </div>
      {outside && <div className="notice">This value is outside the range seen in your data.</div>}
      <div className="kpi-value">{impactText}</div>
      <div>{sentence}</div>
      <div className="muted">Nearest pre-computed scenario: {best[0]}{unit}</div>
    </div>
  );
}

export default function WhatIfSimulator() {
  const { sims, loading } = useSimulations();
  if (loading) return <div className="note">Loading...</div>;
  if (!sims.length) return <EmptyState />;
  return <div className="grid cols3">{sims.map((s) => <Panel key={s.name} name={s.name} sim={s.data || {}} />)}</div>;
}
''')

write_file("src/components/decide/GoalTracker.jsx", r'''
import useGoals from '../../hooks/useGoals';
import useKPIs, { findKpi } from '../../hooks/useKPIs';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import { fmtCurrency, pick, toNum } from '../../utils/formatters';

function Row({ label, target, actual, onChange }) {
  const tgt = toNum(target);
  const pct = tgt && actual !== null ? Math.max(0, (actual / tgt) * 100) : null;
  const status = pct === null ? null : pct >= 100 ? 'On track' : pct >= 80 ? 'At risk' : 'Behind';
  const sc = { 'On track': '#27AE60', 'At risk': '#E67E22', Behind: '#C0392B' };
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="field">
        <label>{label}</label>
        <input type="number" value={target ?? ''} onChange={(e) => onChange(e.target.value)} />
      </div>
      {status === null ? (
        <div className="muted">Set your target to track progress</div>
      ) : (
        <>
          <div className="progress"><div style={{ width: Math.min(100, pct) + '%' }} /></div>
          <div style={{ marginTop: 6 }}>
            Latest week {fmtCurrency(actual)} of {fmtCurrency(tgt)} ({pct.toFixed(0)}%){' '}
            <strong style={{ color: sc[status] }}>{status}</strong>
          </div>
        </>
      )}
    </div>
  );
}

export default function GoalTracker() {
  const t = useTerm();
  const { targets } = useGoals();
  const { kpis } = useKPIs();
  const [stored, setStored] = useLocalStorage('targets', null);
  const eff = stored || { profit: targets.profit, revenue: targets.revenue };
  const profit = toNum(pick(findKpi(kpis, 'netprofit'), 'value', 'current', 'latest'));
  const revenue = toNum(pick(findKpi(kpis, 'netrevenue'), 'value', 'current', 'latest'));
  return (
    <div style={{ maxWidth: 560 }}>
      <Row label="Weekly Net Profit target" target={eff.profit} actual={profit}
        onChange={(v) => setStored({ ...eff, profit: v })} />
      <Row label={t('Weekly {revenue} target')} target={eff.revenue} actual={revenue}
        onChange={(v) => setStored({ ...eff, revenue: v })} />
    </div>
  );
}
''')
# ---- MONITOR components ----
write_file("src/components/monitor/Forecaster.jsx", r'''
import { useState } from 'react';
import useForecast from '../../hooks/useForecast';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtCurrency } from '../../utils/formatters';
import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;

export default function Forecaster() {
  const t = useTerm();
  const { rows, loading, pred, runForecast } = useForecast();
  const [weeks, setWeeks] = useState(4);
  const n = Math.min(13, Math.max(1, Math.round(Number(weeks) || 1)));
  const r = pred.result;

  return (
    <div>
      <div className="card chart-card">
        <h3>{t('{revenue}: history and 13-week outlook')}</h3>
        {loading ? <div className="note">Loading...</div> : !rows.length ? <EmptyState /> : (
          <div className="chart-box">
            <ResponsiveContainer>
              <ComposedChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
                <XAxis dataKey="x" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="band" name="Range" stroke="none" fill={cssVar('--color-accent')} fillOpacity={0.2} />
                <Line type="monotone" dataKey="actual" name="Actual" stroke={cssVar('--chart-1')} dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="forecast" name="Forecast" stroke={cssVar('--chart-2')} strokeDasharray="5 5" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      <div className="card" style={{ maxWidth: 560 }}>
        <div className="field">
          <label>Weeks ahead (1-13)</label>
          <input type="number" min="1" max="13" value={weeks} onChange={(e) => setWeeks(e.target.value)} />
        </div>
        <button className="btn" disabled={pred.loading} onClick={() => runForecast(n)}>Run forecast</button>
        <div style={{ marginTop: 12 }}>
          {pred.loading && <span className="spinner" />}
          {pred.error && <div className="err">Prediction unavailable. Ensure pipeline has run and worker is deployed.</div>}
          {r && !pred.loading && (
            <div>
              <div>
                {t('Expected {revenue}: ')}<strong>{fmtCurrency(r.net_revenue)}</strong> in week {r.weeks_ahead ?? n}
                {' '}(range {fmtCurrency(r.lower)} to {fmtCurrency(r.upper)})
              </div>
              <div>Expected Net Profit: <strong>{fmtCurrency(r.net_profit)}</strong></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
''')

write_file("src/components/monitor/GoalProgress.jsx", r'''
import useGoalProgress from '../../hooks/useGoalProgress';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from 'recharts';

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim() || undefined;

export default function GoalProgress() {
  const t = useTerm();
  const { rows, behind, loading } = useGoalProgress();
  if (loading) return <div className="note">Loading...</div>;
  if (!rows.length) return <EmptyState />;
  const sentence = behind === null ? null :
    behind > 0
      ? t('You are ' + behind.toFixed(0) + '% behind your {revenue} target this month')
      : t('You are ' + Math.abs(behind).toFixed(0) + '% ahead of your {revenue} target this month');
  return (
    <div className="card">
      {sentence && <h3>{sentence}</h3>}
      <div className="chart-box">
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={cssVar('--color-border')} />
            <XAxis dataKey="x" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="actual" name="Actual" stroke={cssVar('--chart-1')} dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="target" name="Target" stroke={cssVar('--chart-3')} dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="projection" name="Projection" stroke={cssVar('--chart-2')} strokeDasharray="5 5" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
''')

write_file("src/components/monitor/AlertCenter.jsx", r'''
import useAlerts from '../../hooks/useAlerts';
import useGoals from '../../hooks/useGoals';
import useRunLog from '../../hooks/useRunLog';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { pick, sevOf, toNum, timeAgo } from '../../utils/formatters';

export default function AlertCenter() {
  const t = useTerm();
  const { alerts, loading } = useAlerts();
  const { thresholds } = useGoals();
  const { runs } = useRunLog();
  const [stored, setStored] = useLocalStorage('alert_thresholds', null);
  const eff = stored || {
    drop: toNum(pick(thresholds, 'revenue_drop_pct', 'alert_revenue_drop_pct')) ?? 15,
    weeks: toNum(pick(thresholds, 'cash_runway_weeks', 'cash_runway_floor')) ?? 8,
  };
  const active = alerts.filter((a) => a.active !== false && String(a.status || '').toLowerCase() !== 'resolved');
  const history = runs.slice(-30).reverse();
  return (
    <div>
      <h3>Active alerts</h3>
      {loading ? <div className="note">Loading...</div> : !active.length ? (
        <div className="card" style={{ marginBottom: 16 }}>No active alerts.</div>
      ) : (
        <div className="grid" style={{ marginBottom: 16 }}>
          {active.map((a, i) => (
            <div key={i} className="card">
              <SeverityBadge level={sevOf(a)} />{' '}
              <strong>{pick(a, 'title', 'type', 'name')}</strong>
              <div>{pick(a, 'message', 'text', 'description')}</div>
            </div>
          ))}
        </div>
      )}
      {!loading && !alerts.length && <EmptyState />}
      <div className="card" style={{ maxWidth: 560, marginBottom: 16 }}>
        <h3>My alert thresholds</h3>
        <div className="field">
          <label>{t('Alert me if {revenue} drops by more than')} (%)</label>
          <input type="number" value={eff.drop} onChange={(e) => setStored({ ...eff, drop: e.target.value })} />
        </div>
        <div className="field">
          <label>Alert me if cash covers fewer than (weeks)</label>
          <input type="number" value={eff.weeks} onChange={(e) => setStored({ ...eff, weeks: e.target.value })} />
        </div>
      </div>
      <h3>History (last 30 runs)</h3>
      {!history.length ? <div className="muted">No runs logged yet.</div> : (
        <table>
          <thead><tr><th>When</th><th>Status</th><th>Alerts</th></tr></thead>
          <tbody>
            {history.map((r, i) => {
              const ts = pick(r, 'timestamp', 'run_at', 'finished_at', 'time');
              return (
                <tr key={i}>
                  <td>{ts ? String(ts) + ' (' + timeAgo(ts) + ')' : '-'}</td>
                  <td>{String(pick(r, 'status', 'result') ?? '-')}</td>
                  <td>{String(pick(r, 'alerts_fired', 'n_alerts', 'alerts') ?? '-')}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
''')
# ---- pages, App, main ----
write_file("src/pages/Dashboard.jsx", r'''
import { useParams } from 'react-router-dom';
import Sidebar from '../components/shared/Sidebar';
import Header from '../components/shared/Header';
import KPICards from '../components/understand/KPICards';
import ChartPanel from '../components/understand/ChartPanel';
import AnomalyTable from '../components/understand/AnomalyTable';
import SegmentExplorer from '../components/understand/SegmentExplorer';
import InsightCards from '../components/decide/InsightCards';
import RecommendationEngine from '../components/decide/RecommendationEngine';
import WhatIfSimulator from '../components/decide/WhatIfSimulator';
import GoalTracker from '../components/decide/GoalTracker';
import Forecaster from '../components/monitor/Forecaster';
import GoalProgress from '../components/monitor/GoalProgress';
import AlertCenter from '../components/monitor/AlertCenter';
import { TABS } from '../utils/tabs';

const REGISTRY = {
  KPICards, ChartPanel, AnomalyTable, SegmentExplorer, InsightCards, RecommendationEngine,
  WhatIfSimulator, GoalTracker, Forecaster, GoalProgress, AlertCenter,
};

export default function Dashboard() {
  const { outcome, tab } = useParams();
  const cur = TABS.find((t) => t.outcome === outcome && t.key === tab) || TABS[0];
  const Comp = REGISTRY[cur.component];
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <Header />
        <main className="content">
          <h2>{cur.label}</h2>
          <Comp />
        </main>
      </div>
    </div>
  );
}
''')

write_file("src/pages/Login.jsx", r'''
import { PROJECT } from '../utils/tabs';

export default function Login() {
  return (
    <div className="center-note">
      <h1>{PROJECT.name}</h1>
      <p>You need to sign in to view this dashboard. Access is managed by your administrator.</p>
      <button className="btn" onClick={() => window.location.assign('/')}>Try again</button>
    </div>
  );
}
''')

write_file("src/App.jsx", r'''
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { TerminologyProvider } from './contexts/TerminologyContext';
import { OutcomeProvider } from './contexts/OutcomeContext';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import { TABS } from './utils/tabs';

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-note">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const first = TABS[0];
  return (
    <BrowserRouter>
      <AuthProvider>
        <TerminologyProvider>
          <OutcomeProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/:outcome/:tab" element={<Protected><Dashboard /></Protected>} />
              <Route path="*" element={<Navigate to={'/' + first.outcome + '/' + first.key} replace />} />
            </Routes>
          </OutcomeProvider>
        </TerminologyProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
''')

write_file("src/main.jsx", r'''
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';

createRoot(document.getElementById('root')).render(<App />);
''')
# ---- data sync (NaN-safe copy, manifests, forecast lookup, schema report) ----

CLEANED = [0]
REV_K = ("forecast", "net_revenue", "Net_Revenue", "predicted", "yhat", "value", "pred")
PRO_K = ("net_profit", "Net_Profit", "forecast_net_profit", "profit")
LOW_K = ("lower", "lower_bound", "yhat_lower", "lo", "low")
UP_K = ("upper", "upper_bound", "yhat_upper", "hi", "high")


def _clean(o):
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        CLEANED[0] += 1
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def sync_dir(src, dst):
    # Browsers reject NaN/Infinity in JSON (Python/pandas write them), which blanks every tab.
    for root, _d, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(out, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            t = os.path.join(out, f)
            if f.lower().endswith(".json"):
                try:
                    with open(s, encoding="utf-8-sig") as fh:
                        obj = json.load(fh)
                    with open(t, "w", encoding="utf-8") as fh:
                        json.dump(_clean(obj), fh, allow_nan=False)
                except Exception as e:
                    print("WARNING: could not parse %s: %s" % (s, e))
            else:
                shutil.copy2(s, t)


def _num(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def _first(r, keys):
    if not isinstance(r, dict):
        return None
    for k in keys:
        if _num(r.get(k)) is not None:
            return _num(r.get(k))
    return None


def _build_lookup(base):
    p = os.path.join(base, "monitor", "forecast.json")
    if not os.path.isfile(p):
        print("WARNING: monitor/forecast.json missing - no forecast lookup written")
        return
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d, dict):
        fut = d.get("forecast") or d.get("future") or d.get("predictions") or []
    elif d and isinstance(d[0], dict) and "actual" in d[0]:
        fut = [r for r in d if _num(r.get("actual")) is None and _first(r, REV_K) is not None]
    else:
        fut = list(d)[-13:]
    table = {}
    for i, r in enumerate(fut[:13]):
        table[str(i + 1)] = {"net_revenue": _first(r, REV_K), "net_profit": _first(r, PRO_K),
                             "lower": _first(r, LOW_K), "upper": _first(r, UP_K)}
    if not table:
        print("WARNING: no future weeks found in forecast.json - write forecast_lookup.json by hand")
        return
    with open(os.path.join(PKG, "forecast_lookup.json"), "w", encoding="utf-8") as fh:
        json.dump(table, fh, indent=2)
    print("forecast_lookup.json written (%d weeks) -> used by npm run dev and by the Worker secret" % len(table))


def _describe(name, d):
    if isinstance(d, list):
        first = d[0] if d else None
        keys = list(first.keys()) if isinstance(first, dict) else repr(first)
        print("  %-26s list[%d] first item: %s" % (name, len(d), keys))
    elif isinstance(d, dict):
        print("  %-26s dict keys: %s" % (name, list(d.keys())[:14]))
        for k, v in list(d.items())[:14]:
            if isinstance(v, list) and v:
                print("       %-22s list[%d] first: %s" % (k, len(v), list(v[0].keys()) if isinstance(v[0], dict) else repr(v[0])))
            elif isinstance(v, dict):
                print("       %-22s dict keys: %s" % (k, list(v.keys())[:8]))
            else:
                print("       %-22s %r" % (k, v))
    else:
        print("  %-26s %s" % (name, type(d).__name__))


def _report(base):
    print("")
    print("SCHEMA REPORT (what is really in your output files):")
    for t in TABS:
        loc = os.path.join(PKG, "public", DATA[t[1]].lstrip("/"))
        if loc.endswith("/") or os.path.isdir(loc):
            for f in sorted(os.listdir(loc)) if os.path.isdir(loc) else []:
                if f.endswith(".json") and f != "index.json":
                    with open(os.path.join(loc, f), encoding="utf-8") as fh:
                        _describe(t[1] + "/" + f, json.load(fh))
        elif os.path.isfile(loc):
            with open(loc, encoding="utf-8") as fh:
                _describe(t[1], json.load(fh))
        else:
            print("  %-26s MISSING (%s)" % (t[1], loc))
    print("")


def sync_all():
    base = os.path.join(PKG, "public", "data")
    shutil.rmtree(base, ignore_errors=True)
    for sub in ("understand", "decide", "monitor", "meta"):
        src = os.path.join("output", sub)
        if os.path.isdir(src):
            sync_dir(src, os.path.join(base, sub))
        else:
            os.makedirs(os.path.join(base, sub), exist_ok=True)
            print("WARNING: %s not found - run the pipeline (main.py) first" % src)
    missing = []
    for t in TABS:
        p = contract["outcomes"][t[0]][t[1]]
        if p.endswith("/") or os.path.isdir(p):
            ok = os.path.isdir(p) and any(f.endswith(".json") for f in os.listdir(p))
        else:
            ok = os.path.isfile(p)
        if not ok:
            missing.append(p)
    if missing:
        print("WARNING: missing or empty pipeline outputs (these tabs will show 'Run main.py'):")
        for m in missing:
            print("   - " + m)
    for key in ("charts", "simulations"):
        d = os.path.join(PKG, "public", DATA[key].lstrip("/"))
        os.makedirs(d, exist_ok=True)
        names = sorted(f for f in os.listdir(d) if f.endswith(".json") and f != "index.json")
        with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
            json.dump(names, fh)
    _build_lookup(base)
    print("NaN/Infinity values replaced with null: %d" % CLEANED[0])
    _report(base)
# ---- summary ----

sync_all()
counts = dict((o, sum(1 for t in TABS if t[0] == o)) for o, _l in OUTCOME_LABELS)
print("Specialized React SaaS scaffold complete.")
print("  Client        : %s" % NAME)
print("  Domain        : %s" % DOMAIN)
print("  pkg_name      : %s" % PKG)
print("  Outcome tabs  : UNDERSTAND (%d) / DECIDE (%d) / MONITOR (%d)" % (
    counts["understand"], counts["decide"], counts["monitor"]))
print("  Terminology   : %s / %s / %s / %s" % (
    TERM["revenue"], TERM["customer"], TERM["product"], TERM["transaction"]))
print("  Files written : %d" % COUNT[0])
print("")
print("Next steps:")
print("  cd %s" % PKG)
print("  npm install                              <- REQUIRED: generates package-lock.json")
print("  npm run dev                              -> http://localhost:5173")
print("  git add . && git commit -m \"scaffold: %s SaaS\" && git push" % NAME)
print("  npx wrangler secret put FORECAST_LOOKUP  <- paste forecast JSON when prompted")
print("  npm run deploy                           -> live on Cloudflare")
