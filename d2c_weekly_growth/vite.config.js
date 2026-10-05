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
