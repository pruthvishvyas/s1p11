#!/usr/bin/env python3
# sync_data.py - re-sync ./output into <pkg>/public/data (NaN-safe), rebuild forecast_lookup.json,
# and print a schema report. Run from the folder that contains ./output and frontend_contract.json.
import os
import json
import shutil

with open("frontend_contract.json", encoding="utf-8") as _f:
    contract = json.load(_f)
PKG = contract["project"]["client_id"]
TABS = [(o, k, "", "") for o, d in contract["outcomes"].items() for k in d]


def _url(p):
    p = p.replace("\\", "/")
    if p.startswith("output/"):
        p = p[len("output/"):]
    return "/data/" + p.lstrip("/")


DATA = {k: _url(contract["outcomes"][o][k]) for o, k, _l, _c in TABS}
for _k in ("charts", "simulations"):
    if _k in DATA and not DATA[_k].endswith("/"):
        DATA[_k] += "/"

CLEANED = [0]
REV_K = ("Net_Revenue_forecast", "forecast", "net_revenue", "Net_Revenue", "predicted", "yhat", "value", "pred")
PRO_K = ("Net_Profit_forecast", "net_profit", "Net_Profit", "forecast_net_profit", "profit")
LOW_K = ("Net_Revenue_lo80", "lower", "lower_bound", "yhat_lower", "lo", "low")
UP_K = ("Net_Revenue_hi80", "upper", "upper_bound", "yhat_upper", "hi", "high")


def _clean(o):
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        CLEANED[0] += 1
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def sync_dir(src, dst):
    # Browsers reject NaN/Infinity in JSON (Python/pandas write them), which blanks every tab.
    for root, _d, files in os.walk(src):
        rel = os.path.relpath(root, src)
        out = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(out, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            t = os.path.join(out, f)
            if f.lower().endswith(".json"):
                try:
                    with open(s, encoding="utf-8-sig") as fh:
                        obj = json.load(fh)
                    with open(t, "w", encoding="utf-8") as fh:
                        json.dump(_clean(obj), fh, allow_nan=False)
                except Exception as e:
                    print("WARNING: could not parse %s: %s" % (s, e))
            else:
                shutil.copy2(s, t)


def _num(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def _first(r, keys):
    if not isinstance(r, dict):
        return None
    for k in keys:
        if _num(r.get(k)) is not None:
            return _num(r.get(k))
    return None


def _build_lookup(base):
    p = os.path.join(base, "monitor", "forecast.json")
    if not os.path.isfile(p):
        print("WARNING: monitor/forecast.json missing - no forecast lookup written")
        return
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    if isinstance(d, dict):
        fut = d.get("forecast") or d.get("future") or d.get("predictions") or []
    elif d and isinstance(d[0], dict) and "actual" in d[0]:
        fut = [r for r in d if _num(r.get("actual")) is None and _first(r, REV_K) is not None]
    else:
        fut = list(d)[-13:]
    table = {}
    for i, r in enumerate(fut[:13]):
        table[str(i + 1)] = {"net_revenue": _first(r, REV_K), "net_profit": _first(r, PRO_K),
                             "lower": _first(r, LOW_K), "upper": _first(r, UP_K),
                             "profit_lower": _first(r, ("Net_Profit_lo80",)), "profit_upper": _first(r, ("Net_Profit_hi80",)), "week_start": r.get("Week_Start")}
    if not table:
        print("WARNING: no future weeks found in forecast.json - write forecast_lookup.json by hand")
        return
    with open(os.path.join(PKG, "forecast_lookup.json"), "w", encoding="utf-8") as fh:
        json.dump(table, fh, indent=2)
    print("forecast_lookup.json written (%d weeks) -> used by npm run dev and by the Worker secret" % len(table))


def _describe(name, d):
    if isinstance(d, list):
        first = d[0] if d else None
        keys = list(first.keys()) if isinstance(first, dict) else repr(first)
        print("  %-26s list[%d] first item: %s" % (name, len(d), keys))
    elif isinstance(d, dict):
        print("  %-26s dict keys: %s" % (name, list(d.keys())[:14]))
        for k, v in list(d.items())[:14]:
            if isinstance(v, list) and v:
                print("       %-22s list[%d] first: %s" % (k, len(v), list(v[0].keys()) if isinstance(v[0], dict) else repr(v[0])))
            elif isinstance(v, dict):
                print("       %-22s dict keys: %s" % (k, list(v.keys())[:8]))
            else:
                print("       %-22s %r" % (k, v))
    else:
        print("  %-26s %s" % (name, type(d).__name__))


def _report(base):
    print("")
    print("SCHEMA REPORT (what is really in your output files):")
    for t in TABS:
        loc = os.path.join(PKG, "public", DATA[t[1]].lstrip("/"))
        if loc.endswith("/") or os.path.isdir(loc):
            for f in sorted(os.listdir(loc)) if os.path.isdir(loc) else []:
                if f.endswith(".json") and f != "index.json":
                    with open(os.path.join(loc, f), encoding="utf-8") as fh:
                        _describe(t[1] + "/" + f, json.load(fh))
        elif os.path.isfile(loc):
            with open(loc, encoding="utf-8") as fh:
                _describe(t[1], json.load(fh))
        else:
            print("  %-26s MISSING (%s)" % (t[1], loc))
    print("")


def sync_all():
    base = os.path.join(PKG, "public", "data")
    shutil.rmtree(base, ignore_errors=True)
    for sub in ("understand", "decide", "monitor", "meta"):
        src = os.path.join("output", sub)
        if os.path.isdir(src):
            sync_dir(src, os.path.join(base, sub))
        else:
            os.makedirs(os.path.join(base, sub), exist_ok=True)
            print("WARNING: %s not found - run the pipeline (main.py) first" % src)
    missing = []
    for t in TABS:
        p = contract["outcomes"][t[0]][t[1]]
        if p.endswith("/") or os.path.isdir(p):
            ok = os.path.isdir(p) and any(f.endswith(".json") for f in os.listdir(p))
        else:
            ok = os.path.isfile(p)
        if not ok:
            missing.append(p)
    if missing:
        print("WARNING: missing or empty pipeline outputs (these tabs will show 'Run main.py'):")
        for m in missing:
            print("   - " + m)
    for key in ("charts", "simulations"):
        d = os.path.join(PKG, "public", DATA[key].lstrip("/"))
        os.makedirs(d, exist_ok=True)
        names = sorted(f for f in os.listdir(d) if f.endswith(".json") and f != "index.json")
        with open(os.path.join(d, "index.json"), "w", encoding="utf-8") as fh:
            json.dump(names, fh)
    _build_lookup(base)
    print("NaN/Infinity values replaced with null: %d" % CLEANED[0])
    _report(base)


sync_all()
