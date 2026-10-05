import useGoalProgress from '../../hooks/useGoalProgress';
import useLocalStorage from '../../hooks/useLocalStorage';
import { useTerm } from '../../contexts/TerminologyContext';
import EmptyState from '../shared/EmptyState';
import { fmtValue, humanize, toNum } from '../../utils/formatters';

const ROWS = [
  ['net_profit_target', 'Weekly Net Profit', 'currency', 'profit'],
  ['net_revenue_target', 'Weekly {revenue}', 'currency', 'revenue'],
  ['cash_floor_weeks', 'Cash runway (weeks)', 'number1', null],
  ['ltv_cac_min', 'LTV to CAC (4-week avg)', 'ratio', null],
];

const statusColor = (s) => {
  const x = String(s || '');
  if (/behind|off|miss|fail|breach|below|low|critical/i.test(x)) return '#C0392B';
  if (/risk|watch|warn|monitor|near/i.test(x)) return '#E67E22';
  if (/track|ok|met|ahead|good|safe|healthy/i.test(x)) return '#27AE60';
  return '#7A8190';
};

export default function GoalProgress() {
  const t = useTerm();
  const { g, loading } = useGoalProgress();
  const [stored] = useLocalStorage('targets', null);
  if (loading) return <div className="note">Loading...</div>;
  if (!Object.keys(g).length) return <EmptyState />;
  return (
    <div className="grid cols3">
      {ROWS.map(([key, label, kind, local]) => {
        const x = g[key];
        if (!x) return null;
        const target = (local && stored && toNum(stored[local])) || toNum(x.target);
        const actual = toNum(x.actual_last_week ?? x.actual ?? x.actual_4w_avg);
        let pct = toNum(x.progress_pct);
        if (local && stored && toNum(stored[local]) && actual !== null) pct = (actual / toNum(stored[local])) * 100;
        const status = x.status ? humanize(String(x.status)) : null;
        return (
          <div key={key} className="card">
            <h3>{t(label)}</h3>
            <div className="kpi-value">{fmtValue(kind, actual)}</div>
            <div className="muted">Target: {target === null ? 'not set (see My Targets)' : fmtValue(kind, target)}
              {toNum(x.actual_4w_avg) !== null && key.includes('_target') ? ' | 4-week avg: ' + fmtValue(kind, toNum(x.actual_4w_avg)) : ''}</div>
            {pct !== null && <div className="progress" style={{ margin: '8px 0' }}><div style={{ width: Math.min(100, Math.max(0, pct)) + '%' }} /></div>}
            {pct !== null && <div>{pct.toFixed(0)}% of target</div>}
            {status && <strong style={{ color: statusColor(x.status) }}>{status}</strong>}
          </div>
        );
      })}
    </div>
  );
}
