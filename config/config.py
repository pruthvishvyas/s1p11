# config/config.py
import os, json, math
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def _p(*parts):
    return os.path.join(ROOT, *parts)


_SPEND = ['Spend_Search', 'Spend_Social', 'Spend_Email', 'Spend_Display']

CONFIG = {
    # identity / SaaS foundation
    'PIPELINE_VERSION': 'v3.0',
    'DATASET_NAME': 'D2C Weekly Growth & Profit',
    'CLIENT_ID': 'd2c_weekly_growth',
    'OUTCOME_LAYERS': ['UNDERSTAND', 'DECIDE', 'MONITOR'],
    'SAAS_READY': True,
    'ROOT': ROOT,

    # paths (all prefixed by CLIENT_ID, absolute so every entry point works)
    'RAW_CSV': _p('data', 'raw', 'd2c_weekly_growth.csv'),
    'PROCESSED_CSV': _p('data', 'processed', 'd2c_weekly_growth_clean_data.csv'),
    'PROC_CSV': _p('data', 'processed', 'd2c_weekly_growth_clean_data.csv'),
    'FEAT_CSV': _p('data', 'processed', 'd2c_weekly_growth_feature_store.csv'),
    'PROCESSED_DIR': _p('data', 'processed'),
    'REPORTS_DIR': _p('reports'),
    'MODELS_DIR': _p('models'),
    'OUTPUT_DIR': _p('output'),
    'VALIDATION_JSON': _p('data', 'processed', 'validation_report.json'),
    'THRESHOLDS_JSON': _p('data', 'processed', 'thresholds.json'),
    'ML1_CSV': _p('data', 'processed', 'ml_task1_output.csv'),
    'ML2_CSV': _p('data', 'processed', 'ml_task2_output.csv'),
    'DRIVER_CSV': _p('data', 'processed', 'driver_importance.csv'),
    'FORECAST_CSV': _p('data', 'processed', 'forecast_output.csv'),
    'BL_CSV': _p('data', 'processed', 'business_logic_output.csv'),
    'GOALS_JSON': _p('config', 'goals.json'),
    'INSIGHTS_JSON': _p('reports', 'insights.json'),
    'MODEL_CLF': _p('models', 'classifier.pkl'),
    'MODEL_SEG': _p('models', 'segmentation.pkl'),
    'MODEL_DRIVER': _p('models', 'driver_model.pkl'),
    'MODEL_FORECAST': _p('models', 'forecast_model.pkl'),
    'EXCEL_PATH': _p('reports', 'd2c_weekly_growth_report.xlsx'),
    'HTML_PATH': _p('reports', 'dashboard.html'),
    'PPT_REPORT': _p('reports', 'ppt_report.txt'),

    # columns (exact)
    'DATE_COL': 'Week_Start', 'ID_COL': 'Week_ID', 'PROMO_COL': 'Promo_Event',
    'CAT_COLS': ['Quarter', 'Month', 'Promo_Event'],
    'SPEND_COLS': _SPEND,
    'CHANNEL_NAMES': {'Spend_Search': 'Search', 'Spend_Social': 'Social',
                      'Spend_Email': 'Email', 'Spend_Display': 'Display'},
    'SHARE_COLS': ['search_share', 'social_share', 'email_share', 'display_share'],
    'TOTAL_SPEND': 'Total_Marketing_Spend',
    'FUNNEL': ['Impressions', 'Clicks', 'CTR_pct', 'CPC', 'Leads', 'Orders', 'New_Customers'],
    'REVENUE': ['Gross_Revenue', 'Discounts', 'Returns', 'Net_Revenue'],
    'COST_PROFIT': ['COGS', 'Gross_Profit', 'Gross_Margin_pct', 'Payroll', 'Other_Opex',
                    'EBITDA', 'Depreciation', 'Interest', 'Tax', 'Net_Profit', 'Net_Margin_pct'],
    'CASH': ['AR_Outstanding', 'DSO_Days', 'Cash_Balance'],
    'EFFICIENCY': ['ROAS', 'Marketing_ROI_pct', 'CAC', 'Customer_LTV_est', 'LTV_to_CAC',
                   'Repeat_Customer_Rate_pct'],
    'EXPECTED_COLS': ['Week_ID', 'Week_Start', 'Year', 'Quarter', 'Month', 'Promo_Event',
                      'Spend_Search', 'Spend_Social', 'Spend_Email', 'Spend_Display',
                      'Total_Marketing_Spend', 'Impressions', 'Clicks', 'CTR_pct', 'CPC', 'Leads',
                      'Orders', 'New_Customers', 'Repeat_Customer_Rate_pct', 'CAC', 'Units_Sold',
                      'Avg_Order_Value', 'Gross_Revenue', 'Discounts', 'Returns', 'Net_Revenue',
                      'COGS', 'Gross_Profit', 'Gross_Margin_pct', 'Payroll', 'Other_Opex', 'EBITDA',
                      'Depreciation', 'Interest', 'Tax', 'Net_Profit', 'Net_Margin_pct',
                      'AR_Outstanding', 'DSO_Days', 'ROAS', 'Marketing_ROI_pct', 'Cash_Balance',
                      'Customer_LTV_est', 'LTV_to_CAC'],
    'TARGET_PRIMARY': 'Net_Profit',
    'TARGET_SECONDARY': 'Net_Revenue',
    'TARGET_FLAG': 'is_loss_week',
    'TARGET': 'Net_Profit',
    'COL_DATE': 'Week_Start',

    # cleaning
    'CAP_COLS': ['CTR_pct', 'CPC', 'CAC', 'DSO_Days', 'ROAS', 'LTV_to_CAC'],

    # constants
    'RANDOM_STATE': 42, 'TEST_WEEKS': 26, 'N_SPLITS': 5, 'MIN_ROWS': 104,
    'ANOMALY_CONT': 0.05, 'N_CLUSTERS': 3, 'FORECAST_HORIZON_WEEKS': 13,
    'SEASONAL_LAG': 52, 'BASELINE_WINDOW_WEEKS': 13,
    'LAG_WEEKS': [1, 4, 13],
    'LAG_SERIES': ['Net_Revenue', 'Net_Profit', 'Total_Marketing_Spend'],
    'LOSS_MIN_WEEKS': 15, 'RECALL_TARGET': 0.70, 'MAPE_TARGET_PCT': 15.0,
    'SILHOUETTE_TARGET': 0.25, 'SILHOUETTE_MARGIN': 0.05,
    'FORECAST_BAND': (0.10, 0.90),
    'HEALTH_WEIGHTS': {'ROAS': 0.30, 'LTV_to_CAC': 0.20, 'Net_Margin_pct': 0.30,
                       'cash_runway_weeks': 0.20},

    # model feature sets
    'SEG_FEATS': ['ROAS', 'CAC', 'Gross_Margin_pct', 'discount_rate_pct',
                  'marketing_pct_of_revenue', 'conversion_rate_pct'],
    'ANOM_FEATS': ['ROAS', 'CAC', 'CTR_pct', 'CPC', 'conversion_rate_pct', 'lead_to_order_pct',
                   'discount_rate_pct', 'return_rate_pct', 'marketing_pct_of_revenue',
                   'new_customer_share', 'Gross_Margin_pct'],
    'CLF_FEATS': _SPEND + ['search_share', 'social_share', 'email_share', 'display_share',
                           'Total_Marketing_Spend', 'promo_flag', 'discount_rate_pct',
                           'week_of_year', 'is_q4', 'weeks_since_last_promo',
                           'Net_Revenue_lag1', 'Net_Revenue_lag4', 'Net_Revenue_lag13',
                           'Net_Profit_lag1', 'Net_Profit_lag4', 'Net_Profit_lag13',
                           'Total_Marketing_Spend_lag1', 'Total_Marketing_Spend_lag4',
                           'Total_Marketing_Spend_lag13', 'Net_Revenue_rm4', 'Net_Profit_rm4',
                           'Total_Marketing_Spend_rm4'],
    'DRIVER_FEATS': _SPEND + ['search_share', 'social_share', 'email_share', 'display_share',
                              'Total_Marketing_Spend', 'promo_flag', 'discount_rate_pct',
                              'week_of_year', 'is_q4'],
    'FORECAST_EXOG': ['Total_Marketing_Spend'] + _SPEND + ['promo_flag', 'discount_rate_pct',
                                                           'week_of_year', 'is_q4', 't_index'],

    # domain thresholds (None = computed at runtime, never hardcoded)
    'THRESHOLDS': {
        'LTV_CAC_MIN': 3.0,
        'ROAS_BREAKEVEN': None,
        'DSO_MAX_DAYS': None,
        'CASH_FLOOR_WEEKS': 8.0,
        'DISCOUNT_RATE_MAX_PCT': None,
        'RETURN_RATE_MAX_PCT': None,
    },

    # business-logic / simulation settings
    'SHIFT_STEPS_PCT': [-20, -15, -10, -5, 0, 5, 10, 15, 20],
    'DISCOUNT_SIM_MAX_PCT': 25, 'DISCOUNT_SIM_STEP_PCT': 1,
    'SHIFT_BUDGET_PCT': 10,
    'LTV_CAC_STREAK_WEEKS': 4, 'SATURATION_WEEKS': 4,

    'GOAL_DEFAULTS': {
        'net_profit_target': {'value': None, 'unit': 'weekly', 'client_sets': True},
        'net_revenue_target': {'value': None, 'unit': 'weekly', 'client_sets': True},
        'alert_revenue_drop_pct': {'value': 20, 'unit': 'percent',
                                   'description': 'Alert if 4-week Net_Revenue falls this % below prior 4 weeks'},
        'cash_floor_weeks': {'value': 8, 'unit': 'weeks'},
        'ltv_cac_min': {'value': 3.0, 'unit': 'ratio'},
        'forecast_horizon': {'value': 13, 'unit': 'weeks'},
    },

    'TERMINOLOGY': {'revenue': 'Net Revenue', 'customer': 'Customer',
                    'product': 'Order', 'transaction': 'Order'},

    'BIGQUERY': {'project_id': '', 'dataset': '', 'table': 'feat',
                 'credentials_file': 'credentials.json'},
}

