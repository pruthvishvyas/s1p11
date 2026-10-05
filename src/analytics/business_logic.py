import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, safe_div, compute_thresholds
import numpy as np
import pandas as pd
import joblib


# ------------------------------------------------------------------ elasticities
def _log_ols(d, ycol, xlog, extra):
    """Log-log OLS: log(y) ~ log(xlog) + extra. Returns (coef dict, r2)."""
    d = d.copy()
    d['t_scaled'] = d['t_index'] / max(1, len(d)) if 't_index' in d else np.arange(len(d)) / max(1, len(d))
    X = [np.ones(len(d))] + [np.log(d[c].clip(lower=1).values.astype(float)) for c in xlog] + [d[c].values.astype(float) for c in extra]
    X = np.column_stack(X)
    y = np.log(d[ycol].clip(lower=1).values.astype(float))
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    pred = X @ beta
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = float(1 - ((y - pred) ** 2).sum() / ss_tot) if ss_tot > 0 else 0.0
    return dict(zip(['const'] + list(xlog) + list(extra), beta.tolist())), r2


def _elasticities(df, config):
    coefs, r2 = _log_ols(df, 'Net_Revenue', config['SPEND_COLS'], ['promo_flag', 'is_q4', 't_scaled'])
    return {c: float(coefs[c]) for c in config['SPEND_COLS']}, r2


def _marginal_roas(df, config):
    """Marginal revenue per unit spend per channel = elasticity x revenue / spend, recent 52 vs prior 52 weeks."""
    out = {}
    wins = {'recent': df.tail(52), 'prior': df.iloc[-104:-52] if len(df) >= 104 + 10 else None}
    for tag, w in wins.items():
        if w is None or len(w) < 30:
            out[tag] = {c: None for c in config['SPEND_COLS']}
            continue
        el, _ = _elasticities(w, config)
        out[tag] = {c: max(el[c], 0.0) * w['Net_Revenue'].mean() / max(1.0, w[c].mean()) for c in config['SPEND_COLS']}
    return out


# ------------------------------------------------------------------ rules
def _streak(flag):
    flag = flag.astype(int)
    return flag.groupby((flag == 0).cumsum()).cumsum()


