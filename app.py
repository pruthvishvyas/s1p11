import os, sys, json, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.config import CONFIG, safe_div, compute_thresholds
import numpy as np
import pandas as pd
import joblib
import gradio as gr
try:
    import plotly.express as px
except Exception:
    px = None

C = CONFIG
NOT_RUN = ("<div style='color:#C62828;font-family:sans-serif;padding:20px'>"
           "⚠️ Pipeline not run yet.<br>Fix: <code>python main.py</code></div>")
CSS = """
.card{background:#fff;border:1px solid #d9d9d9;border-radius:10px;padding:14px 16px;min-width:170px;flex:1;color:#1a1a1a}
.card *{color:#1a1a1a}
.lbl{font-size:.8rem;font-weight:600;color:#1a1a1a}
.val{font-size:1.6rem;font-weight:700;color:#1a1a1a}
.sub{font-size:.8rem;color:#1a1a1a}
.row{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:12px}
.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:.75rem;font-weight:700;color:#fff;margin-right:6px}
.ins{background:#fff;border:1px solid #d9d9d9;border-radius:10px;padding:12px 14px;margin-bottom:10px;color:#1a1a1a}
.ins *{color:#1a1a1a}
.fnd{font-size:.97rem;font-weight:600;color:#1a1a1a;margin:8px 0}
.evd{background:rgba(0,0,0,0.04);color:#222;padding:8px;border-radius:4px;margin-bottom:6px}
.act{border-left:3px solid #2E7D32;background:#f0fdf4;color:#1a3d2e;padding:8px}
.slide{background:#fff;border:1px solid #d9d9d9;border-radius:10px;padding:12px 16px;margin-bottom:10px;color:#1a1a1a}
.slide h3{color:#1565C0;margin:0 0 6px 0}
.slide li{color:#1a1a1a}
"""
SEV = {'HIGH': '#C62828', 'MEDIUM': '#E65100', 'LOW': '#2E7D32'}


def _df():
    if not os.path.exists(C['FEAT_CSV']):
        return None
    d = pd.read_csv(C['FEAT_CSV'], parse_dates=[C['DATE_COL']])
    return d.sort_values(C['DATE_COL']).reset_index(drop=True)


def _card(label, value, sub=''):
    return f"<div class='card'><div class='lbl'>{label}</div><div class='val'>{value}</div><div class='sub'>{sub}</div></div>"


def _chg(a, b):
    return '' if not b else f"{(a - b) / abs(b) * 100:+.1f}% vs prior 13 weeks"


# ------------------------------------------------------------------ tab 1
def kpi_html():
    df = _df()
    if df is None:
        return NOT_RUN
    H = 13
    a, b = df.tail(H), df.iloc[-2 * H:-H]
    rev, prof = a['Net_Revenue'].sum(), a['Net_Profit'].sum()
    marg = safe_div(prof, rev) * 100
    cards = [
        _card('Net Revenue (13 wks)', f"{rev:,.0f}", _chg(rev, b['Net_Revenue'].sum())),
        _card('Net Profit (13 wks)', f"{prof:,.0f}", _chg(prof, b['Net_Profit'].sum())),
        _card('Net Margin %', f"{marg:.1f}%", 'last 13 weeks'),
        _card('ROAS', f"{safe_div(rev, a[C['TOTAL_SPEND']].sum()):.2f}", 'Net Revenue / marketing spend'),
        _card('CAC', f"{a['CAC'].mean():.1f}", _chg(a['CAC'].mean(), b['CAC'].mean())),
        _card('LTV to CAC', f"{a['LTV_to_CAC'].mean():.1f}", f"floor {C['THRESHOLDS']['LTV_CAC_MIN']:.1f}"),
        _card('Cash Balance', f"{df['Cash_Balance'].iloc[-1]:,.0f}", 'latest week'),
        _card('Cash runway', f"{df['cash_runway_weeks'].iloc[-1]:.1f} wks", f"floor {C['THRESHOLDS']['CASH_FLOOR_WEEKS']:.0f} weeks"),
        _card('Loss weeks', f"{int(df[C['TARGET_FLAG']].sum())}", f"{int(df[C['TARGET_FLAG']].tail(52).sum())} in last 52 weeks"),
        _card('Unusual weeks', f"{int(df['is_anomaly'].sum()) if 'is_anomaly' in df else 0}", 'flagged by IsolationForest'),
    ]
    return "<div class='row'>" + ''.join(cards[:5]) + "</div><div class='row'>" + ''.join(cards[5:]) + "</div>"


