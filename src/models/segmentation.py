import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.config import CONFIG
import numpy as np
import pandas as pd
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score


def _names(k):
    if k == 3:
        return ['Efficient', 'Steady', 'Burn']
    if k == 2:
        return ['Efficient', 'Burn']
    if k == 4:
        return ['Efficient', 'Steady', 'Watch', 'Burn']
    return ['Efficient'] + [f'Tier {i}' for i in range(2, k)] + ['Burn']


def run_segmentation(config=CONFIG, df_feat=None, **kwargs):
    """Phase 5: KMeans week regimes (Efficient / Steady / Burn). Outputs: seg_model, cluster_profile, df_feat, seg_report."""
    if df_feat is None:
        df_feat = pd.read_csv(config['FEAT_CSV'], parse_dates=[config['DATE_COL']])
    df = df_feat.copy()
    assert len(df) >= config['MIN_ROWS'], f"Need at least {config['MIN_ROWS']} rows, got {len(df)}"
    feats = [c for c in config['SEG_FEATS'] if c in df.columns]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    sil = {}
    for k in range(2, 6):
        km = KMeans(n_clusters=k, n_init=10, random_state=config['RANDOM_STATE']).fit(Xs)
        sil[k] = float(silhouette_score(Xs, km.labels_))
    k_cfg = config['N_CLUSTERS']
    best_k = max(sil, key=sil.get)
    k = best_k if sil[best_k] - sil[k_cfg] > config['SILHOUETTE_MARGIN'] else k_cfg
    model = KMeans(n_clusters=k, n_init=10, random_state=config['RANDOM_STATE']).fit(Xs)
    df['cluster'] = model.labels_

    # label by mean Net_Margin_pct (data-derived, best to worst)
    ranking = df.groupby('cluster')['Net_Margin_pct'].mean().sort_values(ascending=False)
    names = _names(k)
    label_map = {int(c): names[i] for i, c in enumerate(ranking.index)}
    tier_map = {int(c): f'TIER_{i + 1}' for i, c in enumerate(ranking.index)}
    df['segment'] = df['cluster'].map(label_map)
    df['segment_tier'] = df['cluster'].map(tier_map)

    prof_cols = feats + ['Net_Margin_pct', 'Net_Profit', 'Net_Revenue']
    prof = df.groupby('segment')[prof_cols].mean()
    prof.insert(0, 'weeks', df.groupby('segment').size())
    prof['loss_week_rate'] = df.groupby('segment')[config['TARGET_FLAG']].mean()
    prof = prof.reindex([label_map[int(c)] for c in ranking.index]).reset_index()

    final_sil = sil[k]
    profit_order_ok = bool(prof['Net_Profit'].is_monotonic_decreasing)
    report = {'k': int(k), 'silhouette_by_k': {int(a): round(b, 4) for a, b in sil.items()},
              'silhouette': round(final_sil, 4), 'silhouette_target': config['SILHOUETTE_TARGET'],
              'target_met': bool(final_sil >= config['SILHOUETTE_TARGET']),
              'k_kept_at_config': bool(k == k_cfg), 'profit_separation_monotonic': profit_order_ok,
              'features': feats, 'label_map': {str(a): b for a, b in label_map.items()}}
    if not report['target_met']:
        print(f"  NOTE: silhouette {final_sil:.3f} below target {config['SILHOUETTE_TARGET']}; regimes overlap, treat as indicative.")

    os.makedirs(config['MODELS_DIR'], exist_ok=True)
    joblib.dump({'model': model, 'scaler': scaler, 'features': feats, 'label_map': label_map}, config['MODEL_SEG'])
    out = df[[config['ID_COL'], config['DATE_COL'], 'cluster', 'segment', 'segment_tier', 'Net_Margin_pct', 'Net_Profit']]
    out.to_csv(config['ML1_CSV'], index=False)
    print(f"  Segmentation k={k} | silhouette={final_sil:.3f} | counts={df['segment'].value_counts().to_dict()}")
    return {'seg_model': model, 'cluster_profile': prof, 'df_feat': df, 'seg_report': report}

