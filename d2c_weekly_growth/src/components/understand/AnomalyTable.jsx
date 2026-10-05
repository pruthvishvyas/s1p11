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