# ------------------------------------------------------------------ tab 2
def core_figs():
    df = _df()
    if df is None or px is None:
        return [None, None, None, None]
    thr = compute_thresholds(C, df)
    d = df.assign(Promo=np.where(df['promo_flag'] == 1, 'Promo week', 'Normal week'))
    f1 = px.line(d, x=C['DATE_COL'], y=['Net_Revenue', 'Net_Profit'], title='Net Revenue and Net Profit by week')
    f2 = px.histogram(d, x='discount_rate_pct', color='Promo', nbins=40, title='Discount rate % (red line = limit)')
    f2.add_vline(x=thr['DISCOUNT_RATE_MAX_PCT'], line_color='#C62828', line_dash='dash')
    f3 = px.histogram(d, x='LTV_to_CAC', nbins=40, title='LTV to CAC (red line = minimum)')
    f3.add_vline(x=thr['LTV_CAC_MIN'], line_color='#C62828', line_dash='dash')
    f4 = px.histogram(d, x='DSO_Days', nbins=30, title='DSO days (red line = limit, 75th percentile)')
    f4.add_vline(x=thr['DSO_MAX_DAYS'], line_color='#C62828', line_dash='dash')
    return [f1, f2, f3, f4]


# ------------------------------------------------------------------ tab 3
def domain_tables():
    df = _df()
    if df is None:
        e = pd.DataFrame({'Message': ['Pipeline not run yet. Fix: python main.py']})
        return e, e, e
    g = df.groupby(C['PROMO_COL'])
    promo = pd.DataFrame({'Weeks': g.size(), 'Median Net Profit': g['Net_Profit'].median(), 'Median Net Margin %': g['Net_Margin_pct'].median(),
                          'Median discount %': g['discount_rate_pct'].median(), 'Loss-week rate %': g[C['TARGET_FLAG']].mean() * 100}).round(2).reset_index()
    if 'segment' in df:
        gs = df.groupby('segment')
        seg = pd.DataFrame({'Weeks': gs.size(), 'Avg Net Margin %': gs['Net_Margin_pct'].mean(), 'Avg Net Profit': gs['Net_Profit'].mean(),
                            'Avg ROAS': gs['ROAS'].mean(), 'Avg CAC': gs['CAC'].mean(), 'Loss-week rate %': gs[C['TARGET_FLAG']].mean() * 100}).round(2).reset_index()
    else:
        seg = pd.DataFrame({'Message': ['No segments yet']})
    rows = []
    last13 = df.tail(13)
    for col, sh in zip(C['SPEND_COLS'], C['SHARE_COLS']):
        rows.append({'Channel': C['CHANNEL_NAMES'][col], 'Total spend': df[col].sum(), 'Share of spend % (last 13 wks)': last13[sh].mean() * 100,
                     'Correlation with Orders': df[col].corr(df['Orders']), 'Correlation with Net Profit': df[col].corr(df['Net_Profit'])})
    return promo, seg, pd.DataFrame(rows).round(2)


# ------------------------------------------------------------------ tab 4
def priority_table():
    df = _df()
    if df is None:
        return pd.DataFrame({'Message': ['Pipeline not run yet. Fix: python main.py']})
    key = 'loss_risk_prob' if 'loss_risk_prob' in df and df['loss_risk_prob'].notna().any() else 'health_score'
    asc = key == 'health_score'
    cols = [c for c in [C['ID_COL'], C[ 'DATE_COL'], C['PROMO_COL'], C['TOTAL_SPEND'], 'discount_rate_pct', 'Net_Profit', 'Net_Margin_pct',
                        'loss_risk_prob', 'loss_risk_flag', 'segment', 'is_anomaly', 'health_score'] if c in df.columns]
    t = df.sort_values(key, ascending=asc).head(200)[cols].copy()
    t[C['DATE_COL']] = t[C['DATE_COL']].dt.strftime('%Y-%m-%d')
    return t.round(3)


