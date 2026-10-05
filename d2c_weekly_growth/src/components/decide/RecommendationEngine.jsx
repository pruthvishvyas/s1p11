import useRecommendations from '../../hooks/useRecommendations';
import useLocalStorage from '../../hooks/useLocalStorage';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { fmtNumber, humanize, sevOf } from '../../utils/formatters';

const cell = (v) => (typeof v === 'number' ? fmtNumber(v, 2) : v === null || v === undefined ? '-' : String(v));

export default function RecommendationEngine() {
  const { recs, channels, loading } = useRecommendations();
  const [done, setDone] = useLocalStorage('recs_done', []);
  if (loading) return <div className="note">Loading...</div>;
  if (!recs.length && !channels.length) return <EmptyState />;
  const all = recs.map((r) => ({ r, id: [r.scope, r.subject, r.rule, r.action].join('|') }));
  const open = all.filter((x) => !done.includes(x.id));
  const closed = all.filter((x) => done.includes(x.id));
  const body = (r) => (
    <>
      <div className="muted">{humanize(r.scope || '')}{r.subject ? ' \u00B7 ' + r.subject : ''}</div>
      <div style={{ margin: '4px 0' }}><strong>{r.action}</strong></div>
      {r.evidence && <div>{r.evidence}</div>}
      {r.rule && <div className="muted">Rule: {r.rule}</div>}
    </>
  );
  const cols = channels.length ? Object.keys(channels[0]).filter((k) => k !== 'rule') : [];
  return (
    <div>
      <div className="grid">
        {open.map(({ r, id }) => (
          <div key={id} className="card">
            <SeverityBadge level={sevOf(r)} />
            <div style={{ margin: '8px 0' }}>{body(r)}</div>
            <button className="btn" onClick={() => setDone([...done, id])}>Mark done</button>
          </div>
        ))}
      </div>
      {closed.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Completed</h3>
          <div className="grid">
            {closed.map(({ r, id }) => (
              <div key={id} className="card done">{body(r)}{' '}
                <button className="link" onClick={() => setDone(done.filter((d) => d !== id))}>Undo</button>
              </div>
            ))}
          </div>
        </div>
      )}
      {channels.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Channel priority</h3>
          <div className="heat">
            <table>
              <thead><tr>{cols.map((c) => <th key={c}>{humanize(c)}</th>)}</tr></thead>
              <tbody>{channels.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{cell(r[c])}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
