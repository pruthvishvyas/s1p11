import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, r2_score

YLAGS = ['lag1', 'lag4', 'lag13', 'lag52', 'rm4']


def _ylag_feats(y, i):
    """Lag features for position i from a history list (recursive-safe)."""
    return {'lag1': y[i - 1], 'lag4': y[i - 4], 'lag13': y[i - 13], 'lag52': y[i - 52],
            'rm4': float(np.mean(y[i - 4:i]))}


def _plan_future(df_hist, horizon, config):
    """Assumptions for future weeks: recent average spend, last year's promo calendar and discount depth."""
    n = len(df_hist)
    last = df_hist[config['DATE_COL']].iloc[-1]
    win = df_hist.tail(config['BASELINE_WINDOW_WEEKS'])
    spend = {c: float(win[c].mean()) for c in config['SPEND_COLS']}
    non_promo = df_hist.loc[df_hist['promo_flag'] == 0, 'discount_rate_pct']
    base_disc = float(non_promo.median()) if len(non_promo) else float(df_hist['discount_rate_pct'].median())
    rows = []
    for h in range(1, horizon + 1):
        d = last + pd.Timedelta(weeks=h)
        i = n + h - 1
        j = i - config['SEASONAL_LAG']
        row = dict(spend)
        row[config['TOTAL_SPEND']] = sum(spend.values())
        row['promo_flag'] = int(df_hist['promo_flag'].iloc[j]) if 0 <= j < n else 0
        row['discount_rate_pct'] = float(df_hist['discount_rate_pct'].iloc[j]) if 0 <= j < n else base_disc
        row['week_of_year'] = int(min(d.isocalendar()[1], 52))
        row['is_q4'] = int(d.month >= 10)
        row['t_index'] = i
        row[config['DATE_COL']] = d
        rows.append(row)
    return pd.DataFrame(rows)


def _exog_all(df_hist, horizon, config):
    cols = config['FORECAST_EXOG']
    hist = df_hist[cols].reset_index(drop=True)
    fut = _plan_future(df_hist, horizon, config)[cols]
    return pd.concat([hist, fut], ignore_index=True)


def _design_row(exog, y, i, cols):
    row = {c: float(exog.iloc[i][c]) for c in cols}
    row.update(_ylag_feats(y, i))
    return row


def _fit_model(X, y, config):
    grid = {'max_depth': [2, 3], 'n_estimators': [150, 300]}
    base = GradientBoostingRegressor(learning_rate=0.04, subsample=0.8, random_state=config['RANDOM_STATE'])
    try:
        gs = GridSearchCV(base, grid, cv=TimeSeriesSplit(n_splits=3), scoring='neg_mean_absolute_error')
        gs.fit(X, y)
        return gs.best_estimator_
    except Exception:
        return base.set_params(max_depth=2, n_estimators=200).fit(X, y)


def _forecast(df_hist, y_hist, horizon, config, fit_model=True):
    """Train on df_hist and forecast `horizon` weeks recursively. Returns (model_preds, seasonal_naive, ma4, model)."""
    cols = config['FORECAST_EXOG']
    origin = len(df_hist)
    assert origin >= config['MIN_ROWS'], f"Need at least {config['MIN_ROWS']} rows, got {origin}"
    exog = _exog_all(df_hist, horizon, config)
    y = list(map(float, y_hist[:origin]))
    sn = [y[origin + h - config['SEASONAL_LAG']] for h in range(horizon)]
    ma = [float(np.mean(y[-4:]))] * horizon
    if not fit_model:
        return None, sn, ma, None
    start = config['SEASONAL_LAG']
    Xtr = pd.DataFrame([_design_row(exog, y, i, cols) for i in range(start, origin)])
    ytr = np.array(y[start:origin])
    model = _fit_model(Xtr, ytr, config)
    feat_cols = list(Xtr.columns)
    y_ext, preds = list(y), []
    for h in range(horizon):
        i = origin + h
        x = pd.DataFrame([_design_row(exog, y_ext, i, cols)])[feat_cols]
        p = float(model.predict(x)[0])
        y_ext.append(p)
        preds.append(p)
    model.feature_cols_ = feat_cols
    return preds, sn, ma, model


def _metrics(act, pred, target):
    act, pred = np.array(act, float), np.array(pred, float)
    mae = float(mean_absolute_error(act, pred))
    out = {'mae': round(mae, 2), 'r2': round(float(r2_score(act, pred)), 4),
           'wape_pct': round(float(np.abs(act - pred).sum() / max(1e-9, np.abs(act).sum()) * 100), 2)}
    nz = np.abs(act) > 0
    out['mape_pct'] = round(float(np.mean(np.abs(act[nz] - pred[nz]) / np.abs(act[nz])) * 100), 2) if nz.any() else None
    return out


