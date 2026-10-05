import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG, save_json, compute_thresholds
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import IsolationForest, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import recall_score, precision_score, roc_auc_score, r2_score, mean_absolute_error
from sklearn.inspection import permutation_importance


def _label(c):
    return c.replace('_pct', ' %').replace('_', ' ')


def _anomalies(config, df):
    feats = [c for c in config['ANOM_FEATS'] if c in df.columns]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    med = X.median()
    X = X.fillna(med)
    sc = StandardScaler()
    Z = sc.fit_transform(X)
    iso = IsolationForest(n_estimators=200, contamination=config['ANOMALY_CONT'], random_state=config['RANDOM_STATE'])
    pred = iso.fit_predict(Z)
    df['is_anomaly'] = (pred == -1).astype(int)
    df['anomaly_score'] = -iso.score_samples(Z)
    reasons = []
    for i in range(len(df)):
        if pred[i] != -1:
            reasons.append('')
            continue
        j = int(np.argmax(np.abs(Z[i])))
        side = 'above' if Z[i, j] > 0 else 'below'
        reasons.append(f"{_label(feats[j])} is {abs(Z[i, j]):.1f} std dev {side} normal ({X.iloc[i, j]:.2f} vs typical {med.iloc[j]:.2f})")
    df['anomaly_reason'] = reasons
    return df


def _make_models(rs):
    return {
        'LogisticRegression': lambda: make_pipeline(StandardScaler(), LogisticRegression(class_weight='balanced', C=0.5, max_iter=2000)),
        'GradientBoosting': lambda: GradientBoostingClassifier(n_estimators=150, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=rs),
    }


def _fit(name, model, X, y):
    if name == 'GradientBoosting':
        w = np.where(y == 1, (y == 0).sum() / max(1, (y == 1).sum()), 1.0)
        model.fit(X, y, sample_weight=w)
    else:
        model.fit(X, y)
    return model


def _loss_week_model(config, df, thr):
    tgt = config['TARGET_FLAG']
    y = df[tgt].astype(int).reset_index(drop=True)
    feats = [c for c in config['CLF_FEATS'] if c in df.columns]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    med = X.median()
    X = X.fillna(med).reset_index(drop=True)
    df['loss_risk_rule'] = ((df['promo_flag'] == 1) & (df['discount_rate_pct'] > thr['DISCOUNT_RATE_MAX_PCT'])).astype(int)
    n_loss = int(y.sum())
    rule_recall = float(recall_score(y, df['loss_risk_rule'], zero_division=0))
    report = {'n_loss_weeks': n_loss, 'n_weeks': int(len(y)), 'rule_recall': round(rule_recall, 4),
              'features_used': feats, 'excluded_for_leakage': ['Net_Profit', 'EBITDA', 'Net_Margin_pct', 'Tax', 'Gross_Profit']}
    bundle = {'model': None, 'features': feats, 'medians': med.to_dict(), 'threshold': None,
              'method': 'rule', 'encoders': {}, 'model_name': 'rule'}
    if n_loss < config['LOSS_MIN_WEEKS'] or (len(y) - n_loss) < config['LOSS_MIN_WEEKS']:
        report.update({'method': 'rule', 'skipped': True,
                       'reason': f"Only {n_loss} loss weeks (need {config['LOSS_MIN_WEEKS']}); using rule-based flag."})
        print('  ' + report['reason'])
        joblib.dump(bundle, config['MODEL_CLF'])
        return bundle, report, {}

    tscv = TimeSeriesSplit(n_splits=config['N_SPLITS'])
    results, oof_all = {}, {}
    for name, mk in _make_models(config['RANDOM_STATE']).items():
        oof = np.full(len(y), np.nan)
        for tr, te in tscv.split(X):
            if y.iloc[tr].nunique() < 2 or len(tr) < 30:
                continue
            m = _fit(name, mk(), X.iloc[tr], y.iloc[tr])
            oof[te] = m.predict_proba(X.iloc[te])[:, 1]
        mask = ~np.isnan(oof)
        if mask.sum() == 0 or y[mask].nunique() < 2:
            continue
        best_th, best = None, None
        for th in np.arange(0.05, 0.95, 0.05):
            pr = (oof[mask] >= th).astype(int)
            rec = recall_score(y[mask], pr, zero_division=0)
            prec = precision_score(y[mask], pr, zero_division=0)
            if rec >= config['RECALL_TARGET'] and (best is None or prec > best[1]):
                best_th, best = float(th), (rec, prec)
        if best_th is None:       # target not reachable: take the threshold with best recall (lowest threshold)
            best_th = 0.05
            pr = (oof[mask] >= best_th).astype(int)
            best = (recall_score(y[mask], pr, zero_division=0), precision_score(y[mask], pr, zero_division=0))
        results[name] = {'threshold': round(best_th, 2), 'recall': round(float(best[0]), 4), 'precision': round(float(best[1]), 4),
                         'roc_auc': round(float(roc_auc_score(y[mask], oof[mask])), 4), 'oof_weeks': int(mask.sum())}
        oof_all[name] = best_th
    if not results:
        report.update({'method': 'rule', 'skipped': True, 'reason': 'Time-series folds had no usable loss weeks; using rule-based flag.'})
        joblib.dump(bundle, config['MODEL_CLF'])
        return bundle, report, {}

    chosen = max(results, key=lambda n: (results[n]['recall'] >= config['RECALL_TARGET'], results[n]['roc_auc']))
    final = _fit(chosen, _make_models(config['RANDOM_STATE'])[chosen](), X, y)
    if chosen == 'GradientBoosting':
        imp = pd.Series(final.feature_importances_, index=feats)
    else:
        imp = pd.Series(np.abs(final[-1].coef_[0]), index=feats)
    imp = (imp / imp.sum()).sort_values(ascending=False)
    bundle.update({'model': final, 'threshold': oof_all[chosen], 'method': 'ml', 'model_name': chosen})
    joblib.dump(bundle, config['MODEL_CLF'])
    report.update({'method': 'ml', 'skipped': False, 'candidates': results, 'chosen': chosen,
                   'recall': results[chosen]['recall'], 'precision': results[chosen]['precision'],
                   'roc_auc': results[chosen]['roc_auc'], 'threshold': results[chosen]['threshold'],
                   'recall_target': config['RECALL_TARGET'],
                   'target_met': bool(results[chosen]['recall'] >= config['RECALL_TARGET']),
                   'top_features': {k: round(float(v), 4) for k, v in imp.head(10).items()},
                   'note': 'Metrics are out-of-fold over time-ordered splits; loss_risk_prob on training weeks is in-sample.'})
    print(f"  Loss-week model: {chosen} | recall {report['recall']:.2f} | precision {report['precision']:.2f} | AUC {report['roc_auc']:.2f}")
    return bundle, report, imp.to_dict()


