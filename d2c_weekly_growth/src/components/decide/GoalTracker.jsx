import useGoals from '../../hooks/useGoals';
import useGoalProgress from '../../hooks/useGoalProgress';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import { fmtCurrency, toNum } from '../../utils/formatters';

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
  const { g } = useGoalProgress();
  const [stored, setStored] = useLocalStorage('targets', null);
  const eff = stored || { profit: targets.profit, revenue: targets.revenue };
  const profit = toNum(g.net_profit_target && g.net_profit_target.actual_last_week);
  const revenue = toNum(g.net_revenue_target && g.net_revenue_target.actual_last_week);
  return (
    <div style={{ maxWidth: 560 }}>
      <Row label="Weekly Net Profit target" target={eff.profit} actual={profit}
        onChange={(v) => setStored({ ...eff, profit: v })} />
      <Row label={t('Weekly {revenue} target')} target={eff.revenue} actual={revenue}
        onChange={(v) => setStored({ ...eff, revenue: v })} />
    </div>
  );
}
