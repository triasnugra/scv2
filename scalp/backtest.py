"""Backtest walk-forward (parameter tetap, evaluasi per-fold waktu) dengan fee+slippage.
Tanpa look-ahead: engine hanya melihat candle tertutup <= t; hasil trade disimulasikan dari bar 5m setelah t."""
from __future__ import annotations
import pandas as pd
from .engine import evaluate
from .journal import make_signal
from .report import stats
from .sim import simulate
from .util import snap


def run_symbol(symbol, frames, cfg, days, btc_frames=None, events=None, step="15min", progress=None) -> list:
    df5 = frames["5m"]; end = df5.index[-1] + pd.Timedelta(minutes=5)
    start = max(end - pd.Timedelta(days=days), df5.index[0] + pd.Timedelta(days=cfg["backtest"].get("warmup_days", 45)))
    grid = pd.date_range(start.ceil(step), end, freq=step, tz="UTC")
    trades, busy = [], None
    for t in grid:
        if busy is not None and t < busy:
            continue
        o = evaluate(symbol, frames, cfg, t, {"btc_frames": btc_frames, "events": events or [], "trades": trades})
        if o["decision"] not in ("LONG_SCALP", "SHORT_SCALP"):
            continue
        sig = make_signal(o)
        pos = df5.index.searchsorted(snap(t))
        res = simulate(sig, df5.iloc[pos:pos + 200], cfg)
        sig.update(res)
        trades.append(sig)
        busy = pd.Timestamp(res["exit_ts"]) if res.get("exit_ts") else end
        if progress:
            progress(symbol, t, len(trades))
    return trades


def _group(trades, key):
    out = {}
    for k in sorted({t[key] for t in trades if t.get("status") == "CLOSED"}):
        out[k] = stats([t for t in trades if t.get(key) == k])
    return out


def summarize(trades: list, cfg: dict) -> dict:
    closed = sorted([t for t in trades if t["status"] == "CLOSED"], key=lambda t: t["exit_ts"])
    n_fold = cfg["backtest"]["folds"]; folds = []
    if closed:
        t0, t1 = pd.Timestamp(closed[0]["exit_ts"]), pd.Timestamp(closed[-1]["exit_ts"])
        span = (t1 - t0) / n_fold if t1 > t0 else pd.Timedelta(days=1)
        for i in range(n_fold):
            a, b = t0 + span * i, t0 + span * (i + 1)
            sub = [t for t in closed if a <= pd.Timestamp(t["exit_ts"]) < b or (i == n_fold - 1 and pd.Timestamp(t["exit_ts"]) == b)]
            folds.append({"from": str(a)[:10], "to": str(b)[:10], **stats(sub)})
    allst = stats(closed); mn = cfg["backtest"]["min_trades_significance"]
    notes = []
    if allst["n"] < mn:
        notes.append(f"Sampel {allst['n']} trade < {mn}: hasil BELUM signifikan secara statistik.")
    if allst["n"] and allst["expectancy_r"] <= 0:
        notes.append("Expectancy <= 0R setelah biaya: aturan ini belum punya edge pada data ini.")
    if folds and any(f.get("n", 0) and f.get("expectancy_r", 0) <= 0 for f in folds):
        notes.append("Ada fold dengan expectancy <= 0: hasil tidak stabil antar periode.")
    notes.append("Parameter [C] adalah hipotesis; jangan memakai uang nyata sebelum forward-test lolos.")
    n_all = len(trades)
    return {"overall": allst, "by_trigger": _group(closed, "trigger"), "by_symbol": _group(closed, "symbol"),
            "by_side": _group(closed, "side"), "folds": folds, "signals": n_all,
            "cancelled_or_expired": sum(1 for t in trades if t["status"] in ("CANCELLED", "EXPIRED")),
            "notes": notes, "trades": trades[-300:]}


def to_markdown(s: dict, days: int) -> str:
    o = s["overall"]; L = [f"# Laporan Backtest ({days} hari)", ""]
    L.append(f"Sinyal: {s['signals']} | Trade tertutup: {o.get('n', 0)} | Batal/expired: {s['cancelled_or_expired']}")
    if o.get("n"):
        L.append(f"Win rate {o['win_rate']}% | Expectancy {o['expectancy_r']}R | Total {o['total_r']}R | Max DD {o['max_dd_r']}R | PF {o['profit_factor']}")
    for title, key in (("Per trigger", "by_trigger"), ("Per simbol", "by_symbol"), ("Per sisi", "by_side")):
        L += ["", f"## {title}", "| grup | n | win% | exp(R) | total(R) | maxDD(R) |", "|---|---|---|---|---|---|"]
        for k, v in s[key].items():
            L.append(f"| {k} | {v['n']} | {v['win_rate']} | {v['expectancy_r']} | {v['total_r']} | {v['max_dd_r']} |")
    L += ["", "## Walk-forward (per periode)", "| periode | n | win% | exp(R) |", "|---|---|---|---|"]
    for f in s["folds"]:
        L.append(f"| {f['from']}..{f['to']} | {f.get('n', 0)} | {f.get('win_rate', '-')} | {f.get('expectancy_r', '-')} |")
    L += ["", "## Catatan"] + [f"- {n}" for n in s["notes"]]
    return "\n".join(L)