def _backtest(df, target, config):
    y = df[target].values.astype(float)
    n, H, T = len(y), config['FORECAST_HORIZON_WEEKS'], config['TEST_WEEKS']
    act, mod, sn, ma = [], [], [], []
    for o in range(n - T, n, H):
        hh = min(H, n - o)
        m, s, a, _ = _forecast(df.iloc[:o], y[:o], hh, config)
        act += list(y[o:o + hh]); mod += m; sn += s; ma += a
    return np.array(act), np.array(mod), np.array(sn), np.array(ma)


def _score_rows(df, bundle, config):
    if bundle and bundle.get('model') is not None:
        X = df[bundle['features']].replace([np.inf, -np.inf], np.nan).fillna(pd.Series(bundle['medians']))
        df['loss_risk_prob'] = bundle['model'].predict_proba(X)[:, 1]
        df['loss_risk_flag'] = (df['loss_risk_prob'] >= bundle['threshold']).astype(int)
    else:
        df['loss_risk_prob'] = np.nan
        df['loss_risk_flag'] = df.get('loss_risk_rule', 0)
    return df


def _next_week_risk(df, bundle, config):
    """Loss-risk score for the coming week under the stated planning assumptions."""
    plan = _plan_future(df, 1, config).iloc[0].to_dict()
    n = len(df)
    row = {c: plan.get(c) for c in config['SPEND_COLS'] + [config['TOTAL_SPEND'], 'promo_flag', 'discount_rate_pct', 'week_of_year', 'is_q4']}
    tot = row[config['TOTAL_SPEND']]
    for col, sh in zip(config['SPEND_COLS'], config['SHARE_COLS']):
        row[sh] = row[col] / tot if tot else 0.0
    row['weeks_since_last_promo'] = 0 if row['promo_flag'] == 1 else min(int(df['weeks_since_last_promo'].iloc[-1]) + 1, 52)
    for s in config['LAG_SERIES']:
        yv = df[s].values
        for k in config['LAG_WEEKS']:
            row[f'{s}_lag{k}'] = float(yv[n - k])
        row[f'{s}_rm4'] = float(np.mean(yv[n - 4:n]))
    thr = None
    try:
        from config.config import compute_thresholds
        thr = compute_thresholds(config, df)
    except Exception:
        pass
    rule_flag = int(row['promo_flag'] == 1 and thr is not None and row['discount_rate_pct'] > thr['DISCOUNT_RATE_MAX_PCT'])
    if bundle and bundle.get('model') is not None:
        x = pd.DataFrame([row]).reindex(columns=bundle['features'])
        x = x.fillna(pd.Series(bundle['medians']))
        p = float(bundle['model'].predict_proba(x)[0, 1])
        return {'week_start': plan[config['DATE_COL']].strftime('%Y-%m-%d'), 'probability': round(p, 4),
                'threshold': bundle['threshold'], 'at_risk': bool(p >= bundle['threshold']), 'method': 'ml',
                'assumed_promo': int(row['promo_flag'])}
    return {'week_start': plan[config['DATE_COL']].strftime('%Y-%m-%d'), 'probability': None, 'threshold': None,
            'at_risk': bool(rule_flag), 'method': 'rule', 'assumed_promo': int(row['promo_flag'])}


