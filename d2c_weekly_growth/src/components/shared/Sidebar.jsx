import { NavLink } from 'react-router-dom';
import { PROJECT, TABS, OUTCOMES } from '../../utils/tabs';
import { EXTRA_OUTCOMES, EXTRA_TABS } from '../../utils/extraTabs';

export default function Sidebar() {
  const groups = OUTCOMES.concat(EXTRA_OUTCOMES);
  const tabs = TABS.concat(EXTRA_TABS);
  return (
    <aside className="sidebar">
      <div className="brand">{PROJECT.name}</div>
      {groups.map((o) => (
        <div key={o.id}>
          <div className="nav-group">{o.label}</div>
          {tabs.filter((t) => t.outcome === o.id).map((t) => (
            <NavLink key={t.key} to={'/' + t.outcome + '/' + t.key}
              className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
              {t.label}
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}