def _business_rules(config, df, thr, channel_importance):
    SP, SH, CN = config['SPEND_COLS'], config['SHARE_COLS'], config['CHANNEL_NAMES']
    base_med = float(df.loc[df['promo_flag'] == 0, 'Net_Profit'].median())
    month_tab = df.groupby('month_num')['Net_Margin_pct'].mean()
    best_month = pd.Timestamp(2000, int(month_tab.idxmax()), 1).strftime('%B') if len(month_tab) else 'the strongest month'
    recs = []

    # weekly flags
    bl = df[[config['ID_COL'], config['DATE_COL'], config['PROMO_COL'], 'promo_flag']].copy()
    bl['rule_cut_promo'] = ((df['promo_flag'] == 1) & (df['Net_Profit'] < base_med) & (df['discount_rate_pct'] > thr['DISCOUNT_RATE_MAX_PCT'])).astype(int)
    bl['rule_repeat_promo'] = ((df['promo_flag'] == 1) & (df['Net_Profit'] > base_med)).astype(int)
    below = (df['LTV_to_CAC'] < thr['LTV_CAC_MIN']).astype(int)
    streak = _streak(below)
    bl['ltv_cac_below_streak'] = streak.values
    bl['rule_pause_acquisition'] = (streak >= config['LTV_CAC_STREAK_WEEKS']).astype(int).values
    bl['rule_high_returns'] = (df['return_rate_pct'] > thr['RETURN_RATE_MAX_PCT']).astype(int)

    # promo-level recommendations
    for ev, g in df[df['promo_flag'] == 1].groupby(config['PROMO_COL']):
        med, disc = float(g['Net_Profit'].median()), float(g['discount_rate_pct'].median())
        ev_txt = f"{ev}: median Net_Profit {med:,.0f} vs {base_med:,.0f} in normal weeks; median discount {disc:.1f}% (limit {thr['DISCOUNT_RATE_MAX_PCT']:.1f}%)"
        if med < base_med and disc > thr['DISCOUNT_RATE_MAX_PCT']:
            act, rule, pr = 'Reduce discount depth or drop this promo type', 'promo_unprofitable', 'HIGH'
        elif med > base_med:
            act, rule, pr = f'Repeat this promo; schedule it for the strongest season ({best_month})', 'promo_profitable', 'MEDIUM'
        else:
            act, rule, pr = 'Keep, but test a shallower discount before repeating', 'promo_neutral', 'LOW'
        recs.append({'scope': 'promo', 'subject': ev, 'rule': rule, 'action': act, 'evidence': ev_txt,
                     'weeks': int(len(g)), 'priority': pr, 'outcome': 'DECIDE'})

    # channel rules
    mroas = _marginal_roas(df, config)
    last13 = df.tail(config['BASELINE_WINDOW_WEEKS'])
    share13 = {c: float(last13[s].mean()) for c, s in zip(SP, SH)}
    med_share = float(np.median(list(share13.values())))
    rows = []
    for c, s in zip(SP, SH):
        name = CN[c]
        up = df[c].diff() > 0
        run4 = up.rolling(config['SATURATION_WEEKS']).sum() == config['SATURATION_WEEKS']
        no_lift = df['Orders'].diff(config['SATURATION_WEEKS']) <= 0
        sat = (run4 & no_lift).fillna(False)
        bl[f'saturation_{name.lower()}'] = sat.astype(int).values
        sat_recent = bool(sat.tail(config['BASELINE_WINDOW_WEEKS']).any())
        mr, mp = mroas['recent'][c], mroas['prior'][c]
        rising = mr is not None and mp is not None and mr > mp and mr > 0
        low_share = share13[c] < med_share
        action, rule, pr = 'Hold current budget', 'none', 'LOW'
        if sat_recent:
            action, rule, pr = 'Cap this channel; saturation', 'channel_saturation', 'HIGH'
        elif rising and low_share:
            action, rule, pr = f"Shift {config['SHIFT_BUDGET_PCT']}% of budget here (test)", 'channel_underinvested', 'MEDIUM'
        ev = (f"{name}: share of spend {share13[c] * 100:.1f}% (peer median {med_share * 100:.1f}%); "
              f"marginal return recent {('n/a' if mr is None else f'{mr:.2f}')} vs prior {('n/a' if mp is None else f'{mp:.2f}')}; "
              f"saturation weeks (4 straight rises, no order lift): {int(sat.sum())}")
        if rule != 'none':
            recs.append({'scope': 'channel', 'subject': name, 'rule': rule, 'action': action, 'evidence': ev,
                         'priority': pr, 'outcome': 'DECIDE'})
        rows.append({'channel': name, 'share_last13': share13[c], 'peer_median_share': med_share,
                     'marginal_return_recent': mr, 'marginal_return_prior': mp, 'saturation_weeks': int(sat.sum()),
                     'driver_importance_share': (channel_importance or {}).get(name), 'action': action, 'rule': rule})
    seg_priority = pd.DataFrame(rows)

    # customer economics and returns
    if int(bl['ltv_cac_below_streak'].iloc[-1]) >= config['LTV_CAC_STREAK_WEEKS']:
        recs.append({'scope': 'customer', 'subject': 'LTV_to_CAC', 'rule': 'ltv_cac_below_floor',
                     'action': 'Pause paid acquisition expansion; invest in Email/retention',
                     'evidence': f"LTV_to_CAC below {thr['LTV_CAC_MIN']:.1f} for {int(bl['ltv_cac_below_streak'].iloc[-1])} straight weeks",
                     'priority': 'HIGH', 'outcome': 'DECIDE'})
    n_ret = int(bl['rule_high_returns'].tail(13).sum())
    if n_ret >= 4:
        recs.append({'scope': 'quality', 'subject': 'Returns', 'rule': 'high_return_rate',
                     'action': 'Audit product quality or listing accuracy',
                     'evidence': f"Return rate above {thr['RETURN_RATE_MAX_PCT']:.1f}% in {n_ret} of the last 13 weeks",
                     'priority': 'MEDIUM', 'outcome': 'DECIDE'})

    def week_text(r):
        t = []
        if r['rule_cut_promo']:
            t.append('Reduce discount depth or drop this promo type')
        if r['rule_repeat_promo']:
            t.append('Repeat this promo; schedule it for the strongest season')
        if r['rule_pause_acquisition']:
            t.append('Pause paid acquisition expansion; invest in Email/retention')
        if r['rule_high_returns']:
            t.append('Audit product quality or listing accuracy')
        for c in SP:
            if r[f'saturation_{CN[c].lower()}']:
                t.append(f'Cap {CN[c]}; saturation')
        return '; '.join(t)
    bl['recommendation'] = bl.apply(week_text, axis=1)
    return bl, recs, seg_priority


