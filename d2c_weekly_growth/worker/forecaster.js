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
