import { useState } from 'react';
import useSimulations from '../../hooks/useSimulations';
import EmptyState from '../shared/EmptyState';
import { fmtNumber, fmtValue, toNum } from '../../utils/formatters';

const isExtra = (v) => v === true || (typeof v === 'string' && v !== '' && !/^(false|no|none|inside)$/i.test(v));

function nearest(list, f, target) {
  const tg = toNum(target);
  if (tg === null) return Math.floor(list.length / 2);
  let b = 0;
  list.forEach((s, i) => {
    if (Math.abs((toNum(s[f]) ?? 0) - tg) < Math.abs((toNum(list[b][f]) ?? 0) - tg)) b = i;
  });
  return b;
}

const CFG = {
  promo_discount_depth: {
    title: 'Promo discount depth', field: 'discount_rate_pct', label: 'Discount rate', unit: '%',
    base: (m, l) => nearest(l, 'discount_rate_pct', m.baseline_discount_rate_pct),
    outs: [['orders', 'Orders', 'number'], ['net_revenue', 'Net Revenue', 'currency'], ['net_profit', 'Net Profit', 'currency']],
  },
  cac_cap_scenarios: {
    title: 'Marketing spend level', field: 'spend_multiplier', label: 'Spend vs today', unit: 'x',
    base: (m, l) => nearest(l, 'spend_multiplier', 1),
    outs: [['weekly_spend', 'Weekly spend', 'currency'], ['net_revenue', 'Net Revenue', 'currency'],
      ['new_customers', 'New customers', 'number'], ['net_profit', 'Net Profit', 'currency'],
      ['marketing_pct_of_revenue', 'Marketing % of revenue', 'percent']],
  },
};

function Meta({ meta }) {
  const r2 = toNum(meta.model_r2 ?? meta.elasticity_model_r2);
  return (
    <>
      {r2 !== null && <div className="muted">Model fit (R&sup2;): {r2.toFixed(2)}</div>}
      {meta.caveat && <p className="muted">{meta.caveat}</p>}
    </>
  );
}

function SliderPanel({ cfg, meta, list }) {
  const rows = [...list].sort((a, b) => (toNum(a[cfg.field]) ?? 0) - (toNum(b[cfg.field]) ?? 0));
  const baseIdx = cfg.base(meta, rows);
  const [i, setI] = useState(baseIdx);
  const cur = rows[i] || rows[0];
  const base = rows[baseIdx];
  return (
    <div className="card">
      <h3>{cfg.title}</h3>
      <div className="field">
        <label>{cfg.label}: <strong>{fmtNumber(toNum(cur[cfg.field]), 2)}{cfg.unit}</strong>{i === baseIdx ? ' (current)' : ''}</label>
        <input type="range" min={0} max={rows.length - 1} step={1} value={i} onChange={(e) => setI(Number(e.target.value))} />
      </div>
      {isExtra(cur.extrapolation) && <div className="notice">Outside the range seen in your history, so treat this as a rough estimate.</div>}
      {cfg.outs.map(([k, lab, f]) => {
        const v = toNum(cur[k]);
        const b = toNum(base[k]);
        const d = v !== null && b !== null ? v - b : null;
        return (
          <div key={k}>{lab}: <strong>{fmtValue(f, v)}</strong>
            {d !== null && i !== baseIdx && <span className={d >= 0 ? 'up' : 'down'}> ({d >= 0 ? '+' : ''}{fmtValue(f, d)} vs current)</span>}
          </div>
        );
      })}
      <Meta meta={meta} />
    </div>
  );
}

function ShiftPanel({ meta, list }) {
  const pairs = [...new Set(list.map((s) => s.pair))];
  const [p, setP] = useState(pairs[0]);
  const rows = list.filter((s) => s.pair === p).sort((a, b) => (toNum(a.signed_step) ?? 0) - (toNum(b.signed_step) ?? 0));
  const ok = list.filter((s) => s.feasible !== false && !isExtra(s.extrapolation) && toNum(s.delta_net_profit) !== null)
    .sort((a, b) => b.delta_net_profit - a.delta_net_profit);
  const best = ok[0];
  return (
    <div className="card">
      <h3>Shift budget between channels</h3>
      {best && best.delta_net_profit > 0 && (
        <div className="notice">Best in-range move: shift {best.shift_pct_of_budget}% of budget from {best.from} to {best.to} ({fmtValue('currency', best.delta_net_profit)} weekly Net Profit).</div>
      )}
      <div className="field">
        <label>Channel pair</label>
        <select value={p} onChange={(e) => setP(e.target.value)}>{pairs.map((x) => <option key={x}>{x}</option>)}</select>
      </div>
      <div className="heat">
        <table>
          <thead><tr><th>Shift % of budget</th><th>Feasible</th><th>&Delta; Net Revenue</th><th>&Delta; Net Profit</th><th>Driver-model &Delta; profit</th><th>Note</th></tr></thead>
          <tbody>
            {rows.map((s, i) => (
              <tr key={i}>
                <td>{fmtNumber(toNum(s.signed_step) !== null ? toNum(s.signed_step) : toNum(s.shift_pct_of_budget), 1)}</td>
                <td>{s.feasible === false ? 'No' : 'Yes'}</td>
                <td>{fmtValue('currency', toNum(s.delta_net_revenue))}</td>
                <td>{fmtValue('currency', toNum(s.delta_net_profit))}</td>
                <td>{fmtValue('currency', toNum(s.driver_model_delta_net_profit))}</td>
                <td>{isExtra(s.extrapolation) ? 'Outside observed range' : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Meta meta={meta} />
    </div>
  );
}

export default function WhatIfSimulator() {
  const { sims, loading } = useSimulations();
  if (loading) return <div className="note">Loading...</div>;
  if (!sims.length) return <EmptyState />;
  return (
    <div className="grid">
      {sims.map((s) => {
        const d = s.data || {};
        const meta = d.meta || {};
        const list = Array.isArray(d.scenarios) ? d.scenarios : [];
        if (!list.length) return <div key={s.name} className="card"><EmptyState /></div>;
        if (s.name === 'channel_budget_shift') return <ShiftPanel key={s.name} meta={meta} list={list} />;
        const cfg = CFG[s.name];
        return cfg ? <SliderPanel key={s.name} cfg={cfg} meta={meta} list={list} /> : null;
      })}
    </div>
  );
}
