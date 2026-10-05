import { useMemo, useState } from 'react';
import { TABS } from '../../utils/tabs';
import { EXTRA_TABS } from '../../utils/extraTabs';
import useKPIs from '../../hooks/useKPIs';
import useGoals from '../../hooks/useGoals';
import { fmtCurrency, isNum } from '../../utils/formatters';
import {
  TAB_HELP, QUICK_START, EXPLORER_STEPS, EXPLORER_EXAMPLE, GLOSSARY, FAQ, ACCURACY_NOTES,
} from '../../manual/content';

const LIMITS = [
  ['LTV_CAC_MIN', 'LTV to CAC should stay at or above', ''],
  ['ROAS_BREAKEVEN', 'ROAS break-even (below this, advertising does not pay for itself)', ''],
  ['DSO_MAX_DAYS', 'Customers should pay within (days)', ''],
  ['CASH_FLOOR_WEEKS', 'Cash should cover at least (weeks)', ''],
  ['DISCOUNT_RATE_MAX_PCT', 'Average discount should stay below (%)', ''],
  ['RETURN_RATE_MAX_PCT', 'Return rate should stay below (%)', ''],
];

export default function Manual() {
  const [q, setQ] = useState('');
  const { thresholds } = useKPIs();
  const { targets } = useGoals();
  const pages = TABS.concat(EXTRA_TABS).filter((t) => TAB_HELP[t.key]);
  const needle = q.trim().toLowerCase();
  const hit = (...parts) => !needle || parts.join(' ').toLowerCase().includes(needle);

  const sections = useMemo(() => [
    { id: 'start', title: 'Quick start', show: hit('quick start', ...QUICK_START) },
    { id: 'pages', title: 'Page by page', show: pages.some((t) => hit(t.label, TAB_HELP[t.key].what, TAB_HELP[t.key].read, TAB_HELP[t.key].act)) },
    { id: 'explorer', title: 'Using the Interactive Explorer', show: hit('explorer', ...EXPLORER_STEPS, EXPLORER_EXAMPLE) },
    { id: 'glossary', title: 'Glossary', show: GLOSSARY.some((g) => hit(g[0], g[1])) },
    { id: 'limits', title: 'Your current limits', show: hit('limits thresholds targets', ...LIMITS.map((l) => l[1])) },
    { id: 'faq', title: 'Questions and troubleshooting', show: FAQ.some((f) => hit(f[0], f[1])) },
    { id: 'accuracy', title: 'Reading the numbers responsibly', show: hit('accuracy', ...ACCURACY_NOTES) },
  ], [needle]); // eslint-disable-line react-hooks/exhaustive-deps
  const visible = sections.filter((s) => s.show);

  return (
    <div className="manual">
      <div className="no-print" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <input type="text" style={{ width: 280 }} placeholder="Search the manual (for example: DSO)" value={q} onChange={(e) => setQ(e.target.value)} />
        <button className="btn alt" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <div className="chips no-print">
        {visible.map((s) => <a key={s.id} className="chip" href={'#m-' + s.id} onClick={(e) => { e.preventDefault(); const el = document.getElementById('m-' + s.id); if (el) el.scrollIntoView({ behavior: 'smooth' }); }}>{s.title}</a>)}
      </div>
      {!visible.length && <div className="card">Nothing in the manual matches "{q}".</div>}

      {sections.find((s) => s.id === 'start').show && (
        <section id="m-start" className="card man-sec">
          <h3>Quick start</h3>
          <p>This dashboard answers three questions: what happened (UNDERSTAND), what should I do (DECIDE), and what should I watch (MONITOR). Data is refreshed each time your analysis pipeline runs.</p>
          <ol>{QUICK_START.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <p className="muted">Colour guide: green means good or improving, orange means watch, red means a problem or decline.</p>
        </section>
      )}

      {sections.find((s) => s.id === 'pages').show && (
        <section id="m-pages" className="card man-sec">
          <h3>Page by page</h3>
          {pages.filter((t) => hit(t.label, TAB_HELP[t.key].what, TAB_HELP[t.key].read, TAB_HELP[t.key].act)).map((t) => (
            <div key={t.key} className="man-item">
              <h4>{t.label}</h4>
              <p><strong>What it shows.</strong> {TAB_HELP[t.key].what}</p>
              <p><strong>How to read it.</strong> {TAB_HELP[t.key].read}</p>
              <p><strong>What to do.</strong> {TAB_HELP[t.key].act}</p>
            </div>
          ))}
        </section>
      )}

      {sections.find((s) => s.id === 'explorer').show && (
        <section id="m-explorer" className="card man-sec">
          <h3>Using the Interactive Explorer</h3>
          <ol>{EXPLORER_STEPS.map((s, i) => <li key={i}>{s}</li>)}</ol>
          <p>{EXPLORER_EXAMPLE}</p>
        </section>
      )}

      {sections.find((s) => s.id === 'glossary').show && (
        <section id="m-glossary" className="card man-sec">
          <h3>Glossary</h3>
          <dl>
            {GLOSSARY.filter((g) => hit(g[0], g[1])).map((g) => (
              <div key={g[0]} className="man-item"><dt><strong>{g[0]}</strong></dt><dd>{g[1]}</dd></div>
            ))}
          </dl>
        </section>
      )}

      {sections.find((s) => s.id === 'limits').show && (
        <section id="m-limits" className="card man-sec">
          <h3>Your current limits</h3>
          <p className="muted">These values are read live from your analysis, so they always match what the dashboard uses to colour cards and raise alerts.</p>
          <table>
            <tbody>
              {LIMITS.map((l) => (
                <tr key={l[0]}><td>{l[1]}</td><td><strong>{isNum(thresholds[l[0]]) ? thresholds[l[0]] : 'not available'}</strong></td></tr>
              ))}
              <tr><td>Weekly Net Profit target</td><td><strong>{isNum(targets.profit) ? fmtCurrency(targets.profit) : 'set by you in My Targets'}</strong></td></tr>
              <tr><td>Weekly Net Revenue target</td><td><strong>{isNum(targets.revenue) ? fmtCurrency(targets.revenue) : 'set by you in My Targets'}</strong></td></tr>
            </tbody>
          </table>
        </section>
      )}

      {sections.find((s) => s.id === 'faq').show && (
        <section id="m-faq" className="card man-sec">
          <h3>Questions and troubleshooting</h3>
          {FAQ.filter((f) => hit(f[0], f[1])).map((f) => (
            <div key={f[0]} className="man-item"><p><strong>{f[0]}</strong></p><p>{f[1]}</p></div>
          ))}
        </section>
      )}

      {sections.find((s) => s.id === 'accuracy').show && (
        <section id="m-accuracy" className="card man-sec">
          <h3>Reading the numbers responsibly</h3>
          <ul>{ACCURACY_NOTES.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
      )}
    </div>
  );
}