# ------------------------------------------------------------------ simulations
def _baseline(df, config):
    w, y = df.tail(config['BASELINE_WINDOW_WEEKS']), df.tail(52)
    b = {c: float(w[c].mean()) for c in config['SPEND_COLS']}
    b['total'] = float(sum(b.values()))
    for k, col in [('net_revenue', 'Net_Revenue'), ('net_profit', 'Net_Profit'), ('orders', 'Orders'), ('new_customers', 'New_Customers'),
                   ('gross_revenue', 'Gross_Revenue'), ('cogs', 'COGS'), ('discount_rate_pct', 'discount_rate_pct'), ('return_rate_pct', 'return_rate_pct')]:
        b[k] = float(w[col].mean())
    b['gm_share'] = float(safe_div(y['Gross_Profit'].sum(), y['Net_Revenue'].sum()))
    ts, ps = y['Tax'].sum(), y['Net_Profit'].sum()
    tr = safe_div(ts, ps + ts)
    b['tax_rate'] = float(min(max(tr, 0.0), 0.4)) if (ps + ts) > 0 else 0.25
    return b


def _driver_row(bundle, B, spend, df, config):
    x = {c: B[c] for c in config['SPEND_COLS']}
    x.update(spend)
    tot = sum(x[c] for c in config['SPEND_COLS'])
    x[config['TOTAL_SPEND']] = tot
    for c, s in zip(config['SPEND_COLS'], config['SHARE_COLS']):
        x[s] = x[c] / tot if tot else 0.0
    last = df.tail(config['BASELINE_WINDOW_WEEKS'])
    x['promo_flag'] = float(last['promo_flag'].mean())
    x['discount_rate_pct'] = B['discount_rate_pct']
    x['week_of_year'] = float(df['week_of_year'].iloc[-1])
    x['is_q4'] = float(df['is_q4'].iloc[-1])
    return pd.DataFrame([x]).reindex(columns=bundle['features'])