for _d in ['data/raw', 'data/processed', 'models', 'reports', 'notebook', 'config',
           'src/data', 'src/features', 'src/models', 'src/analytics', 'src/reporting',
           'output/understand/charts', 'output/decide/simulations', 'output/monitor',
           'output/meta']:
    os.makedirs(_p(*_d.split('/')), exist_ok=True)


# ---------------------------------------------------------------- shared helpers
def safe_div(num, den, fill=0.0):
    """Zero-safe division for scalars or Series."""
    num = pd.to_numeric(num, errors='coerce')
    den = pd.to_numeric(den, errors='coerce')
    if np.isscalar(den) and np.isscalar(num):
        return fill if (pd.isna(den) or den == 0 or pd.isna(num)) else num / den
    if np.isscalar(den):
        return num / den if (not pd.isna(den) and den != 0) else num * 0 + fill
    out = num / den.replace(0, np.nan)
    return out.replace([np.inf, -np.inf], np.nan).fillna(fill)


def sanitize(o, nd=4):
    """Make any object JSON-safe: numpy -> python, NaN/inf -> None, floats rounded."""
    if isinstance(o, dict):
        return {str(k): sanitize(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [sanitize(v, nd) for v in o]
    if isinstance(o, np.ndarray):
        return sanitize(o.tolist(), nd)
    if isinstance(o, pd.DataFrame):
        return sanitize(o.to_dict(orient='records'), nd)
    if isinstance(o, pd.Series):
        return sanitize(o.tolist(), nd)
    if isinstance(o, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(o).strftime('%Y-%m-%d')
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, nd)
    if o is None or isinstance(o, str):
        return o
    return str(o)


def save_json(path, obj, nd=4):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sanitize(obj, nd), f, indent=2, ensure_ascii=False)
    return path


def compute_thresholds(config, df):
    """Runtime thresholds relative to this business (never hardcoded)."""
    t = dict(config['THRESHOLDS'])
    gm = safe_div(df['Gross_Profit'].sum(), df['Net_Revenue'].sum())
    t['ROAS_BREAKEVEN'] = round(1.0 / gm, 4) if gm and gm > 0 else None
    t['DSO_MAX_DAYS'] = float(df['DSO_Days'].quantile(0.75))
    disc = df['discount_rate_pct'] if 'discount_rate_pct' in df else safe_div(df['Discounts'], df['Gross_Revenue']) * 100
    promo = df['promo_flag'] if 'promo_flag' in df else (df['Promo_Event'].fillna('None') != 'None').astype(int)
    base = disc[promo == 0]
    t['DISCOUNT_RATE_MAX_PCT'] = float(2 * (base.median() if len(base) > 0 else disc.median()))
    ret = df['return_rate_pct'] if 'return_rate_pct' in df else safe_div(df['Returns'], df['Gross_Revenue']) * 100
    t['RETURN_RATE_MAX_PCT'] = float(ret.quantile(0.75))
    return t


def rel(path, config=CONFIG):
    """Path relative to project root (for frontend contract)."""
    try:
        return os.path.relpath(path, config['ROOT']).replace(os.sep, '/')
    except Exception:
        return str(path)

