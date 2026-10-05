import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.config import CONFIG
import numpy as np
import pandas as pd

SLIDES = []


def slide(n, title, *body):
    SLIDES.append((n, title, [b for b in body if b]))


def load(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def fmt(v, d=0):
    return f"{v:,.{d}f}"


def main():
    C = CONFIG
    if not os.path.exists(C['FEAT_CSV']):
        print(f"ERROR: {C['FEAT_CSV']} not found. Run: python main.py")
        sys.exit(1)
    df = pd.read_csv(C['FEAT_CSV'], parse_dates=[C['DATE_COL']]).sort_values(C['DATE_COL']).reset_index(drop=True)
    out = C['OUTPUT_DIR']
    S = load(os.path.join(out, 'meta', 'summary.json'), {})
    insights = load(C['INSIGHTS_JSON'], [])
    recs = (load(os.path.join(out, 'decide', 'recommendations.json'), {}) or {}).get('recommendations', [])
    seg = load(os.path.join(out, 'understand', 'segments.json'), {}) or {}
    sims = load(os.path.join(out, 'decide', 'simulations', 'promo_discount_depth.json'), {}) or {}
    thr = S.get('thresholds') or {}
    models = S.get('models', {})
    clf, drv, fc, sr = models.get('loss_week_classifier', {}), models.get('driver_model', {}), models.get('forecast', {}), models.get('segmentation', {})
    n, last52 = len(df), df.tail(52)
    d0, d1 = df[C['DATE_COL']].min().strftime('%Y-%m-%d'), df[C['DATE_COL']].max().strftime('%Y-%m-%d')
    promo, non = df[df['promo_flag'] == 1], df[df['promo_flag'] == 0]
    n_loss = int(df[C['TARGET_FLAG']].sum())

    slide(1, 'TITLE & HOOK', f"{C['DATASET_NAME']} - weekly channel, promo and cash analytics",
          f"{n} weeks of data ({d0} to {d1}), {len(C['EXPECTED_COLS'])} source columns, one row per week",
          'Domain: direct-to-consumer e-commerce. Target: Net_Profit (forecast also Net_Revenue).',
          f"Hook: {n_loss} of {n} weeks lost money. Which channels and promos are behind that?",
          'NOTE: this run used SYNTHETIC demo data.' if S.get('synthetic_data') else '')
    slide(2, 'BUSINESS PROBLEM', 'Marketing spend keeps growing, but it is unclear which channel and which promos actually make money, or whether cash is safe.',
          'Commercial friction: ROAS looks good on revenue while discounts and returns can erase profit.',
          'Core question: which spend mix and promo choices maximize Net_Profit while keeping Cash_Balance safe over the next 13 weeks?',
          'Outcomes: UNDERSTAND (health, regimes, anomalies), DECIDE (mix, promos, simulations), MONITOR (forecast, cash, alerts).')
    slide(3, 'DATASET OVERVIEW', f"Source: {'synthetic demo data' if S.get('synthetic_data') else C['RAW_CSV']}",
          f"Shape: {n} rows x {len(C['EXPECTED_COLS'])} columns; date range {d0} to {d1}",
          f"Promo weeks: {len(promo)} ({len(promo) / n * 100:.0f}%); normal weeks: {len(non)}",
          f"Loss weeks (Net_Profit < 0): {n_loss} ({n_loss / n * 100:.0f}%)",
          f"ROAS basis detected: {S.get('roas_basis')}; accounting identities checked in validation_report.json")
    slide(4, 'OVERALL PERFORMANCE', f"Last 52 weeks Net Revenue {fmt(last52['Net_Revenue'].sum())}, Net Profit {fmt(last52['Net_Profit'].sum())} "
          f"(margin {last52['Net_Profit'].sum() / max(1, last52['Net_Revenue'].sum()) * 100:.1f}%)",
          f"Average week: revenue {fmt(df['Net_Revenue'].mean())}, profit {fmt(df['Net_Profit'].mean())}, marketing {fmt(df[C['TOTAL_SPEND']].mean())}",
          f"ROAS {df['ROAS'].mean():.2f} (break-even {thr.get('ROAS_BREAKEVEN', 0) or 0:.2f}); CAC {df['CAC'].mean():.1f}; LTV to CAC {df['LTV_to_CAC'].mean():.1f}",
          f"Cash now {fmt(df['Cash_Balance'].iloc[-1])}, runway {df['cash_runway_weeks'].iloc[-1]:.1f} weeks")
    gap = promo['Net_Profit'].median() - non['Net_Profit'].median() if len(promo) and len(non) else 0.0
    slide(5, 'CORE FINDING', f"**Promo weeks earn {fmt(abs(gap))} {'more' if gap >= 0 else 'less'} median Net Profit than normal weeks** ({fmt(promo['Net_Profit'].median())} vs {fmt(non['Net_Profit'].median())}).",
          f"Median discount {promo['discount_rate_pct'].median():.1f}% in promo weeks vs {non['discount_rate_pct'].median():.1f}% normally; limit set at {thr.get('DISCOUNT_RATE_MAX_PCT', 0) or 0:.1f}%.",
          f"Loss-week rate: promo {promo[C['TARGET_FLAG']].mean() * 100 if len(promo) else 0:.0f}% vs normal {non[C['TARGET_FLAG']].mean() * 100 if len(non) else 0:.0f}%.",
          'Associations only: promos coincide with seasons and higher spend.')
    mt = df.groupby('month_num')['Net_Margin_pct'].mean()
    avg = df['Net_Margin_pct'].mean()
    nm = lambda m: pd.Timestamp(2000, int(m), 1).strftime('%b')
    top, bot = mt.sort_values(ascending=False).head(3), mt.sort_values().head(3)
    slide(6, 'DOMAIN DEEP DIVE', f"Average Net Margin {avg:.1f}%.",
          'Strongest months: ' + ', '.join(f"{nm(m)} {v:.1f}% ({v - avg:+.1f} pts)" for m, v in top.items()),
          'Weakest months: ' + ', '.join(f"{nm(m)} {v:.1f}% ({v - avg:+.1f} pts)" for m, v in bot.items()),
          f"Q4 weeks average margin {df.loc[df['is_q4'] == 1, 'Net_Margin_pct'].mean():.1f}% vs {df.loc[df['is_q4'] == 0, 'Net_Margin_pct'].mean():.1f}% rest of year.")
    prof = seg.get('profile', [])
    slide(7, 'WEEK REGIMES', *[f"{p['segment']}: {int(p['weeks'])} weeks, Net Margin {p['Net_Margin_pct']:.1f}%, Net Profit {fmt(p['Net_Profit'])}, loss-week rate {p['loss_week_rate'] * 100:.0f}%" for p in prof],
          'Regimes are labelled from each cluster\'s average Net_Margin_pct, best to worst.')
    best = None
    pts = [p for p in sims.get('scenarios', []) if not p.get('extrapolation')]
    if pts:
        best = max(pts, key=lambda p: p['net_profit'])
    slide(8, 'BUSINESS LOGIC', f"{len(recs)} rule-based recommendations produced (promo, channel, customer, quality).",
          *[f"{r['priority']}: {r['subject']} - {r['action']}" for r in recs[:4]],
          f"Simulation: within the observed discount range, modelled weekly profit peaks near {best['discount_rate_pct']:.0f}% discount ({fmt(best['net_profit'])})." if best else '',
          'Simulations are pre-computed lookups with observed-range warnings; they are not guarantees.')
    slide(9, 'ML CLASSIFIER', f"Loss-week early warning: method {clf.get('method')} ({clf.get('chosen', 'rule')}), time-series cross-validation.",
          f"Out-of-fold recall {clf.get('recall', 0) * 100:.0f}% (target {C['RECALL_TARGET'] * 100:.0f}%), precision {clf.get('precision', 0) * 100:.0f}%, AUC {clf.get('roc_auc', 0):.2f}" if clf.get('method') == 'ml' else clf.get('reason', 'Rule-based flag only.'),
          'Top features: ' + ', '.join(list((clf.get('top_features') or {}).keys())[:5]),
          f"Profit driver model holdout R2 {drv.get('holdout_r2', 0):.2f}, MAE {fmt(drv.get('holdout_mae', 0))}; channel importance: " + ', '.join(f"{k} {v * 100:.0f}%" for k, v in (drv.get('channel_importance') or {}).items()))
    slide(10, 'ML SEGMENTATION', f"Algorithm: KMeans on scaled ROAS, CAC, gross margin, discount rate, marketing % of revenue, conversion rate.",
          f"k = {sr.get('k')} (silhouette by k: {sr.get('silhouette_by_k')}); silhouette {sr.get('silhouette')} vs target {C['SILHOUETTE_TARGET']}",
          'Cluster definitions: ' + '; '.join(f"{p['segment']} (ROAS {p['ROAS']:.1f}, CAC {p['CAC']:.0f}, discount {p['discount_rate_pct']:.1f}%)" for p in prof))
    nr, npf = fc.get('Net_Revenue', {}), fc.get('Net_Profit', {})
    alerts = (load(os.path.join(out, 'monitor', 'alerts.json'), {}) or {}).get('alerts', [])
    slide(11, '13-WEEK OUTLOOK & ALERTS', f"Net Revenue: next 13 weeks {fmt(nr.get('next_13w_total', 0))} vs {fmt(nr.get('last_13w_actual_total', 0))} last 13 weeks; method {nr.get('method')}",
          f"Net Profit: next 13 weeks {fmt(npf.get('next_13w_total', 0))}; method {npf.get('method')}; accuracy claim {npf.get('accuracy_claim')}",
          f"Revenue MAPE shipped {nr.get('shipped_mape_pct')}% (target under {C['MAPE_TARGET_PCT']:.0f}%); model accepted: {nr.get('model_accepted')}",
          *[f"ALERT {a['severity']}: {a['message']}" for a in alerts[:3]], 'Alerts: none triggered.' if not alerts else '')
    slide(12, 'KEY INSIGHTS', *[f"[{i['severity']}] {i['finding']} Evidence: {i['evidence']}" for i in [x for x in insights if x['severity'] == 'HIGH'][:3]])
    steps, seen = [], set()
    for r in [r for r in recs if r['priority'] == 'HIGH'] + insights + recs:
        a = r['action']
        if a not in seen:
            seen.add(a)
            steps.append(a)
    slide(13, 'RECOMMENDATIONS', *[f"{i + 1}. {a}" for i, a in enumerate(steps[:5])])
    slide(14, 'TECHNICAL ARCH', 'Pipeline phases: ingest, clean, engineer, EDA, segmentation, classifier/anomaly/driver, predictor, business logic, insights, export.',
          'Modules: src/data, src/features, src/models, src/analytics, src/reporting; orchestrated by main.py.',
          'Frameworks: pandas, scikit-learn (KMeans, IsolationForest, GradientBoosting), matplotlib, openpyxl, Gradio.',
          'Outputs: output/{understand,decide,monitor,meta}, frontend_contract.json, Excel report. Runs in about a minute on a laptop.')

    lines = []
    for n_, title, body in sorted(SLIDES):
        lines.append(f"SLIDE {n_} — {title}")
        lines.extend(f"- {b}" for b in body)
        lines.append('')
    text = '\n'.join(lines)
    os.makedirs(os.path.dirname(C['PPT_REPORT']), exist_ok=True)
    with open(C['PPT_REPORT'], 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"Report: {C['PPT_REPORT']}\nLines: {len(text.splitlines())} | Chars: {len(text)} | Slides: {len(SLIDES)}")
    print("\nAI prompt: 'Convert ppt_report.txt into a PowerPoint deck: one slide per SLIDE heading, bullets as written, "
          "bold the **marked** text, add a simple chart where a number comparison appears, keep a clean professional theme.'")


if __name__ == '__main__':
    main()

