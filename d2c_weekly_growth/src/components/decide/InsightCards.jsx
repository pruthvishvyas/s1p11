import { useState } from 'react';
import useInsights from '../../hooks/useInsights';
import EmptyState from '../shared/EmptyState';
import SeverityBadge from '../shared/SeverityBadge';
import { SEV_RANK, humanize, sevOf } from '../../utils/formatters';

export default function InsightCards() {
  const { insights, loading } = useInsights();
  const [cat, setCat] = useState('All');
  if (loading) return <div className="note">Loading...</div>;
  if (!insights.length) return <EmptyState />;
  const cats = ['All', ...new Set(insights.map((i) => String(i.category || 'Other')))];
  const list = insights
    .filter((i) => cat === 'All' || String(i.category || 'Other') === cat)
    .sort((a, b) => (SEV_RANK[sevOf(a)] ?? 3) - (SEV_RANK[sevOf(b)] ?? 3));
  return (
    <div>
      <div className="chips">
        {cats.map((c) => (
          <button key={c} className={'chip' + (cat === c ? ' on' : '')} onClick={() => setCat(c)}>{c === 'All' ? c : humanize(c)}</button>
        ))}
      </div>
      <div className="grid cols3">
        {list.map((i, n) => (
          <div key={i.id || n} className="card">
            <div style={{ marginBottom: 8 }}>
              <SeverityBadge level={sevOf(i)} />{' '}
              <span className="muted">{humanize(i.category || '')}</span>
            </div>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{i.finding}</div>
            {i.evidence && <div style={{ color: '#4A5160', marginBottom: 10 }}>{i.evidence}</div>}
            {i.action && <div style={{ background: '#FFF8E6', color: '#7A4B00', padding: 8, borderRadius: 6 }}>{i.action}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
