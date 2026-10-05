import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, safe_div, compute_thresholds
import numpy as np
import pandas as pd


def _n(v, d=0):
    return f"{v:,.{d}f}"


def run_insights(config=CONFIG, df_feat=None, agg_promo=None, agg_month=None, **kwargs):
    """Phase 9: >=8 insights computed live, top 3 HIGH. Outputs: insights (list). Saved to reports/insights.json."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    df = df_feat.copy().sort_values(config['DATE_COL']).reset_index(drop=True)
    thr = kwargs.get('thresholds') or compute_thresholds(config, df)
    seg_priority = kwargs.get('seg_priority')
    channel_imp = kwargs.get('channel_importance') or {}
    drv = kwargs.get('driver_report') or {}
    fcr = kwargs.get('forecast_report') or {}
    clf = kwargs.get('clf_report') or {}
    CN = config['CHANNEL_NAMES']
    items = []

    def add(cat, finding, evidence, action, metric, impact):
        items.append({'category': cat, 'finding': finding, 'evidence': evidence, 'action': action,
                      'metric_value': float(metric) if metric is not None and np.isfinite(metric) else 0.0,
                      'outcome': 'DECIDE', '_impact': float(impact)})

    scale = float(df['Net_Profit'].abs().mean()) + 1.0

    # 1. Promo vs non-promo profit gap
    promo, non = df[df['promo_flag'] == 1], df[df['promo_flag'] == 0]
    if len(promo) and len(non):
        gap = float(promo['Net_Profit'].median() - non['Net_Profit'].median())
        loss_p = float(promo[config['TARGET_FLAG']].mean() * 100)
        loss_n = float(non[config['TARGET_FLAG']].mean() * 100)
        word = 'earn more' if gap >= 0 else 'earn less'
        add('Promo Profitability',
            f"Promo weeks {word} than normal weeks by {_n(abs(gap))} in median Net Profit.",
            f"Median Net Profit {_n(promo['Net_Profit'].median())} in {len(promo)} promo weeks vs {_n(non['Net_Profit'].median())} in {len(non)} normal weeks; loss-week rate {loss_p:.0f}% vs {loss_n:.0f}%.",
            'Keep promos that clear the normal-week profit level and cut discount depth on those that do not.' if gap < 0 else
            'Promos are profitable overall; protect depth limits and repeat the best events.',
            gap, min(1, abs(gap) / scale) + (0.25 if gap < 0 else 0.0))

    # 2. Best / worst promo type
    ap = agg_promo if agg_promo is not None else None
    if ap is not None:
        pe = ap[(ap[config['PROMO_COL']] != 'None') & (ap['weeks'] >= 2)]
        if len(pe) >= 2:
            b, w = pe.iloc[0], pe.iloc[-1]
            add('Promo Profitability',
                f"{b[config['PROMO_COL']]} is the strongest promo and {w[config['PROMO_COL']]} the weakest.",
                f"Median Net Profit {_n(b['median_net_profit'])} ({int(b['weeks'])} weeks) vs {_n(w['median_net_profit'])} ({int(w['weeks'])} weeks); weakest runs at {w['median_discount_rate_pct']:.1f}% median discount.",
                f"Repeat {b[config['PROMO_COL']]}; reprice or drop {w[config['PROMO_COL']]}.",
                float(b['median_net_profit'] - w['median_net_profit']),
                min(1, float(b['median_net_profit'] - w['median_net_profit']) / (2 * scale)))

    # 3. Channel driver importance
    if channel_imp:
        ordered = sorted(channel_imp.items(), key=lambda kv: kv[1], reverse=True)
        best, worst = ordered[0], ordered[-1]
        rel = 'reliable enough to act on' if drv.get('reliable') else 'weak (holdout R2 low), so treat as a hint to test'
        add('Channel Performance',
            f"{best[0]} spend is most associated with Net Profit; {worst[0]} the least.",
            f"Permutation importance share: {best[0]} {best[1] * 100:.0f}%, {worst[0]} {worst[1] * 100:.0f}%. Driver model holdout R2 {drv.get('holdout_r2', float('nan')):.2f}: {rel}.",
            f"Test a small budget move toward {best[0]} and watch weekly profit before scaling.",
            best[1], 0.35 + 0.4 * best[1] + (0.1 if drv.get('reliable') else 0.0))

    # 4. Marginal return by channel
    if seg_priority is not None and len(seg_priority) and seg_priority['marginal_return_recent'].notna().any():
        sp = seg_priority.dropna(subset=['marginal_return_recent']).sort_values('marginal_return_recent', ascending=False)
        top, bot = sp.iloc[0], sp.iloc[-1]
        add('Channel Performance',
            f"{top['channel']} returns the most revenue per extra unit of spend recently; {bot['channel']} the least.",
            f"Marginal return {top['marginal_return_recent']:.2f} ({top['channel']}, {top['share_last13'] * 100:.0f}% of spend) vs {bot['marginal_return_recent']:.2f} ({bot['channel']}, {bot['share_last13'] * 100:.0f}% of spend). Associated with, not proof of, cause.",
            f"Rule check: {top['action']} for {top['channel']}; {bot['action'].lower()} for {bot['channel']}.",
            float(top['marginal_return_recent']), 0.45)

    # 5. LTV_to_CAC trend
    l13, p13 = df['LTV_to_CAC'].tail(13).mean(), df['LTV_to_CAC'].iloc[-26:-13].mean()
    below = int((df['LTV_to_CAC'] < thr['LTV_CAC_MIN']).sum())
    d = (l13 - p13) / p13 * 100 if p13 else 0.0
    add('Customer Economics',
        f"LTV to CAC is {'improving' if d > 1 else ('declining' if d < -1 else 'stable')} at {l13:.1f} (last 13 weeks).",
        f"{l13:.2f} vs {p13:.2f} in the prior 13 weeks ({d:+.1f}%); {below} weeks below the {thr['LTV_CAC_MIN']:.1f} floor of {len(df)}.",
        'Acquisition pays back; keep funding it while watching CAC.' if l13 >= thr['LTV_CAC_MIN'] else 'Pause paid acquisition expansion and invest in Email/retention.',
        l13, 0.9 if l13 < thr['LTV_CAC_MIN'] else min(0.5, abs(d) / 50 + 0.2))

    # 6. Retention vs acquisition
    rr13, rrp = df['Repeat_Customer_Rate_pct'].tail(13).mean(), df['Repeat_Customer_Rate_pct'].iloc[-26:-13].mean()
    ns13 = df['new_customer_share'].tail(13).mean() * 100
    add('Customer Economics',
        f"{ns13:.0f}% of recent orders come from new customers; repeat rate is {rr13:.1f}%.",
        f"Repeat customer rate {rr13:.1f}% vs {rrp:.1f}% in the prior 13 weeks; new-customer share of orders {ns13:.1f}%.",
        'Shift effort toward retention (Email, loyalty) if growth depends mostly on paid acquisition.' if ns13 > 50 else 'Retention is carrying a good part of orders; protect it.',
        rr13, 0.4)

    # 7. Cash runway
    run_now = float(df['cash_runway_weeks'].iloc[-1])
    floor = config['THRESHOLDS']['CASH_FLOOR_WEEKS']
    mn = float(df['cash_runway_weeks'].min())
    add('Cash & Collections',
        f"Cash covers {run_now:.1f} weeks of payroll, opex and marketing ({'above' if run_now >= floor else 'BELOW'} the {floor:.0f}-week floor).",
        f"Cash balance {_n(df['Cash_Balance'].iloc[-1])}; lowest runway in history {mn:.1f} weeks; weeks under the floor: {int((df['cash_runway_weeks'] < floor).sum())}.",
        'Cash is safe; keep the floor as a guardrail for any spend increase.' if run_now >= floor else 'Slow discretionary spend and chase receivables until runway recovers.',
        run_now, 0.95 if run_now < floor else 0.3)

    # 8. DSO / collections
    dso_now, dso_avg = float(df['DSO_Days'].iloc[-1]), float(df['DSO_Days'].mean())
    add('Cash & Collections',
        f"Collections take {dso_now:.1f} days (history average {dso_avg:.1f}, limit {thr['DSO_MAX_DAYS']:.1f}).",
        f"AR outstanding {_n(df['AR_Outstanding'].iloc[-1])}; DSO above the limit in {int((df['DSO_Days'] > thr['DSO_MAX_DAYS']).sum())} of {len(df)} weeks.",
        'Chase receivables now.' if dso_now > thr['DSO_MAX_DAYS'] else 'Collections are within the normal range; keep monitoring.',
        dso_now, 0.65 if dso_now > thr['DSO_MAX_DAYS'] else 0.2)

    # 9. Seasonality
    am = agg_month if agg_month is not None else None
    if am is not None and len(am) >= 2:
        s, w = am.loc[am['avg_net_margin_pct'].idxmax()], am.loc[am['avg_net_margin_pct'].idxmin()]
        add('Seasonality',
            f"{s['month']} is the strongest month and {w['month']} the weakest by net margin.",
            f"Average Net Margin {s['avg_net_margin_pct']:.1f}% in {s['month']} vs {w['avg_net_margin_pct']:.1f}% in {w['month']}; loss-week rate {s['loss_week_rate'] * 100:.0f}% vs {w['loss_week_rate'] * 100:.0f}%.",
            f"Schedule big promos in or near {s['month']}; hold spend steady in {w['month']}.",
            float(s['avg_net_margin_pct'] - w['avg_net_margin_pct']), min(1, float(s['avg_net_margin_pct'] - w['avg_net_margin_pct']) / 20 + 0.3))

    # 10. Return rate
    ret13 = float(df['return_rate_pct'].tail(13).mean())
    n_hi = int((df['return_rate_pct'] > thr['RETURN_RATE_MAX_PCT']).sum())
    add('Customer Economics',
        f"Return rate is {ret13:.1f}% of gross revenue recently (limit {thr['RETURN_RATE_MAX_PCT']:.1f}%).",
        f"{n_hi} of {len(df)} weeks above the limit; returns cost {_n(df['Returns'].tail(13).sum())} over the last 13 weeks.",
        'Audit product quality or listing accuracy.' if ret13 > thr['RETURN_RATE_MAX_PCT'] else 'Returns are in the normal range; keep tracking after promos.',
        ret13, 0.6 if ret13 > thr['RETURN_RATE_MAX_PCT'] else 0.25)

    # 11. Anomalies
    if 'is_anomaly' in df.columns:
        an = df[df['is_anomaly'] == 1].sort_values('anomaly_score', ascending=False)
        ex = '; '.join(f"{r[config['ID_COL']]}: {r['anomaly_reason']}" for _, r in an.head(2).iterrows())
        add('Channel Performance',
            f"{len(an)} unusual weeks were flagged ({len(an) / len(df) * 100:.0f}% of history).",
            ex if ex else 'No anomalies.', 'Review the flagged weeks for tracking errors, stock-outs or one-off events before using them in plans.',
            len(an), 0.35)

    # 12. Forecast direction
    t = (fcr.get('targets') or {})
    if 'Net_Revenue' in t:
        r, p = t['Net_Revenue'], t.get('Net_Profit', {})
        chg = (fcr.get('direction') or {}).get('net_revenue_change_pct_vs_last_13w', 0.0)
        pt = p.get('next_13w_total')
        add('Seasonality',
            f"Next 13 weeks Net Revenue is forecast {('up' if chg > 0 else 'down')} {abs(chg):.1f}% vs the last 13 weeks.",
            f"Forecast {_n(r['next_13w_total'])} vs {_n(r['last_13w_actual_total'])} actual; method {r['method']}; Net Profit forecast {_n(pt) if pt is not None else 'n/a'} (method {p.get('method', 'n/a')}). Accuracy claim: revenue {r['accuracy_claim']}, profit {p.get('accuracy_claim')}.",
            'Plan the quarter on the forecast band, not a single number.', chg, min(1, abs(chg) / 25 + 0.3))

    # 13. Loss weeks and early warning
    n_loss = int(df[config['TARGET_FLAG']].sum())
    if clf:
        meth = clf.get('method')
        ev = (f"{n_loss} loss weeks of {len(df)}. Early-warning model ({clf.get('chosen')}): recall {clf.get('recall', 0) * 100:.0f}%, precision {clf.get('precision', 0) * 100:.0f}% (out-of-fold)."
              if meth == 'ml' else f"{n_loss} loss weeks of {len(df)}. {clf.get('reason', 'Rule-based flag only.')}")
    else:
        ev = f"{n_loss} loss weeks of {len(df)}."
    add('Promo Profitability', f"{n_loss} weeks lost money ({n_loss / len(df) * 100:.0f}% of history).", ev,
        'Review planned promo weeks flagged at risk before launch; confirm discount depth against the limit.', n_loss,
        min(1, n_loss / len(df) * 2.5))

    # severity: top 3 HIGH, next 5 MEDIUM, rest LOW
    items.sort(key=lambda x: x['_impact'], reverse=True)
    out = []
    for i, it in enumerate(items):
        it['severity'] = 'HIGH' if i < 3 else ('MEDIUM' if i < 8 else 'LOW')
        it['id'] = f'I{i + 1}'
        it.pop('_impact')
        out.append({k: it[k] for k in ['id', 'category', 'severity', 'finding', 'evidence', 'action', 'outcome', 'metric_value']})
    assert len(out) >= 8, 'Need at least 8 insights'
    save_json(config['INSIGHTS_JSON'], out)
    print(f"  Insights: {len(out)} | HIGH {sum(i['severity'] == 'HIGH' for i in out)} | saved {config['INSIGHTS_JSON']}")
    return {'insights': out}

