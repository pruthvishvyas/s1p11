import useKPIs from '../../hooks/useKPIs';
import EmptyState from '../shared/EmptyState';
import { fmtValue, humanize, isNum, toNum } from '../../utils/formatters';

function kindOf(k) {
  const u = String(k.unit || '').toLowerCase();
  const key = String(k.key || '').toLowerCase();
  if (/%|pct|percent/.test(u) || /margin|rate|pct/.test(key)) return 'percent';
  if (/week|day/.test(u) || /runway|dso/.test(key)) return 'number1';
  if (/^x$|ratio|\u00d7/.test(u) || /roas|ltv/.test(key)) return 'ratio';
  if (/\u20b9|inr|currency|rupee|\$/.test(u) || /revenue|profit|cac|cash|spend|receivable|ar_/.test(key)) return 'currency';
  return 'number1';
}

function warnOf(k, v, th) {
  const key = String(k.key || '').toLowerCase();
  if (v === null) return null;
  if (/ltv/.test(key) && isNum(th.LTV_CAC_MIN) && v < th.LTV_CAC_MIN) return 'Below the ' + th.LTV_CAC_MIN + ' target';
  if (/runway/.test(key) && isNum(th.CASH_FLOOR_WEEKS) && v < th.CASH_FLOOR_WEEKS) return 'Under ' + th.CASH_FLOOR_WEEKS + ' weeks of cash';
  if (/^roas/.test(key) && isNum(th.ROAS_BREAKEVEN) && v < th.ROAS_BREAKEVEN) return 'Below break-even ROAS of ' + th.ROAS_BREAKEVEN;
  if (/dso/.test(key) && isNum(th.DSO_MAX_DAYS) && v > th.DSO_MAX_DAYS) return 'Above the ' + th.DSO_MAX_DAYS + ' day limit';
  return null;
}

export default function KPICards() {
  const { kpis, thresholds, loading } = useKPIs();
  if (loading) return <div className="note">Loading...</div>;
  if (!kpis.length) return <EmptyState />;
  return (
    <div className="grid kpis">
      {kpis.map((k) => {
        const v = toNum(k.value);
        const ch = toNum(k.change_pct);
        const lowerIsBetter = /cac|dso/.test(String(k.key).toLowerCase());
        const good = ch === null ? true : lowerIsBetter ? ch <= 0 : ch >= 0;
        const warn = warnOf(k, v, thresholds);
        return (
          <div key={k.key} className={'card' + (warn ? ' kpi-warn' : '')}>
            <div className="kpi-label">{k.label || humanize(k.key)}</div>
            <div className="kpi-value">{fmtValue(kindOf(k), v)}</div>
            {ch !== null && (
              <div className={good ? 'up' : 'down'}>
                {ch >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(ch).toFixed(1)}% vs prior {k.period ? '(' + k.period + ')' : 'period'}
              </div>
            )}
            {warn && <div className="warn-text">{warn}</div>}
          </div>
        );
      })}
    </div>
  );
}
