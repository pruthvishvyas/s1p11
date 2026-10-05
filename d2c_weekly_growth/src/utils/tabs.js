export const PROJECT = {
  "name": "Weekly Growth & Profit",
  "domain": "d2c_ecommerce",
  "client_id": "d2c_weekly_growth"
};
export const DATA = {
  "kpis": "/data/understand/kpis.json",
  "charts": "/data/understand/charts/",
  "anomalies": "/data/understand/anomalies.json",
  "segments": "/data/understand/segments.json",
  "insights": "/data/decide/insights.json",
  "recommendations": "/data/decide/recommendations.json",
  "simulations": "/data/decide/simulations/",
  "goals": "/data/decide/goals.json",
  "forecast": "/data/monitor/forecast.json",
  "goal_progress": "/data/monitor/goal_progress.json",
  "alerts": "/data/monitor/alerts.json",
  "run_log": "/data/meta/run_log.json",
  "terminology": "/data/meta/terminology.json"
};
export const OUTCOMES = [
  {
    "id": "understand",
    "label": "UNDERSTAND"
  },
  {
    "id": "decide",
    "label": "DECIDE"
  },
  {
    "id": "monitor",
    "label": "MONITOR"
  }
];
export const TABS = [
  {
    "outcome": "understand",
    "key": "kpis",
    "label": "This Week's Numbers",
    "component": "KPICards",
    "path": "output/understand/kpis.json",
    "dataUrl": "/data/understand/kpis.json"
  },
  {
    "outcome": "understand",
    "key": "charts",
    "label": "Profit & Spend Charts",
    "component": "ChartPanel",
    "path": "output/understand/charts/",
    "dataUrl": "/data/understand/charts/"
  },
  {
    "outcome": "understand",
    "key": "anomalies",
    "label": "Unusual Weeks",
    "component": "AnomalyTable",
    "path": "output/understand/anomalies.json",
    "dataUrl": "/data/understand/anomalies.json"
  },
  {
    "outcome": "understand",
    "key": "segments",
    "label": "Week Types",
    "component": "SegmentExplorer",
    "path": "output/understand/segments.json",
    "dataUrl": "/data/understand/segments.json"
  },
  {
    "outcome": "decide",
    "key": "insights",
    "label": "What's Happening",
    "component": "InsightCards",
    "path": "output/decide/insights.json",
    "dataUrl": "/data/decide/insights.json"
  },
  {
    "outcome": "decide",
    "key": "recommendations",
    "label": "This Quarter's Actions",
    "component": "RecommendationEngine",
    "path": "output/decide/recommendations.json",
    "dataUrl": "/data/decide/recommendations.json"
  },
  {
    "outcome": "decide",
    "key": "simulations",
    "label": "What If I...",
    "component": "WhatIfSimulator",
    "path": "output/decide/simulations/",
    "dataUrl": "/data/decide/simulations/"
  },
  {
    "outcome": "decide",
    "key": "goals",
    "label": "My Targets",
    "component": "GoalTracker",
    "path": "output/decide/goals.json",
    "dataUrl": "/data/decide/goals.json"
  },
  {
    "outcome": "monitor",
    "key": "forecast",
    "label": "13-Week Outlook",
    "component": "Forecaster",
    "path": "output/monitor/forecast.json",
    "dataUrl": "/data/monitor/forecast.json"
  },
  {
    "outcome": "monitor",
    "key": "goal_progress",
    "label": "Target Progress",
    "component": "GoalProgress",
    "path": "output/monitor/goal_progress.json",
    "dataUrl": "/data/monitor/goal_progress.json"
  },
  {
    "outcome": "monitor",
    "key": "alerts",
    "label": "My Alerts",
    "component": "AlertCenter",
    "path": "output/monitor/alerts.json",
    "dataUrl": "/data/monitor/alerts.json"
  }
];
