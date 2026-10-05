# Weekly Growth & Profit

Private weekly dashboard (React + Recharts) with a Cloudflare Worker for the 13-week forecaster.

## Local
    npm install
    npm run dev          # http://localhost:5173  (VITE_DEV_AUTH=true in .env)

## Forecast lookup
The Worker reads the secret FORECAST_LOOKUP, a JSON object keyed by weeks ahead:

    {"1": {"net_revenue": 0, "net_profit": 0, "lower": 0, "upper": 0}, "...": {}, "13": {}}

    npx wrangler secret put FORECAST_LOOKUP

## Cloudflare settings
- Root directory: `d2c_weekly_growth/`
- Build command: `npm run build`
- Deploy command: `npx wrangler deploy`

`npm install` must be run once locally and `package-lock.json` committed, otherwise the Cloudflare build fails.
Spend and discount what-ifs are pre-computed JSON (DECIDE > What If I...), not Worker calls.
Currency symbol: change `CURRENCY` in `src/utils/formatters.js`.
