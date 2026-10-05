import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, safe_div
import numpy as np
import pandas as pd


def make_synthetic(config, n_weeks=208):
    """Synthetic weekly D2C data with the exact 44-column schema and consistent accounting identities."""
    rng = np.random.default_rng(config['RANDOM_STATE'])
    n = n_weeks
    dates = pd.date_range('2022-10-03', periods=n, freq='7D')
    woy = np.minimum(dates.isocalendar().week.astype(int).values, 52)
    month = dates.month.values
    t = np.arange(n)
    season = 1 + 0.10 * np.sin(2 * np.pi * (woy - 10) / 52) + np.where(month >= 10, 0.15, 0.0)
    promo_map = {47: 'Black Friday', 48: 'Black Friday', 51: 'Holiday Sale', 1: 'New Year Sale',
                 14: 'Spring Sale', 15: 'Spring Sale', 26: 'Summer Sale', 27: 'Summer Sale'}
    promo = np.array([promo_map.get(int(w)) for w in woy], dtype=object)
    free = [i for i in range(n) if promo[i] is None]
    for i in rng.choice(free, 7, replace=False):
        promo[i] = 'Flash Sale'
    pf = np.array([p is not None for p in promo]).astype(float)

    grow = 1 + 0.0012 * t
    base = {'Search': 5600, 'Social': 4300, 'Email': 1250, 'Display': 2300}
    sp = {}
    for k, v in base.items():
        seas = season if k != 'Email' else 1 + 0.3 * (season - 1)
        sp[k] = np.round(v * grow * seas * np.where(pf == 1, 1.25, 1.0) * rng.normal(1, 0.07, n))
    total = sp['Search'] + sp['Social'] + sp['Email'] + sp['Display']

    cpc0 = {'Search': 1.2, 'Social': 0.9, 'Display': 1.6, 'Email': 0.5}
    expo = {'Search': 0.80, 'Social': 0.85, 'Display': 0.85, 'Email': 0.95}
    clicks = np.zeros(n)
    for k in cpc0:
        k_c = (base[k] / cpc0[k]) / (base[k] ** expo[k])
        clicks += k_c * (sp[k] ** expo[k]) * rng.normal(1, 0.05, n)
    clicks = np.round(clicks)
    ctr = rng.normal(2.0, 0.15, n) + 0.2 * pf
    impressions = np.round(clicks / (ctr / 100))
    ctr_pct = np.round(clicks / impressions * 100, 2)
    cpc = np.round(total / clicks, 2)
    leads = np.round(clicks * 0.14 * rng.normal(1, 0.05, n))
    conv = 0.075 * (1 + 0.20 * pf) * (1 + 0.5 * (season - 1)) * rng.normal(1, 0.06, n)
    orders = np.round(clicks * conv)
    new_c = np.round(orders * np.clip(0.56 + 0.08 * pf + rng.normal(0, 0.02, n), 0.3, 0.9))
    repeat = np.round((orders - new_c) / orders * 100, 1)
    cac = np.round(total / new_c, 2)
    units = np.round(orders * rng.normal(1.8, 0.1, n))
    aov = np.round(rng.normal(82, 3, n) * (1 + 0.0005 * t), 2)
    gross = np.round(orders * aov)
    disc = np.round(gross * np.where(pf == 1, rng.normal(0.14, 0.03, n), rng.normal(0.03, 0.008, n)))
    rets = np.round(gross * (rng.normal(0.06, 0.01, n) + np.where(month >= 11, 0.015, 0.0)))
    net = gross - disc - rets
    cogs = np.round(gross * 0.40 * rng.normal(1, 0.02, n))
    gp = net - cogs
    gm = np.round(gp / net * 100, 1)
    payroll = np.round(17000 * (1 + 0.0006 * t) * rng.normal(1, 0.01, n))
    opex = np.round(10500 * (1 + 0.0004 * t) * rng.normal(1, 0.04, n))
    ebitda = gp - total - payroll - opex
    dep = np.round(800 + 2 * t).astype(int)
    interest = np.round(400 * rng.normal(1, 0.05, n))
    ebt = ebitda - dep - interest
    tax = np.round(np.maximum(0, 0.25 * ebt))
    npf = ebt - tax
    nm = np.round(npf / net * 100, 1)
    ar = np.round(net * rng.uniform(0.35, 0.50, n))
    dso = np.round(ar / (net / 7), 1)
    roas = np.round(net / total, 2)
    roi = np.round((gp - total) / total * 100, 1)
    cash = np.zeros(n)
    cash[0] = 183275
    for i in range(1, n):
        cash[i] = cash[i - 1] + npf[i] + dep[i] - (ar[i] - ar[i - 1])
    cash = np.round(cash)
    ltv = np.round(rng.normal(217, 8, n) * (1 + 0.0004 * t), 2)
    ltv_cac = np.round(ltv / cac, 2)

    df = pd.DataFrame({
        'Week_ID': [f'W{i + 1:03d}' for i in range(n)],
        'Week_Start': dates.strftime('%Y-%m-%d'),
        'Year': dates.year.values,
        'Quarter': ['Q%d' % q for q in dates.quarter],
        'Month': dates.strftime('%b'),
        'Promo_Event': promo,
        'Spend_Search': sp['Search'], 'Spend_Social': sp['Social'],
        'Spend_Email': sp['Email'], 'Spend_Display': sp['Display'],
        'Total_Marketing_Spend': total, 'Impressions': impressions.astype(int),
        'Clicks': clicks.astype(int), 'CTR_pct': ctr_pct, 'CPC': cpc,
        'Leads': leads.astype(int), 'Orders': orders.astype(int),
        'New_Customers': new_c.astype(int), 'Repeat_Customer_Rate_pct': repeat, 'CAC': cac,
        'Units_Sold': units.astype(int), 'Avg_Order_Value': aov, 'Gross_Revenue': gross,
        'Discounts': disc, 'Returns': rets, 'Net_Revenue': net, 'COGS': cogs,
        'Gross_Profit': gp, 'Gross_Margin_pct': gm, 'Payroll': payroll, 'Other_Opex': opex,
        'EBITDA': ebitda, 'Depreciation': dep, 'Interest': interest, 'Tax': tax,
        'Net_Profit': npf, 'Net_Margin_pct': nm, 'AR_Outstanding': ar, 'DSO_Days': dso,
        'ROAS': roas, 'Marketing_ROI_pct': roi, 'Cash_Balance': cash,
        'Customer_LTV_est': ltv, 'LTV_to_CAC': ltv_cac,
    })
    return df[config['EXPECTED_COLS']]


