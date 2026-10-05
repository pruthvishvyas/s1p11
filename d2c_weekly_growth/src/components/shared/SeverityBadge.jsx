const S = {
  HIGH: { bg: '#FDECEA', fg: '#C0392B' },
  MEDIUM: { bg: '#FEF3E2', fg: '#E67E22' },
  LOW: { bg: '#E8F6EE', fg: '#27AE60' },
};

export default function SeverityBadge({ level }) {
  const k = String(level || 'LOW').toUpperCase();
  const c = S[k] || S.LOW;
  return <span className="badge" style={{ background: c.bg, color: c.fg }}>{k}</span>;
}
