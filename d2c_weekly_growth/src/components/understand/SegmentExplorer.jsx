import useSegments from '../../hooks/useSegments';
import { useOutcome } from '../../contexts/OutcomeContext';
import EmptyState from '../shared/EmptyState';
import { fmtCurrency, fmtNumber, fmtPercent, fmtRatio, isNum } from '../../utils/formatters';

export default function SegmentExplorer() {
  const { items, report, loading } = useSegments();
  const { segment, setSegment } = useOutcome();
  if (loading) return <div className="note">Loading...</div>;
  if (!items.length) return <EmptyState />;
  return (
    <div>
      <p className="muted">
        Click a week type to filter the charts on the "Profit &amp; Spend Charts" tab.
        {isNum(report.silhouette) ? ' Cluster quality (silhouette): ' + report.silhouette.toFixed(2) + '.' : ''}
      </p>
      <div className="grid cols3">
        {items.map((s) => (
          <div key={s.id} className={'card seg' + (segment === s.label ? ' on' : '')}
            onClick={() => setSegment(segment === s.label ? null : s.label)}>
            <h3>{s.label} weeks</h3>
            <div>Weeks: <strong>{fmtNumber(s.weeks)}</strong></div>
            <div>Net margin: <strong>{fmtPercent(s.margin)}</strong></div>
            <div>ROAS: <strong>{fmtRatio(s.roas)}</strong></div>
            <div>CAC: <strong>{fmtCurrency(s.cac)}</strong></div>
            <div>Net profit: <strong>{fmtCurrency(s.profit)}</strong></div>
            <div>Net revenue: <strong>{fmtCurrency(s.revenue)}</strong></div>
            <div>Loss-week rate: <strong>{fmtNumber(s.lossRate, 2)}</strong></div>
          </div>
        ))}
      </div>
    </div>
  );
}
