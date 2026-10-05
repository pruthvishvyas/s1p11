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
  const eff = stored || { drop: thresholds.drop ?? 15, weeks: thresholds.weeks ?? 8 };
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
