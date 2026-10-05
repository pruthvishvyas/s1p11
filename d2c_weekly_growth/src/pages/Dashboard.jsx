import { useParams } from 'react-router-dom';
import Sidebar from '../components/shared/Sidebar';
import Header from '../components/shared/Header';
import HelpBar, { Welcome } from '../components/shared/HelpBar';
import KPICards from '../components/understand/KPICards';
import ChartPanel from '../components/understand/ChartPanel';
import AnomalyTable from '../components/understand/AnomalyTable';
import SegmentExplorer from '../components/understand/SegmentExplorer';
import InsightCards from '../components/decide/InsightCards';
import RecommendationEngine from '../components/decide/RecommendationEngine';
import WhatIfSimulator from '../components/decide/WhatIfSimulator';
import GoalTracker from '../components/decide/GoalTracker';
import Forecaster from '../components/monitor/Forecaster';
import GoalProgress from '../components/monitor/GoalProgress';
import AlertCenter from '../components/monitor/AlertCenter';
import Explorer from '../components/explore/Explorer';
import Manual from '../components/help/Manual';
import { TABS } from '../utils/tabs';
import { EXTRA_TABS } from '../utils/extraTabs';

const REGISTRY = {
  KPICards, ChartPanel, AnomalyTable, SegmentExplorer, InsightCards, RecommendationEngine,
  WhatIfSimulator, GoalTracker, Forecaster, GoalProgress, AlertCenter, Explorer, Manual,
};

export default function Dashboard() {
  const { outcome, tab } = useParams();
  const all = TABS.concat(EXTRA_TABS);
  const cur = all.find((t) => t.outcome === outcome && t.key === tab) || TABS[0];
  const Comp = REGISTRY[cur.component];
  return (
    <div className="shell">
      <Sidebar />
      <div className="main">
        <Header />
        <main className="content">
          <Welcome />
          <h2>{cur.label}</h2>
          {cur.key !== 'manual' && <HelpBar key={cur.key} helpKey={cur.key} />}
          <Comp />
        </main>
      </div>
    </div>
  );
}