# ------------------------------------------------------------------ tab 5
def insights_html():
    if not os.path.exists(C['INSIGHTS_JSON']):
        return NOT_RUN
    with open(C['INSIGHTS_JSON'], 'r', encoding='utf-8') as f:
        items = json.load(f)
    out = []
    for i in items:
        out.append(f"<div class='ins'><span class='pill' style='background:{SEV.get(i['severity'], '#555')}'>{i['severity']}</span>"
                   f"<span class='pill' style='background:#263238'>{i['category']}</span>"
                   f"<div class='fnd'>{i['finding']}</div><div class='evd'>{i['evidence']}</div>"
                   f"<div class='act'><b>Action:</b> {i['action']}</div></div>")
    return ''.join(out)


# ------------------------------------------------------------------ tab 6
CAPS = {'01': 'Net Revenue and Net Profit with 13-week averages.', '02': 'How the marketing budget is split across channels.',
        '03': 'Profit and discount depth in promo versus normal weeks.', '04': 'How spend correlates with orders and profit at 0-2 week delays.',
        '05': 'Lifetime value versus acquisition cost against the 3.0 floor.', '06': 'Average net margin by month and year.',
        '07': 'Cash balance against the runway floor, plus receivables and DSO.'}


def gallery_items():
    files = sorted(glob.glob(os.path.join(C['REPORTS_DIR'], '*.png')))
    return [(f, f"{os.path.basename(f)[:-4].replace('_', ' ')}: {CAPS.get(os.path.basename(f)[:2], 'Pipeline chart.')}") for f in files]


