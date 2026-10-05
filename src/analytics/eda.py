import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, compute_thresholds
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

C_BLUE, C_GREEN, C_RED, C_ORANGE, C_GREY = '#1565C0', '#2E7D32', '#C62828', '#E65100', '#757575'


def _save(config, fig, name):
    os.makedirs(config['REPORTS_DIR'], exist_ok=True)
    path = os.path.join(config['REPORTS_DIR'], name)
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def _cjson(config, cid, title, question, outcome, x, series, extra=None):
    """Chart data for the frontend (output/understand/charts/<id>.json)."""
    payload = {'id': cid, 'title': title, 'question': question, 'outcome': outcome, 'x': x, 'series': series}
    if extra:
        payload.update(extra)
    save_json(os.path.join(config['OUTPUT_DIR'], 'understand', 'charts', f'{cid}.json'), payload)


def run_eda(config=CONFIG, df_feat=None, **kwargs):
    """Phase 4: seven business-question charts (dpi=150) plus chart JSON for the frontend. Outputs: chart_paths, chart_meta."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    df = df_feat.copy()
    df[config['DATE_COL']] = pd.to_datetime(df[config['DATE_COL']])
    thr = kwargs.get('thresholds') or compute_thresholds(config, df)
    x = df[config['DATE_COL']]
    xs = x.dt.strftime('%Y-%m-%d').tolist()
    paths, meta = [], []

    # 1. Growing profitably?
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax[0].plot(x, df['Net_Revenue'], color=C_BLUE, alpha=0.45, label='Net Revenue (weekly)')
    ax[0].plot(x, df['Net_Revenue'].rolling(13, min_periods=4).mean(), color=C_BLUE, lw=2.5, label='13-week average')
    ax[0].set_ylabel('Net Revenue'); ax[0].legend(loc='upper left'); ax[0].grid(alpha=0.3)
    ax[1].plot(x, df['Net_Profit'], color=C_GREEN, alpha=0.45, label='Net Profit (weekly)')
    ax[1].plot(x, df['Net_Profit'].rolling(13, min_periods=4).mean(), color=C_GREEN, lw=2.5, label='13-week average')
    ax[1].axhline(0, color=C_RED, ls='--', lw=1)
    ax[1].set_ylabel('Net Profit'); ax[1].legend(loc='upper left'); ax[1].grid(alpha=0.3)
    fig.suptitle('Is my business growing profitably?', fontweight='bold')
    p = _save(config, fig, '01_growth_vs_profit.png'); paths.append(p)
    _cjson(config, 'growth_vs_profit', 'Net Revenue vs Net Profit', 'Is my business growing profitably?', 'UNDERSTAND', xs,
           {'net_revenue': df['Net_Revenue'], 'net_profit': df['Net_Profit'],
            'net_revenue_13w': df['Net_Revenue'].rolling(13, min_periods=4).mean(),
            'net_profit_13w': df['Net_Profit'].rolling(13, min_periods=4).mean()})
    meta.append({'file': p, 'title': 'Growth vs profit', 'caption': 'Revenue trend against profit: is growth turning into money?'})

    # 2. Where does the marketing money go?
    fig, ax = plt.subplots(figsize=(12, 5))
    shares = df[config['SHARE_COLS']].rolling(4, min_periods=1).mean()
    ax.stackplot(x, [shares[c] * 100 for c in config['SHARE_COLS']],
                 labels=[config['CHANNEL_NAMES'][c] for c in config['SPEND_COLS']],
                 colors=[C_BLUE, C_ORANGE, C_GREEN, C_GREY], alpha=0.85)
    ax.set_ylabel('% of marketing spend (4-week average)'); ax.set_ylim(0, 100)
    ax.legend(loc='upper left', ncol=4); ax.set_title('Where does my marketing money go and is the mix shifting?', fontweight='bold')
    p = _save(config, fig, '02_channel_mix.png'); paths.append(p)
    _cjson(config, 'channel_mix', 'Channel mix over time', 'Where does my marketing money go and is the mix shifting?', 'UNDERSTAND', xs,
           {config['CHANNEL_NAMES'][c]: shares[s] * 100 for c, s in zip(config['SPEND_COLS'], config['SHARE_COLS'])})
    meta.append({'file': p, 'title': 'Channel mix', 'caption': 'Share of budget by channel, smoothed over 4 weeks.'})

    # 3. Do promo weeks make or lose money?
    fig, ax = plt.subplots(1, 3, figsize=(16, 5), gridspec_kw={'width_ratios': [2.2, 1, 1]})
    events = [e for e in df[config['PROMO_COL']].unique() if e != 'None']
    order = ['None'] + sorted(events)
    data = [df.loc[df[config['PROMO_COL']] == e, 'Net_Profit'].values for e in order]
    ax[0].boxplot(data, showmeans=True)
    ax[0].set_xticklabels(order, rotation=30, ha='right'); ax[0].axhline(0, color=C_RED, ls='--', lw=1)
    ax[0].set_title('Net Profit by promo event'); ax[0].grid(alpha=0.3)
    grp = df.groupby('promo_flag')
    labels = ['Non-promo', 'Promo']
    idx = [i for i in (0, 1) if i in grp.groups]
    ax[1].bar([labels[i] for i in idx], [grp['Net_Profit'].median()[i] for i in idx], color=[C_GREY, C_BLUE][:len(idx)])
    ax[1].set_title('Median Net Profit'); ax[1].axhline(0, color=C_RED, ls='--', lw=1)
    ax[2].bar([labels[i] for i in idx], [grp['discount_rate_pct'].median()[i] for i in idx], color=[C_GREY, C_ORANGE][:len(idx)])
    ax[2].axhline(thr['DISCOUNT_RATE_MAX_PCT'], color=C_RED, ls='--', lw=1, label='discount limit')
    ax[2].set_title('Median discount rate %'); ax[2].legend()
    fig.suptitle('Do promo weeks make or lose money?', fontweight='bold')
    p = _save(config, fig, '03_promo_profitability.png'); paths.append(p)
    _cjson(config, 'promo_profitability', 'Promo profitability', 'Do promo weeks make or lose money?', 'DECIDE', order,
           {'median_net_profit': [float(np.median(d)) if len(d) else None for d in data],
            'weeks': [len(d) for d in data]}, {'discount_limit_pct': thr['DISCOUNT_RATE_MAX_PCT']})
    meta.append({'file': p, 'title': 'Promo profitability', 'caption': 'Profit and discount depth in promo versus normal weeks.'})

    # 4. Which channel's spend moves results most? (lagged correlation, 0-2 weeks)
    rows, labels4 = [], []
    for c in config['SPEND_COLS']:
        for lag in (0, 1, 2):
            rows.append([df[c].shift(lag).corr(df['Orders']), df[c].shift(lag).corr(df['Net_Profit'])])
            labels4.append(f"{config['CHANNEL_NAMES'][c]} (lag {lag}w)")
    M = np.array(rows, dtype=float)
    fig, ax = plt.subplots(figsize=(6.5, 6.5))
    im = ax.imshow(np.nan_to_num(M), cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax.set_xticks([0, 1]); ax.set_xticklabels(['Orders', 'Net Profit'])
    ax.set_yticks(range(len(labels4))); ax.set_yticklabels(labels4)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f'{np.nan_to_num(M[i, j]):.2f}', ha='center', va='center', fontsize=9)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title('Which channel\'s spend moves results most?\n(correlation, not proof of cause)', fontweight='bold')
    p = _save(config, fig, '04_channel_lag_correlation.png'); paths.append(p)
    _cjson(config, 'channel_lag_correlation', 'Channel spend vs results', 'Which channel\'s spend moves Net Revenue most?', 'DECIDE',
           labels4, {'orders': M[:, 0], 'net_profit': M[:, 1]})
    meta.append({'file': p, 'title': 'Channel lag correlation', 'caption': 'Spend-to-result correlation at 0 to 2 week delay.'})

    # 5. Is acquisition paying back?
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(x, df['LTV_to_CAC'], color=C_BLUE, label='LTV to CAC')
    ax.axhline(thr['LTV_CAC_MIN'], color=C_RED, ls='--', label=f"minimum {thr['LTV_CAC_MIN']:.1f}")
    ax.set_ylabel('LTV to CAC'); ax.grid(alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(x, df['CAC'], color=C_ORANGE, alpha=0.7, label='CAC')
    ax2.set_ylabel('CAC')
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left')
    ax.set_title('Is customer acquisition paying back?', fontweight='bold')
    p = _save(config, fig, '05_ltv_cac.png'); paths.append(p)
    _cjson(config, 'ltv_cac', 'LTV to CAC and CAC', 'Is customer acquisition paying back?', 'UNDERSTAND', xs,
           {'ltv_to_cac': df['LTV_to_CAC'], 'cac': df['CAC']}, {'floor': thr['LTV_CAC_MIN']})
    meta.append({'file': p, 'title': 'Customer payback', 'caption': 'Lifetime value versus acquisition cost against the 3.0 floor.'})

    # 6. Seasonality heatmap
    piv = df.assign(cal_year=df[config['DATE_COL']].dt.year).pivot_table(
        index='cal_year', columns='month_num', values='Net_Margin_pct', aggfunc='mean')
    piv = piv.reindex(columns=range(1, 13))
    fig, ax = plt.subplots(figsize=(12, 4.5))
    im = ax.imshow(piv.values, cmap='RdYlGn', aspect='auto', vmin=-max(5, np.nanmax(np.abs(piv.values))), vmax=max(5, np.nanmax(np.abs(piv.values))))
    ax.set_xticks(range(12)); ax.set_xticklabels([pd.Timestamp(2000, m, 1).strftime('%b') for m in range(1, 13)])
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index.astype(int))
    for i in range(piv.shape[0]):
        for j in range(12):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8, label='Net margin %')
    ax.set_title('Which months and seasons are strongest? (Net margin %)', fontweight='bold')
    p = _save(config, fig, '06_seasonality_heatmap.png'); paths.append(p)
    _cjson(config, 'seasonality_heatmap', 'Net margin by month and year', 'Which months/seasons are strongest?', 'DECIDE',
           [int(i) for i in piv.index], {str(m): piv[m] for m in piv.columns})
    meta.append({'file': p, 'title': 'Seasonality', 'caption': 'Average net margin by calendar month and year.'})

    # 7. Is cash safe?
    floor = config['THRESHOLDS']['CASH_FLOOR_WEEKS'] * (df['Payroll'] + df['Other_Opex'] + df[config['TOTAL_SPEND']])
    fig, ax = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    ax[0].plot(x, df['Cash_Balance'], color=C_BLUE, label='Cash balance')
    ax[0].plot(x, floor, color=C_RED, ls='--', label=f"{config['THRESHOLDS']['CASH_FLOOR_WEEKS']:.0f}-week runway floor")
    ax[0].legend(loc='upper left'); ax[0].grid(alpha=0.3); ax[0].set_ylabel('Cash')
    ax[1].plot(x, df['AR_Outstanding'], color=C_ORANGE); ax[1].set_ylabel('AR outstanding'); ax[1].grid(alpha=0.3)
    ax[2].plot(x, df['DSO_Days'], color=C_GREEN); ax[2].axhline(thr['DSO_MAX_DAYS'], color=C_RED, ls='--', label='DSO limit (75th pct)')
    ax[2].set_ylabel('DSO days'); ax[2].legend(loc='upper left'); ax[2].grid(alpha=0.3)
    fig.suptitle('Is cash safe?', fontweight='bold')
    p = _save(config, fig, '07_cash_safety.png'); paths.append(p)
    _cjson(config, 'cash_safety', 'Cash, receivables and DSO', 'Is cash safe?', 'MONITOR', xs,
           {'cash_balance': df['Cash_Balance'], 'runway_floor': floor, 'ar_outstanding': df['AR_Outstanding'],
            'dso_days': df['DSO_Days']}, {'dso_limit': thr['DSO_MAX_DAYS']})
    meta.append({'file': p, 'title': 'Cash safety', 'caption': 'Cash balance against an 8-week runway floor, plus receivables and DSO.'})

    print(f"  EDA charts saved: {len(paths)} -> {config['REPORTS_DIR']}")
    return {'chart_paths': paths, 'chart_meta': meta}