def run_predictor(config=CONFIG, df_feat=None, clf_model=None, **kwargs):
    """Phase 7: score loss-week risk, forecast Net_Revenue and Net_Profit 13 weeks (baselines first). Outputs: df_feat, forecast_df, forecast_report."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    if clf_model is None and os.path.exists(config['MODEL_CLF']):
        clf_model = joblib.load(config['MODEL_CLF'])
    df = df_feat.copy().sort_values(config['DATE_COL']).reset_index(drop=True)
    assert len(df) >= config['MIN_ROWS'], f"Need at least {config['MIN_ROWS']} rows, got {len(df)}"
    H = config['FORECAST_HORIZON_WEEKS']
    q_lo, q_hi = config['FORECAST_BAND']
    df = _score_rows(df, clf_model, config)

    plan = _plan_future(df, H, config)
    fc = pd.DataFrame({config['DATE_COL']: plan[config['DATE_COL']], 'horizon_week': range(1, H + 1),
                       'assumed_promo_flag': plan['promo_flag'], 'assumed_discount_rate_pct': plan['discount_rate_pct']})
    report = {'horizon_weeks': H, 'targets': {}, 'band': '80% prediction band from holdout residual quantiles',
              'assumptions': ['Marketing spend per channel held at the last 13-week average.',
                              "Promo calendar and discount depth repeat the same week of last year.",
                              'Forecast is a planning view, not a guarantee.']}
    models = {}
    for target in [config['TARGET_SECONDARY'], config['TARGET_PRIMARY']]:
        y = df[target].values.astype(float)
        act, mod, sn, ma = _backtest(df, target, config)
        m_mod, m_sn, m_ma = _metrics(act, mod, target), _metrics(act, sn, target), _metrics(act, ma, target)
        best_base = 'seasonal_naive' if m_sn['mae'] <= m_ma['mae'] else 'moving_avg_4w'
        base_mae = min(m_sn['mae'], m_ma['mae'])
        accepted = m_mod['mae'] < base_mae
        chosen_pred = mod if accepted else (sn if best_base == 'seasonal_naive' else ma)
        resid = act - chosen_pred
        lo_q, hi_q = float(np.quantile(resid, q_lo)), float(np.quantile(resid, q_hi))
        if accepted:
            preds, _, _, model = _forecast(df, y, H, config)
            method = 'GradientBoostingRegressor'
            models[target] = model
        else:
            _, sn_f, ma_f, _ = _forecast(df, y, H, config, fit_model=False)
            preds = sn_f if best_base == 'seasonal_naive' else ma_f
            method, models[target] = best_base, None
        preds = np.array(preds, float)
        lo, hi = preds + lo_q, preds + hi_q
        if target == 'Net_Revenue':
            preds, lo, hi = np.maximum(preds, 0), np.maximum(lo, 0), np.maximum(hi, 0)
        fc[f'{target}_forecast'], fc[f'{target}_lo80'], fc[f'{target}_hi80'], fc[f'{target}_method'] = preds, lo, hi, method
        mape = m_mod['mape_pct'] if accepted else (m_sn['mape_pct'] if best_base == 'seasonal_naive' else m_ma['mape_pct'])
        claim = bool(accepted and (target != 'Net_Revenue' or (mape is not None and mape < config['MAPE_TARGET_PCT'])))
        report['targets'][target] = {
            'method': method, 'model_accepted': bool(accepted), 'best_baseline': best_base,
            'holdout_weeks': int(len(act)), 'model_metrics': m_mod, 'seasonal_naive_metrics': m_sn, 'moving_avg_4w_metrics': m_ma,
            'shipped_mape_pct': mape, 'mape_target_pct': config['MAPE_TARGET_PCT'] if target == 'Net_Revenue' else None,
            'mape_target_met': bool(mape is not None and mape < config['MAPE_TARGET_PCT']) if target == 'Net_Revenue' else None,
            'accuracy_claim': claim, 'band_residual_q10': round(lo_q, 2), 'band_residual_q90': round(hi_q, 2),
            'note': ('Model beat the best baseline MAE on the holdout.' if accepted else
                     f'Model did not beat {best_base} MAE on holdout; baseline shipped. No accuracy claim for the model.')}
        if target == 'Net_Profit' and not accepted:
            print(f"  NOTE: Net_Profit model did not beat baseline ({best_base}); shipping baseline with prediction band, no accuracy claim.")
        report['targets'][target]['next_13w_total'] = round(float(preds.sum()), 2)
        report['targets'][target]['last_13w_actual_total'] = round(float(y[-H:].sum()), 2)
        print(f"  {target}: shipped {method} | holdout MAE model {m_mod['mae']:.0f} vs baseline {base_mae:.0f} | MAPE shipped {mape}")

    rev_next = report['targets']['Net_Revenue']['next_13w_total']
    rev_last = report['targets']['Net_Revenue']['last_13w_actual_total']
    chg = (rev_next - rev_last) / rev_last * 100 if rev_last else 0.0
    report['direction'] = {'net_revenue_change_pct_vs_last_13w': round(chg, 2),
                           'label': 'up' if chg > 2 else ('down' if chg < -2 else 'flat')}
    report['next_week_loss_risk'] = _next_week_risk(df, clf_model, config)

    os.makedirs(config['MODELS_DIR'], exist_ok=True)
    joblib.dump({'models': models, 'report': report, 'exog_cols': config['FORECAST_EXOG'],
                 'type': 'GradientBoostingRegressor (or baseline if it won)'}, config['MODEL_FORECAST'])
    fc.to_csv(config['FORECAST_CSV'], index=False)
    ml2 = df[[config['ID_COL'], config['DATE_COL'], 'is_anomaly', 'anomaly_score', 'anomaly_reason',
              config['TARGET_FLAG'], 'loss_risk_rule', 'loss_risk_prob', 'loss_risk_flag']]
    ml2.to_csv(config['ML2_CSV'], index=False)
    df.to_csv(config['FEAT_CSV'], index=False)
    return {'df_feat': df, 'forecast_df': fc, 'forecast_report': report}