def _gap(a, b):
    d = (pd.to_numeric(a, errors='coerce') - pd.to_numeric(b, errors='coerce')).abs()
    return float(d.max()) if len(d) else 0.0, float(d.mean()) if len(d) else 0.0


def _check(name, a, b, tol, out):
    mx, mean = _gap(a, b)
    ok = bool(mx <= tol)
    out[name] = {'max_abs_gap': round(mx, 4), 'mean_abs_gap': round(mean, 4), 'tolerance': tol, 'ok': ok}
    if not ok:
        print(f"  WARNING identity '{name}': max abs gap {mx:.4f} (tolerance {tol})")


def _best_basis(name, target, candidates, tol, out):
    """Detect which denominator reproduces a ratio column; record it."""
    best = None
    for label, series in candidates.items():
        mx, mean = _gap(target, series)
        if best is None or mean < best[2]:
            best = (label, mx, mean)
    out[name] = {'basis': best[0], 'max_abs_gap': round(best[1], 4),
                 'mean_abs_gap': round(best[2], 4), 'tolerance': tol, 'ok': bool(best[1] <= tol)}
    if not out[name]['ok']:
        print(f"  WARNING identity '{name}': best basis {best[0]}, max abs gap {best[1]:.4f}")


def run_ingest(config=CONFIG, **kwargs):
    """Phase 1: load, schema-check, validate weekly spacing and accounting identities. Outputs: df_raw, validation_dict."""
    path = config['RAW_CSV']
    synthetic = False
    if not os.path.exists(path):
        print(f"WARNING: CSV not found at {path}. Using synthetic data.")
        df = make_synthetic(config)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        synthetic = True
    else:
        df = pd.read_csv(path)

    v = {'rows': int(len(df)), 'cols': int(df.shape[1]), 'synthetic_data': synthetic}
    missing = [c for c in config['EXPECTED_COLS'] if c not in df.columns]
    extra = [c for c in df.columns if c not in config['EXPECTED_COLS']]
    v['schema_ok'] = len(missing) == 0
    v['missing_cols'], v['extra_cols'] = missing, extra
    if missing:
        save_json(config['VALIDATION_JSON'], v)
        raise ValueError(f"Schema check failed, missing columns: {missing}")
    if len(df) < config['MIN_ROWS']:
        print(f"  WARNING: only {len(df)} rows; ML phases need at least {config['MIN_ROWS']}.")

    v['null_map'] = {c: int(n) for c, n in df.isnull().sum().items() if n > 0}

    dcol, icol = config['DATE_COL'], config['ID_COL']
    df[dcol] = pd.to_datetime(df[dcol], errors='coerce')
    v['bad_dates'] = int(df[dcol].isna().sum())
    df = df.sort_values(dcol).reset_index(drop=True)
    v['duplicate_week_ids'] = df[df[icol].duplicated(keep=False)][icol].unique().tolist()
    gaps = df[dcol].diff().dt.days.dropna()
    bad = gaps[gaps != 7]
    v['week_gaps'] = {'non_7_day_gaps': int(len(bad)),
                      'examples': [{'row': int(i), 'days': int(d)} for i, d in bad.head(10).items()]}
    start, end = df[dcol].min(), df[dcol].max()
    if pd.notna(start) and pd.notna(end):
        expected = pd.date_range(start, end, freq='7D')
        v['missing_weeks'] = [d.strftime('%Y-%m-%d') for d in expected.difference(pd.DatetimeIndex(df[dcol]))][:20]
        v['date_range'] = [start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')]
    else:
        v['missing_weeks'], v['date_range'] = [], []

    # NaN promo = no promo (not missing data)
    df[config['PROMO_COL']] = df[config['PROMO_COL']].fillna('None').astype(str)
    v['promo_counts'] = {k: int(n) for k, n in df[config['PROMO_COL']].value_counts().items()}
    print(f"  Promo weeks: {int((df[config['PROMO_COL']] != 'None').sum())} of {len(df)}")

    ident = {}
    spend_sum = df[config['SPEND_COLS']].sum(axis=1)
    _check('sum_spend_equals_total', spend_sum, df[config['TOTAL_SPEND']], 1.0, ident)
    _check('net_revenue_identity', df['Gross_Revenue'] - df['Discounts'] - df['Returns'], df['Net_Revenue'], 1.0, ident)
    _check('gross_profit_identity', df['Net_Revenue'] - df['COGS'], df['Gross_Profit'], 1.0, ident)
    _best_basis('gross_margin_pct', df['Gross_Margin_pct'],
                {'Net_Revenue': safe_div(df['Gross_Profit'], df['Net_Revenue']) * 100,
                 'Gross_Revenue': safe_div(df['Gross_Profit'], df['Gross_Revenue']) * 100}, 0.15, ident)
    _best_basis('net_margin_pct', df['Net_Margin_pct'],
                {'Net_Revenue': safe_div(df['Net_Profit'], df['Net_Revenue']) * 100,
                 'Gross_Revenue': safe_div(df['Net_Profit'], df['Gross_Revenue']) * 100}, 0.15, ident)
    _best_basis('roas', df['ROAS'],
                {'Net_Revenue': safe_div(df['Net_Revenue'], df[config['TOTAL_SPEND']]),
                 'Gross_Revenue': safe_div(df['Gross_Revenue'], df[config['TOTAL_SPEND']])}, 0.02, ident)
    v['identity_gaps'] = ident
    v['roas_basis'] = ident['roas']['basis']

    save_json(config['VALIDATION_JSON'], v)
    print(f"  Rows {v['rows']} | Cols {v['cols']} | schema_ok={v['schema_ok']} | ROAS basis={v['roas_basis']}")
    return {'df_raw': df, 'validation_dict': v}

