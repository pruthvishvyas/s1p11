import { getAssetFromKV } from '@cloudflare/kv-asset-handler';
import manifestJSON from '__STATIC_CONTENT_MANIFEST';

const assetManifest = JSON.parse(manifestJSON);

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, mcp-session-id',
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS },
  });
}

// ---------------------------------------------------------------------------
// 1. Existing Legacy API Handler (/api)
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// 2. Claude Model Context Protocol (MCP) Integration
// ---------------------------------------------------------------------------
const MCP_TOOLS = [
  {
    name: 'get_d2c_summary',
    description: 'Get high-level summary metadata about the D2C dataset, models, date ranges, and thresholds.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_kpis',
    description: 'Fetch key D2C performance metrics including Net Revenue, Net Profit, ROAS, CAC, LTV/CAC, and Cash Balance.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'run_forecast',
    description: 'Calculate or retrieve a revenue and profit forecast for N weeks ahead (1 to 13 weeks).',
    inputSchema: {
      type: 'object',
      properties: {
        weeks_ahead: {
          type: 'number',
          description: 'Number of weeks ahead to forecast (1 to 13)',
        },
      },
      required: ['weeks_ahead'],
    },
  },
];

async function handleMcpToolCall(name, args, env) {
  if (name === 'get_d2c_summary') {
    return {
      dataset: 'D2C Weekly Growth & Profit',
      date_range: ['2022-10-03', '2026-09-21'],
      total_history_weeks: 208,
      thresholds: {
        LTV_CAC_MIN: 3.0,
        ROAS_BREAKEVEN: 1.8292,
        DSO_MAX_DAYS: 2.9,
        CASH_FLOOR_WEEKS: 8.0,
      },
      forecast_summary: {
        next_13w_revenue_projection: 2349057.75,
        last_13w_actual_revenue: 2279739.0,
        revenue_change_pct: '+3.04%',
        next_13w_profit_projection: 302308.29,
      },
    };
  }

  if (name === 'get_kpis') {
    return {
      kpis: [
        { label: 'Net Revenue', value: '$2,279,739', change_pct: '+18.05%', period: 'last 13 weeks' },
        { label: 'Net Profit', value: '$328,295', change_pct: '+74.65%', period: 'last 13 weeks' },
        { label: 'Net Margin %', value: '14.40%', change_pct: '+47.94%', period: 'last 13 weeks' },
        { label: 'ROAS', value: '8.20', change_pct: '+17.65%', period: 'last 13 weeks' },
        { label: 'CAC', value: '$23.64', change_pct: '-14.54%', period: 'last 13 weeks' },
        { label: 'LTV to CAC', value: '9.74', change_pct: '+21.59%', period: 'last 13 weeks' },
        { label: 'Cash Balance', value: '$1,574,870', change_pct: '+12.40%', period: 'latest week' },
        { label: 'Cash Runway (weeks)', value: '26.8 weeks', change_pct: '+11.78%', period: 'latest week' },
      ],
    };
  }

  if (name === 'run_forecast') {
    const weeks = Number(args?.weeks_ahead || 1);
    let table = {};
    try {
      table = JSON.parse(env.FORECAST_LOOKUP || '{}');
    } catch (e) {}

    const keys = Object.keys(table).map(Number).filter((n) => isFinite(n));
    if (keys.length > 0) {
      let best = keys[0];
      for (const k of keys) {
        if (Math.abs(k - weeks) < Math.abs(best - weeks)) best = k;
      }
      return { weeks_ahead: best, ...table[String(best)] };
    }

    // Default estimate if FORECAST_LOOKUP secret is not configured
    return {
      weeks_ahead: weeks,
      projected_weekly_revenue: 180696.75,
      projected_weekly_profit: 23254.48,
      note: 'Based on baseline 13-week moving average projection.',
    };
  }

  throw new Error(`Tool not found: ${name}`);
}

// Handles MCP JSON-RPC requests over HTTP/POST or SSE
async function handleMcpRpc(request, env) {
  if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });

  let rpc;
  try {
    rpc = await request.json();
  } catch (e) {
    return json({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' }, id: null }, 400);
  }

  const { jsonrpc, method, params, id } = rpc;

  // Initialize handshake
  if (method === 'initialize') {
    return json({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'D2C Weekly Growth MCP Server', version: '1.0.0' },
      },
    });
  }

  // Handle client notifications
  if (method === 'notifications/initialized') {
    return new Response(null, { status: 200, headers: CORS });
  }

  // List available tools
  if (method === 'tools/list') {
    return json({
      jsonrpc: '2.0',
      id,
      result: { tools: MCP_TOOLS },
    });
  }

  // Execute a tool call
  if (method === 'tools/call') {
    const { name, arguments: toolArgs } = params || {};
    try {
      const resultData = await handleMcpToolCall(name, toolArgs, env);
      return json({
        jsonrpc: '2.0',
        id,
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify(resultData, null, 2),
            },
          ],
        },
      });
    } catch (err) {
      return json({
        jsonrpc: '2.0',
        id,
        result: {
          content: [{ type: 'text', text: `Error executing tool: ${err.message}` }],
          isError: true,
        },
      });
    }
  }

  return json({ jsonrpc: '2.0', error: { code: -32601, message: `Method not found: ${method}` }, id }, 404);
}

// ---------------------------------------------------------------------------
// 3. Static Asset Handler
// ---------------------------------------------------------------------------
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

// ---------------------------------------------------------------------------
// 4. Main Worker Fetch Router
// ---------------------------------------------------------------------------
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // MCP Protocol Endpoints
    if (url.pathname === '/mcp' || url.pathname === '/mcp/v1' || url.pathname === '/sse') {
      return handleMcpRpc(request, env);
    }

    // Existing Forecast endpoint
    if (url.pathname === '/api') return handleForecast(request, env);

    // Default static file server
    return serveAsset(request, env, ctx);
  },
};
