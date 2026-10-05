import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TAB_HELP } from '../../manual/content';
import useLocalStorage from '../../hooks/useLocalStorage';

export default function HelpBar({ helpKey }) {
  const [open, setOpen] = useState(false);
  const h = TAB_HELP[helpKey];
  if (!h) return null;
  return (
    <div className="help-bar no-print">
      <button className="link" onClick={() => setOpen(!open)}>{open ? 'Hide help for this page' : 'How to read this page'}</button>
      {open && (
        <div className="help-box">
          <p><strong>What it shows.</strong> {h.what}</p>
          <p><strong>How to read it.</strong> {h.read}</p>
          <p><strong>What to do.</strong> {h.act}</p>
          <Link to="/help/manual">Open the full User Manual</Link>
        </div>
      )}
    </div>
  );
}

export function Welcome() {
  const [seen, setSeen] = useLocalStorage('welcome_seen', false);
  if (seen) return null;
  return (
    <div className="notice no-print" style={{ marginBottom: 16 }}>
      <strong>Welcome.</strong> Each page has a "How to read this page" link under its title, and a full{' '}
      <Link to="/help/manual">User Manual</Link> is in the HELP section of the menu.{' '}
      <button className="link" onClick={() => setSeen(true)}>Got it</button>
    </div>
  );
}