def _driver_model(config, df):
    feats = [c for c in config['DRIVER_FEATS'] if c in df.columns]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    med = X.median()
    X = X.fillna(med)
    y = df[config['TARGET_PRIMARY']].astype(float)
    T = min(config['TEST_WEEKS'], max(1, len(df) // 4))
    Xtr, Xte, ytr, yte = X.iloc[:-T], X.iloc[-T:], y.iloc[:-T], y.iloc[-T:]
    mk = lambda: GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=config['RANDOM_STATE'])
    m = mk().fit(Xtr, ytr)
    pred = m.predict(Xte)
    r2, mae = float(r2_score(yte, pred)), float(mean_absolute_error(yte, pred))
    pi = permutation_importance(m, Xte, yte, n_repeats=20, random_state=config['RANDOM_STATE'], scoring='neg_mean_absolute_error')
    imp = pd.DataFrame({'feature': feats, 'importance_mean': pi.importances_mean, 'importance_std': pi.importances_std})
    imp = imp.sort_values('importance_mean', ascending=False).reset_index(drop=True)
    pos = imp['importance_mean'].clip(lower=0)
    imp['importance_share'] = pos / pos.sum() if pos.sum() > 0 else 0.0
    share = dict(zip(imp['feature'], imp['importance_share']))
    channel_imp = {}
    for col, sh in zip(config['SPEND_COLS'], config['SHARE_COLS']):
        channel_imp[config['CHANNEL_NAMES'][col]] = float(share.get(col, 0) + share.get(sh, 0))
    group_imp = {'promo': float(sum(share.get(c, 0) for c in ['promo_flag', 'discount_rate_pct'])),
                 'seasonality': float(sum(share.get(c, 0) for c in ['week_of_year', 'is_q4'])),
                 'total_spend': float(share.get('Total_Marketing_Spend', 0))}
    final = mk().fit(X, y)
    joblib.dump({'model': final, 'features': feats, 'medians': med.to_dict()}, config['MODEL_DRIVER'])
    imp.to_csv(config['DRIVER_CSV'], index=False)
    rep = {'holdout_weeks': int(T), 'holdout_r2': round(r2, 4), 'holdout_mae': round(mae, 2),
           'reliable': bool(r2 > 0.2), 'channel_importance': channel_imp, 'group_importance': group_imp,
           'note': 'Permutation importance on the last holdout weeks. Associations, not proven causes.'}
    if not rep['reliable']:
        print(f"  NOTE: driver model holdout R2 {r2:.2f} is weak; channel ranking is indicative only.")
    return rep, imp, channel_imp


def run_classifier(config=CONFIG, df_feat=None, **kwargs):
    """Phase 6: anomaly detection, loss-week classifier, Net_Profit driver model. Outputs: clf_model, clf_report, df_feat, driver_report, channel_importance."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    df = df_feat.copy()
    assert len(df) >= config['MIN_ROWS'], f"Need at least {config['MIN_ROWS']} rows, got {len(df)}"
    thr = kwargs.get('thresholds') or compute_thresholds(config, df)
    df = _anomalies(config, df)
    print(f"  Anomaly weeks flagged: {int(df['is_anomaly'].sum())}")
    bundle, clf_report, clf_imp = _loss_week_model(config, df, thr)
    drv_report, drv_imp, channel_imp = _driver_model(config, df)
    cols = [config['ID_COL'], config['DATE_COL'], 'is_anomaly', 'anomaly_score', 'anomaly_reason', config['TARGET_FLAG'], 'loss_risk_rule']
    df[cols].to_csv(config['ML2_CSV'], index=False)
    return {'clf_model': bundle, 'clf_report': clf_report, 'df_feat': df, 'driver_report': drv_report,
            'driver_importance': drv_imp, 'channel_importance': channel_imp}