def _simulations(config, df):
    SP, SH, CN = config['SPEND_COLS'], config['SHARE_COLS'], config['CHANNEL_NAMES']
    B = _baseline(df, config)
    beta, r2 = _elasticities(df, config)
    beta_c = {c: max(v, 0.0) for c, v in beta.items()}
    sims = {}
    driver = None
    if os.path.exists(config['MODEL_DRIVER']):
        try:
            driver = joblib.load(config['MODEL_DRIVER'])
        except Exception:
            driver = None

    # ---- 1. channel budget shift
    rng_share = {c: [float(df[s].min()), float(df[s].max())] for c, s in zip(SP, SH)}
    entries = []
    for i in range(len(SP)):
        for j in range(i + 1, len(SP)):
            for step in config['SHIFT_STEPS_PCT']:
                if step == 0:
                    continue
                frm, to = (SP[i], SP[j]) if step > 0 else (SP[j], SP[i])
                amt = abs(step) / 100.0 * B['total']
                if amt > B[frm]:
                    entries.append({'pair': [CN[SP[i]], CN[SP[j]]], 'from': CN[frm], 'to': CN[to], 'shift_pct_of_budget': abs(step),
                                    'signed_step': step, 'feasible': False})
                    continue
                new = {c: B[c] for c in SP}
                new[frm] -= amt
                new[to] += amt
                mult = float(np.prod([(max(new[c], 1.0) / max(B[c], 1.0)) ** beta_c[c] for c in SP]))
                rev = B['net_revenue'] * mult
                d_rev = rev - B['net_revenue']
                extrap = any(not (rng_share[c][0] <= new[c] / B['total'] <= rng_share[c][1]) for c in SP)
                e = {'pair': [CN[SP[i]], CN[SP[j]]], 'from': CN[frm], 'to': CN[to], 'shift_pct_of_budget': abs(step), 'signed_step': step,
                     'feasible': True, 'new_spend': {CN[c]: round(new[c], 2) for c in SP},
                     'net_revenue': rev, 'delta_net_revenue': d_rev, 'delta_net_profit': d_rev * B['gm_share'],
                     'extrapolation': bool(extrap)}
                if driver is not None:
                    try:
                        p0 = driver['model'].predict(_driver_row(driver, B, {}, df, config).fillna(0))[0]
                        p1 = driver['model'].predict(_driver_row(driver, B, new, df, config).fillna(0))[0]
                        e['driver_model_delta_net_profit'] = float(p1 - p0)
                    except Exception:
                        pass
                entries.append(e)
    sims['channel_budget_shift'] = {
        'meta': {'method': 'Log-log elasticities of Net_Revenue to channel spend (negative values clipped to 0); profit = revenue change x gross margin share, budget-neutral.',
                 'elasticities': {CN[c]: round(v, 4) for c, v in beta.items()}, 'elasticity_model_r2': round(r2, 4),
                 'baseline_weekly': {'net_revenue': B['net_revenue'], 'net_profit': B['net_profit'], 'total_spend': B['total'],
                                     'spend': {CN[c]: B[c] for c in SP}, 'gross_margin_share': B['gm_share']},
                 'caveat': 'Associations from 4 years of weekly data; spend moves with season and promos. Treat as a test hypothesis.',
                 'observed_range': {'channel_share_of_spend': {CN[c]: rng_share[c] for c in SP}}},
        'scenarios': entries}

    # ---- 2. promo discount depth
    coefs, r2d = _log_ols(df, 'Orders', [config['TOTAL_SPEND']], ['discount_rate_pct', 'is_q4', 't_scaled'])
    b_raw = coefs['discount_rate_pct']
    b = max(b_raw, 0.0)
    d0, r_pct = B['discount_rate_pct'], B['return_rate_pct']
    aov_g, cogs_po = safe_div(B['gross_revenue'], B['orders']), safe_div(B['cogs'], B['orders'])
    base_net_model = B['orders'] * aov_g * (1 - d0 / 100 - r_pct / 100)
    lo_d, hi_d = float(df['discount_rate_pct'].min()), float(df['discount_rate_pct'].max())
    pts = []
    for d in np.arange(0, config['DISCOUNT_SIM_MAX_PCT'] + 1e-9, config['DISCOUNT_SIM_STEP_PCT']):
        orders = B['orders'] * float(np.exp(b * (d - d0)))
        net = orders * aov_g * (1 - d / 100 - r_pct / 100)
        cogs = orders * cogs_po
        pretax = (net - base_net_model) - (cogs - B['cogs'])
        pts.append({'discount_rate_pct': float(d), 'orders': orders, 'net_revenue': B['net_revenue'] + (net - base_net_model),
                    'net_profit': B['net_profit'] + pretax * (1 - B['tax_rate']), 'extrapolation': bool(d < lo_d or d > hi_d)})
    sims['promo_discount_depth'] = {
        'meta': {'method': 'Orders respond to discount depth with the observed log-linear response (controls: total spend, Q4, trend). COGS scales with orders, not with discounts.',
                 'orders_per_discount_point_pct': round(b_raw * 100, 3), 'clipped_to_zero': bool(b_raw < 0), 'model_r2': round(r2d, 4),
                 'baseline_discount_rate_pct': d0,
                 'baseline_weekly': {'orders': B['orders'], 'net_revenue': B['net_revenue'], 'net_profit': B['net_profit']},
                 'caveat': 'Points outside observed_range are extrapolation.',
                 'observed_range': {'discount_rate_pct': [lo_d, hi_d],
                                    'promo_weeks_discount_rate_pct': [float(df.loc[df['promo_flag'] == 1, 'discount_rate_pct'].min()) if (df['promo_flag'] == 1).any() else None,
                                                                      float(df.loc[df['promo_flag'] == 1, 'discount_rate_pct'].max()) if (df['promo_flag'] == 1).any() else None]}},
        'scenarios': pts}

    # ---- 3. marketing % of revenue cap
    sigma = float(sum(beta_c.values()))
    cn, _ = _log_ols(df, 'New_Customers', [config['TOTAL_SPEND']], ['promo_flag', 'is_q4', 't_scaled'])
    gamma = max(cn[config['TOTAL_SPEND']], 0.0)
    mpr = df['marketing_pct_of_revenue']
    lo_m, hi_m = float(mpr.quantile(0.05)), float(mpr.quantile(0.95))
    base_mpr = safe_div(B['total'], B['net_revenue']) * 100
    caps = sorted(set([round(x, 1) for x in np.linspace(lo_m * 0.8, hi_m, 8)] + [round(base_mpr, 1)]))
    spend_rng = [float(df[config['TOTAL_SPEND']].min()), float(df[config['TOTAL_SPEND']].max())]
    out = []
    for cap in caps:
        binding = base_mpr > cap
        if not binding:
            k = 1.0
        elif sigma < 0.999:
            k = (cap / base_mpr) ** (1.0 / (1.0 - sigma))
        else:
            k = cap / base_mpr
        k = float(min(max(k, 0.3), 1.0))
        spend_new = B['total'] * k
        rev_new = B['net_revenue'] * k ** sigma
        out.append({'cap_marketing_pct_of_revenue': cap, 'binding': bool(binding), 'spend_multiplier': k, 'weekly_spend': spend_new,
                    'net_revenue': rev_new, 'marketing_pct_of_revenue': safe_div(spend_new, rev_new) * 100,
                    'new_customers': B['new_customers'] * k ** gamma,
                    'net_profit': B['net_profit'] + (rev_new - B['net_revenue']) * B['gm_share'] - (spend_new - B['total']),
                    'cap_reached': bool(safe_div(spend_new, rev_new) * 100 <= cap + 0.05),
                    'extrapolation': bool(spend_new < spend_rng[0] or spend_new > spend_rng[1] or k <= 0.3)})
    sims['cac_cap_scenarios'] = {
        'meta': {'method': 'All channels scaled together until marketing_pct_of_revenue hits the cap; revenue and new customers follow observed elasticities.',
                 'revenue_elasticity_to_total_spend': round(sigma, 4), 'new_customer_elasticity_to_total_spend': round(gamma, 4),
                 'baseline_marketing_pct_of_revenue': base_mpr,
                 'baseline_weekly': {'net_revenue': B['net_revenue'], 'net_profit': B['net_profit'], 'new_customers': B['new_customers'], 'total_spend': B['total']},
                 'caveat': 'A cap only reduces spend; revenue loss is estimated, not guaranteed. If revenue elasticity to spend is >= 1, a cap cannot be reached by scaling (cap_reached = false).',
                 'observed_range': {'marketing_pct_of_revenue': [lo_m, hi_m], 'weekly_total_spend': spend_rng}},
        'scenarios': out}
    return sims