# ------------------------------------------------------------------ tab 7
def boardroom_html():
    if not os.path.exists(C['PPT_REPORT']):
        return ("<div style='color:#C62828;font-family:sans-serif;padding:20px'>⚠️ Report not generated yet.<br>"
                "Fix: <code>python report.py</code></div>")
    with open(C['PPT_REPORT'], 'r', encoding='utf-8') as f:
        txt = f.read()
    blocks = re.split(r'(?m)^(SLIDE \d+ — .+)$', txt)
    html = ["<div style='max-height:640px;overflow-y:auto'>"]
    for k in range(1, len(blocks), 2):
        body = [l[2:] for l in blocks[k + 1].strip().splitlines() if l.startswith('- ')]
        body = [re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', b) for b in body]
        html.append(f"<div class='slide'><h3>{blocks[k]}</h3><ul>" + ''.join(f'<li>{b}</li>' for b in body) + '</ul></div>')
    html.append('</div>')
    return ''.join(html)


# ------------------------------------------------------------------ tab 8
def forecaster(search, social, email, display, promo, discount, woy):
    try:
        bundle = joblib.load(C['MODEL_CLF'])
    except Exception as e:
        return f"<div style='color:#C62828'>Model load failed: {e}<br>Fix: python main.py</div>"
    df = _df()
    if df is None:
        return NOT_RUN
    thr = compute_thresholds(C, df)
    sp = {'Spend_Search': float(search or 0), 'Spend_Social': float(social or 0), 'Spend_Email': float(email or 0), 'Spend_Display': float(display or 0)}
    tot = sum(sp.values())
    row = dict(sp)
    row[C['TOTAL_SPEND']] = tot
    for col, sh in zip(C['SPEND_COLS'], C['SHARE_COLS']):
        row[sh] = sp[col] / tot if tot > 0 else 0.0
    promo = int(bool(promo))
    row.update({'promo_flag': promo, 'discount_rate_pct': float(discount or 0), 'week_of_year': int(woy), 'is_q4': int(int(woy) >= 40)})
    row['weeks_since_last_promo'] = 0 if promo else min(int(df['weeks_since_last_promo'].iloc[-1]) + 1, 52)
    n = len(df)
    for s in C['LAG_SERIES']:
        y = df[s].values
        for k in C['LAG_WEEKS']:
            row[f'{s}_lag{k}'] = float(y[n - k])
        row[f'{s}_rm4'] = float(np.mean(y[n - 4:n]))
    if bundle.get('model') is not None:
        x = pd.DataFrame([row]).reindex(columns=bundle['features']).fillna(pd.Series(bundle['medians']))
        p = float(bundle['model'].predict_proba(x)[0, 1])
        th = float(bundle['threshold'])
        label = 'HIGH' if p >= th else ('MEDIUM' if p >= th / 2 else 'LOW')
        detail = f"Probability of a loss week: <b>{p * 100:.1f}%</b> (alert threshold {th * 100:.0f}%)"
    else:
        hit = promo == 1 and float(discount or 0) > thr['DISCOUNT_RATE_MAX_PCT']
        label = 'HIGH' if hit else 'LOW'
        detail = f"Rule-based check: promo with discount above {thr['DISCOUNT_RATE_MAX_PCT']:.1f}% limit = {hit}"
    return (f"<div class='ins'><span class='pill' style='background:{SEV[label]}'>{label} loss risk</span>"
            f"<div class='fnd'>{detail}</div><div class='evd'>Lag features use the latest weeks in your feature store; total spend {tot:,.0f}.</div></div>")


def build():
    with gr.Blocks(theme=gr.themes.Soft(), css=CSS, title='Weekly Growth & Profit') as demo:
        gr.Markdown('# Weekly Growth & Profit')
        with gr.Tab('📊 KPI Overview'):
            kpi = gr.HTML()
        with gr.Tab('📈 Core Analysis'):
            plots = [gr.Plot() for _ in range(4)]
        with gr.Tab('📞 Domain Intel'):
            gr.Markdown('**Promo events**')
            t_promo = gr.Dataframe(interactive=False)
            gr.Markdown('**Week regimes**')
            t_seg = gr.Dataframe(interactive=False)
            gr.Markdown('**Channels**')
            t_ch = gr.Dataframe(interactive=False)
        with gr.Tab('🎯 Priority List'):
            gr.Markdown('Top 200 weeks ranked by loss-risk probability (or lowest health score if no model).')
            t_pri = gr.Dataframe(interactive=False)
        with gr.Tab('💡 Insights'):
            ins = gr.HTML()
        with gr.Tab('🖼️ Visual Gallery'):
            gal = gr.Gallery(columns=2, height='auto')
        with gr.Tab('📄 Boardroom Report'):
            board = gr.HTML()
        with gr.Tab('🔮 Forecaster'):
            gr.Markdown('Enter a planned week to see its loss-week risk.')
            with gr.Row():
                i_s = gr.Number(label='Search spend', value=5600)
                i_so = gr.Number(label='Social spend', value=4300)
                i_e = gr.Number(label='Email spend', value=1250)
                i_d = gr.Number(label='Display spend', value=2300)
            with gr.Row():
                i_p = gr.Checkbox(label='Promo week', value=False)
                i_disc = gr.Number(label='Discount rate %', value=3)
                i_w = gr.Slider(1, 52, value=26, step=1, label='Week of year')
            btn = gr.Button('Predict loss risk', variant='primary')
            out = gr.HTML()
            btn.click(forecaster, [i_s, i_so, i_e, i_d, i_p, i_disc, i_w], out)

        def load_all():
            figs = core_figs()
            a, b, c = domain_tables()
            return [kpi_html()] + figs + [a, b, c, priority_table(), insights_html(), gallery_items(), boardroom_html()]
        demo.load(load_all, None, [kpi] + plots + [t_promo, t_seg, t_ch, t_pri, ins, gal, board])
    return demo


if __name__ == '__main__':
    build().launch()

