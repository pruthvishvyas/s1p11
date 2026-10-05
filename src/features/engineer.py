import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, safe_div, compute_thresholds
import numpy as np
import pandas as pd


def _weeks_since_last_promo(flags, cap=52):
    out, count = [], cap
    for f in flags:
        count = 0 if f == 1 else min(count + 1, cap)
        out.append(count)
    return out


def run_engineer(config=CONFIG, df_clean=None, **kwargs):
    """Phase 3: plain-English features, lags, health score, aggregates. Outputs: df_feat, agg_promo, agg_month, agg_channel, thresholds."""
    if df_clean is None:
        df_clean = pd.read_csv(config['PROCESSED_CSV'], parse_dates=[config['DATE_COL']])
    df = df_clean.copy().sort_values(config['DATE_COL']).reset_index(drop=True)
    TOT = config['TOTAL_SPEND']
    if 'promo_flag' not in df.columns:
        df['promo_flag'] = (df[config['PROMO_COL']].fillna('None') != 'None').astype(int)

    df['discount_rate_pct'] = safe_div(df['Discounts'], df['Gross_Revenue']) * 100      # share of sales given away
    df['return_rate_pct'] = safe_div(df['Returns'], df['Gross_Revenue']) * 100
    df['conversion_rate_pct'] = safe_div(df['Orders'], df['Clicks']) * 100
    df['lead_to_order_pct'] = safe_div(df['Orders'], df['Leads']) * 100
    for col, share in zip(config['SPEND_COLS'], config['SHARE_COLS']):
        df[share] = safe_div(df[col], df[TOT])
    df['marketing_pct_of_revenue'] = safe_div(df[TOT], df['Net_Revenue']) * 100
    df['profit_per_order'] = safe_div(df['Net_Profit'], df['Orders'])
    df['contribution_after_marketing'] = df['Gross_Profit'] - df[TOT]
    df['new_customer_share'] = safe_div(df['New_Customers'], df['Orders'])
    df['cash_runway_weeks'] = safe_div(df['Cash_Balance'], df['Payroll'] + df['Other_Opex'] + df[TOT])

    d = df[config['DATE_COL']]
    df['month_num'] = d.dt.month.astype(int)
    df['week_of_year'] = d.dt.isocalendar().week.astype(int).clip(upper=52)
    df['is_q4'] = (df['month_num'] >= 10).astype(int)
    df['t_index'] = np.arange(len(df))
    df['weeks_since_last_promo'] = _weeks_since_last_promo(df['promo_flag'].tolist())

    for s in config['LAG_SERIES']:
        for k in config['LAG_WEEKS']:
            df[f'{s}_lag{k}'] = df[s].shift(k)
        df[f'{s}_rm4'] = df[s].shift(1).rolling(4).mean()     # prior 4 weeks only (no leakage)

    df[config['TARGET_FLAG']] = (df['Net_Profit'] < 0).astype(int)

    w = config['HEALTH_WEIGHTS']
    print('  health_score weights:', w)
    score = 0.0
    for col, wt in w.items():
        score = score + wt * df[col].rank(pct=True) * 100
    df['health_score'] = score / sum(w.values())

    thresholds = compute_thresholds(config, df)
    save_json(config['THRESHOLDS_JSON'], thresholds)

    os.makedirs(os.path.dirname(config['FEAT_CSV']), exist_ok=True)
    df.to_csv(config['FEAT_CSV'], index=False)

    # ---- aggregates used downstream
    base_med = df.loc[df['promo_flag'] == 0, 'Net_Profit'].median()
    g = df.groupby(config['PROMO_COL'])
    agg_promo = pd.DataFrame({
        'weeks': g.size(),
        'median_net_profit': g['Net_Profit'].median(),
        'mean_net_profit': g['Net_Profit'].mean(),
        'median_net_margin_pct': g['Net_Margin_pct'].median(),
        'median_discount_rate_pct': g['discount_rate_pct'].median(),
        'median_orders': g['Orders'].median(),
        'loss_week_rate': g[config['TARGET_FLAG']].mean(),
    }).reset_index()
    agg_promo['profit_vs_non_promo_median'] = agg_promo['median_net_profit'] - base_med
    agg_promo = agg_promo.sort_values('median_net_profit', ascending=False).reset_index(drop=True)

    gm = df.groupby('month_num')
    agg_month = pd.DataFrame({
        'weeks': gm.size(),
        'avg_net_margin_pct': gm['Net_Margin_pct'].mean(),
        'median_net_profit': gm['Net_Profit'].median(),
        'avg_net_revenue': gm['Net_Revenue'].mean(),
        'loss_week_rate': gm[config['TARGET_FLAG']].mean(),
    }).reset_index()
    agg_month['month'] = agg_month['month_num'].map(lambda m: pd.Timestamp(2000, int(m), 1).strftime('%b'))

    rows = []
    last13 = df.tail(config['BASELINE_WINDOW_WEEKS'])
    for col, share in zip(config['SPEND_COLS'], config['SHARE_COLS']):
        rows.append({'channel': config['CHANNEL_NAMES'][col], 'total_spend': df[col].sum(),
                     'avg_share': df[share].mean(), 'last13_share': last13[share].mean(),
                     'corr_with_orders': df[col].corr(df['Orders']),
                     'corr_with_net_profit': df[col].corr(df['Net_Profit'])})
    agg_channel = pd.DataFrame(rows)

    print(f"  Features: {df.shape[1]} cols | loss weeks {int(df[config['TARGET_FLAG']].sum())} | FEAT_CSV saved")
    return {'df_feat': df, 'agg_promo': agg_promo, 'agg_month': agg_month,
            'agg_channel': agg_channel, 'thresholds': thresholds}