# ------------------------------------------------------------------ goals and alerts
def _goals_alerts(config, df, thr, forecast_report):
    path = config['GOALS_JSON']
    if os.path.exists(path):
        import json
        with open(path, 'r', encoding='utf-8') as f:
            goals = json.load(f)
    else:
        goals = config['GOAL_DEFAULTS']
        save_json(path, goals)
    last, last4, prior4 = df.iloc[-1], df.tail(4), df.iloc[-8:-4]
    gv = lambda k, d=None: (goals.get(k, {}) or {}).get('value', d)
    prog = {}
    for key, col in [('net_profit_target', 'Net_Profit'), ('net_revenue_target', 'Net_Revenue')]:
        tgt = gv(key)
        actual4 = float(last4[col].mean())
        prog[key] = {'target': tgt, 'unit': 'weekly', 'actual_last_week': float(last[col]), 'actual_4w_avg': actual4,
                     'progress_pct': (actual4 / tgt * 100) if tgt else None,
                     'status': 'not_set' if tgt is None else ('on_track' if actual4 >= tgt else 'behind')}
    floor_w, ltv_min = gv('cash_floor_weeks', 8), gv('ltv_cac_min', 3.0)
    prog['cash_floor_weeks'] = {'target': floor_w, 'actual': float(last['cash_runway_weeks']),
                                'status': 'on_track' if last['cash_runway_weeks'] >= floor_w else 'breach'}
    prog['ltv_cac_min'] = {'target': ltv_min, 'actual_4w_avg': float(last4['LTV_to_CAC'].mean()),
                           'status': 'on_track' if last4['LTV_to_CAC'].mean() >= ltv_min else 'breach'}

    alerts = []

    def add(aid, sev, metric, value, threshold, msg):
        alerts.append({'id': aid, 'severity': sev, 'metric': metric, 'value': value, 'threshold': threshold,
                       'message': msg, 'outcome': 'MONITOR'})
    drop_lim = gv('alert_revenue_drop_pct', 20)
    r4, p4 = float(last4['Net_Revenue'].sum()), float(prior4['Net_Revenue'].sum())
    chg = (r4 - p4) / p4 * 100 if p4 else 0.0
    if chg <= -drop_lim:
        add('revenue_drop', 'HIGH', 'Net_Revenue 4-week change %', chg, -drop_lim, f'4-week Net Revenue is {abs(chg):.1f}% below the prior 4 weeks.')
    if last['cash_runway_weeks'] < floor_w:
        add('runway_low', 'HIGH', 'cash_runway_weeks', float(last['cash_runway_weeks']), floor_w, f"Cash covers {last['cash_runway_weeks']:.1f} weeks of costs, below the {floor_w} week floor.")
    if last['DSO_Days'] > thr['DSO_MAX_DAYS']:
        add('dso_high', 'MEDIUM', 'DSO_Days', float(last['DSO_Days']), thr['DSO_MAX_DAYS'], f"DSO {last['DSO_Days']:.1f} days is above the limit of {thr['DSO_MAX_DAYS']:.1f}.")
    if last4['LTV_to_CAC'].mean() < ltv_min:
        add('ltv_cac_breach', 'HIGH', 'LTV_to_CAC 4-week avg', float(last4['LTV_to_CAC'].mean()), ltv_min, 'Acquisition is not paying back (LTV_to_CAC below the floor).')
    nxt = (forecast_report or {}).get('next_week_loss_risk')
    if nxt and nxt.get('at_risk'):
        add('loss_risk_next_week', 'MEDIUM', 'loss_risk_next_week', nxt.get('probability'), nxt.get('threshold'),
            f"Next week ({nxt.get('week_start')}) is flagged at risk of a loss under the planned promo and spend assumptions.")
    return goals, prog, alerts


def run_business_logic(config=CONFIG, df_feat=None, agg_promo=None, **kwargs):
    """Phase 8: rule-based actions, simulation lookups, goals and alerts. Outputs: seg_priority, recommendations, simulations, goal_progress, alerts."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    df = df_feat.copy().sort_values(config['DATE_COL']).reset_index(drop=True)
    thr = kwargs.get('thresholds') or compute_thresholds(config, df)
    bl, recs, seg_priority = _business_rules(config, df, thr, kwargs.get('channel_importance'))
    bl.to_csv(config['BL_CSV'], index=False)
    sims = _simulations(config, df)
    goals, goal_progress, alerts = _goals_alerts(config, df, thr, kwargs.get('forecast_report'))
    print(f"  Business logic: {len(recs)} recommendations | {len(sims)} simulation sets | {len(alerts)} alerts")
    return {'business_logic_df': bl, 'recommendations': recs, 'seg_priority': seg_priority, 'simulations': sims,
            'goals': goals, 'goal_progress': goal_progress, 'alerts': alerts}

