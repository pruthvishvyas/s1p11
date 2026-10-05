import { useTerm } from '../../contexts/TerminologyContext';
import { dataErrors } from '../../utils/api';

export default function EmptyState({ message }) {
  const t = useTerm();
  const errs = Object.entries(dataErrors);
  return (
    <div className="empty" style={{ color: '#4A5160' }}>
      {message ? t(message) : t('Run main.py to generate your {revenue} data')}
      {errs.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: '#C0392B' }}>
          {errs.map(([u, e]) => <div key={u}>{u}: {e}</div>)}
        </div>
      )}
    </div>
  );
}
