import useRunLog from '../../hooks/useRunLog';
import { useOutcome } from '../../contexts/OutcomeContext';
import { PROJECT } from '../../utils/tabs';
import { timeAgo } from '../../utils/formatters';

export default function Header() {
  const { lastUpdated } = useRunLog();
  const { segment, setSegment } = useOutcome();
  return (
    <header className="header">
      <div>
        <h1>{PROJECT.name}</h1>
        <span className="muted">{lastUpdated ? 'Last updated: ' + timeAgo(lastUpdated) : 'Last updated: unknown'}</span>
      </div>
      {segment && (
        <div className="viewing">
          Viewing: {segment} weeks <button className="link" onClick={() => setSegment(null)}>Clear</button>
        </div>
      )}
    </header>
  );
}
