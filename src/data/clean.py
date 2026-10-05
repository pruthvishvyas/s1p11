import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG
import numpy as np
import pandas as pd


def run_clean(config=CONFIG, df_raw=None, **kwargs):
    """Phase 2: cast dtypes, dedupe, IQR-cap rate columns only, add promo_flag. Outputs: df_clean, clean_report."""
    if df_raw is None:
        df_raw = pd.read_csv(config['RAW_CSV'])
    df = df_raw.copy()
    dcol, icol, pcol = config['DATE_COL'], config['ID_COL'], config['PROMO_COL']
    df[dcol] = pd.to_datetime(df[dcol], errors='coerce')
    n0 = len(df)
    df = df.drop_duplicates(subset=[icol], keep='last')
    df = df.dropna(subset=[dcol]).sort_values(dcol).reset_index(drop=True)
    report = {'rows_in': int(n0), 'rows_out': int(len(df)), 'duplicates_removed': int(n0 - len(df))}

    keep_cols = {icol, dcol, 'Year', 'Quarter', 'Month', pcol}
    for c in df.columns:
        if c in keep_cols:
            continue
        df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)   # Depreciation int64 -> float
    df[pcol] = df[pcol].fillna('None').astype(str)
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(df[dcol].dt.year).astype(int)

    # guard inf / NaN in numeric columns (never silently)
    num = [c for c in df.columns if c not in keep_cols]
    df[num] = df[num].replace([np.inf, -np.inf], np.nan)
    nan_before = int(df[num].isna().sum().sum())
    if nan_before > 0:
        df[num] = df[num].ffill().bfill()
        for c in num:
            if df[c].isna().any():
                df[c] = df[c].fillna(df[c].median())
    report['numeric_nans_filled'] = nan_before

    # IQR capping: only rate / efficiency columns (never money columns, never Net_Profit)
    capped = {}
    for c in config['CAP_COLS']:
        if c not in df.columns:
            continue
        q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((df[c] < lo) | (df[c] > hi)).sum())
        df[c] = df[c].clip(lo, hi)
        capped[c] = {'capped_rows': n_out, 'lower': round(float(lo), 4), 'upper': round(float(hi), 4)}
    report['iqr_capped'] = capped

    df['promo_flag'] = (df[pcol] != 'None').astype(int)
    report['promo_weeks'] = int(df['promo_flag'].sum())

    os.makedirs(os.path.dirname(config['PROCESSED_CSV']), exist_ok=True)
    df.to_csv(config['PROCESSED_CSV'], index=False)
    print(f"  Clean rows {len(df)} | duplicates removed {report['duplicates_removed']} | "
          f"capped cells {sum(v['capped_rows'] for v in capped.values())}")
    return {'df_clean': df, 'clean_report': report}

