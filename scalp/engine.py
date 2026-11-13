"""Pipeline keputusan: Gate 0 -> 8. Murni fungsi: hanya candle tertutup, tanpa look-ahead."""
from __future__ import annotations
import pandas as pd
from . import g0_data, g1_context, g2_season, g3_regime, g4_levels, g6_confirm, g7_risk, g8_score, limits
from .indicators import atr
from .report import scenarios
from .triggers.common import pick_targets
from .triggers.t1_sweep import sweep_reclaim
from .triggers.t2_breakout import breakout_retest
from .triggers.t3_fib import pullback_fib
from .triggers.t4_flip import flips
from .util import prepare, snap


def _counter(side, season):
    return (season == "LONG_SEASON" and side == "short") or (season == "SHORT_SEASON" and side == "long")


def _gather(closed, cfg, season, levels, restr):
    T = cfg["triggers"]; price = float(closed["5m"]["close"].iloc[-1]); cands = []
    sides = {"LONG_SEASON": ["long", "short"], "SHORT_SEASON": ["short", "long"]}.get(season["season"], ["long", "short"])
    if season["no_short"]:
        sides = [s for s in sides if s != "short"]
    trs, tfs = restr.get("triggers"), restr.get("tfs")
    ok = lambda t, tf: (trs is None or t in trs) and (tfs is None or tf in tfs)
    near = [lv for lv in levels if lv["target_ok"] and lv["family"] != "EMA"
            and abs(lv["price"] - price) / price * 100 <= T["t1"]["level_window_pct"]]
    for tf in T["t1"]["tfs"]:
        if not ok("T1", tf):
            continue
        a = float(atr(closed[tf]).iloc[-1])
        for lv in near:
            for sd in sides:
                r = sweep_reclaim(closed[tf], lv["price"], sd, T["t1"], a, tf)
                if r:
                    r["level_kind"] = lv["kind"]; cands.append(r)
    for tf in T["t2"]["tfs"]:
        if not ok("T2", tf):
            continue
        a = float(atr(closed[tf]).iloc[-1])
        for lv in near:
            for sd in sides:
                r = breakout_retest(closed[tf], lv["price"], sd, T["t2"], a, tf, T["t1"])
                if r:
                    r["level_kind"] = lv["kind"]; cands.append(r)
    if season["season"] != "NEUTRAL_RANGE" and ok("T3", T["t3"]["trigger_tf"]):
        sd = "long" if season["season"] == "LONG_SEASON" else "short"
        if sd in sides:
            cands += pullback_fib(closed, sd, T["t3"])
    if season["season"] != "NEUTRAL_RANGE" and any(ok("T4", tf) for tf in T["t4"]["tfs"]):
        sd = "long" if season["season"] == "LONG_SEASON" else "short"
        if sd in sides:
            cands += [c for c in flips(closed, sd, T["t4"]) if ok("T4", c["tf"])]
    return cands


def _blank(symbol, now):
    return {"symbol": symbol, "timestamp": now.isoformat(), "decision": "NO_TRADE", "season": None, "regime": None,
            "location": {"zone": None, "pct_of_range": None}, "trigger": {"type": "NONE", "status": "PENDING"},
            "levels": {k: None for k in ("entry", "stop", "tp1", "tp2", "stop_pct", "rr_tp1", "rr_tp2")},
            "confirmations": [], "score": 0, "gates": {}, "reasons": [], "invalidated_if": [], "scenarios": [],
            "size": {"risk_pct": 0, "leverage_effective": 0}, "summary": ""}


def evaluate(symbol, frames, cfg, now, ctx=None) -> dict:
    ctx = ctx or {}; now = snap(now); out = _blank(symbol, now)
    is_major = symbol in cfg["major_symbols"]; G = out["gates"]
    closed = prepare(frames, now)
    btc_closed = None if symbol == cfg["btc_symbol"] or not ctx.get("btc_frames") else prepare(ctx["btc_frames"], now)

    def end(dec, reasons):
        out["decision"] = dec; out["reasons"] = reasons[:8]
        from .report import summary
        out["summary"] = summary(out); return out

    g0 = g0_data.check(symbol, closed, cfg, now, is_major); G["G0"] = g0["status"]
    if g0["status"] == "FAIL":
        return end("NO_TRADE", g0["reasons"])
    g1 = g1_context.check(closed, cfg, now, ctx.get("events", []), is_major); G["G1"] = g1["status"]
    if g1["status"] == "STAND_ASIDE":
        return end("NO_TRADE", g1["reasons"])
    restr = g1["restrictions"]
    se = g2_season.season(closed, cfg, now, btc_closed, symbol == cfg["btc_symbol"])
    out["season"] = se["season"]; G["G2"] = "PASS"
    rg = g3_regime.analyze(closed, cfg); out["regime"] = rg["regime"]
    levels = g4_levels.build(closed, cfg, now, rg, ctx.get("orderbook")); G["G4"] = "PASS" if levels else "FAIL"
    out["scenarios"] = scenarios(se["season"], rg, levels, closed, cfg)
    ok_lim, lim_why = limits.check(ctx.get("trades", []), now, cfg, restr.get("max_trades_per_hour"))
    atr1h = float(atr(closed["1H"]).iloc[-1])
    cands = _gather(closed, cfg, se, levels, restr)
    G["G5"] = "PASS" if any(c["status"] == "ACTIVE" for c in cands) else "FAIL"
    rejected, evald = [], []
    for c in cands:
        tag = f"{c['type']}/{c['tf']}/{c['side']}@{c['level_kind']}"
        if c["status"] == "FAILED":
            rejected.append(f"{tag}: gagal (reclaim tidak bertahan)"); continue
        counter = _counter(c["side"], se["season"])
        if counter and not (cfg["g2"]["allow_counter_trend"] and c["type"] in ("T1", "T2")):
            rejected.append(f"{tag}: melawan musim {se['season']} tanpa trigger reversal"); continue
        c["_major"] = is_major
        pick_targets(c, levels, atr1h, cfg)
        loc = g3_regime.locate(c["entry"], rg["range"], levels, cfg)
        if not loc["ok"]:
            rejected.append(f"{tag}: {loc['reason']}"); continue
        n_conf, fams = g4_levels.confluence(c["level_price"], levels, cfg)
        if restr.get("min_confluence") and n_conf < restr["min_confluence"]:
            rejected.append(f"{tag}: confluence {n_conf} < {restr['min_confluence']} (Monday)"); continue
        if restr.get("edge_only") and loc["zone"] not in ("RL", "RH"):
            rejected.append(f"{tag}: pasca-shock hanya di tepi range"); continue
        risk = g7_risk.check(c, cfg, is_major, restr, counter, cfg["account_equity"])
        if not risk["ok"]:
            rejected.append(f"{tag}: " + "; ".join(risk["reasons"])); continue
        conf = g6_confirm.confirm(c, closed, cfg, ctx, symbol, is_major, btc_closed)
        if conf["veto"]:
            rejected.append(f"{tag}: " + "; ".join(conf["notes"])); continue
        sc = g8_score.score(cfg, se, c["side"], counter, loc, n_conf, c, conf, risk, restr, g1["thin"], conf["ob_missing"])
        need = cfg["g6"]["counter_trend_min"] if counter else cfg["g6"]["min_confirmations"]
        evald.append({"c": c, "loc": loc, "risk": risk, "conf": conf, "sc": sc, "fams": fams, "counter": counter,
                      "conf_ok": len(conf["hits"]) >= need, "need": need})
    G["G3"] = "PASS" if evald else "FAIL"
    if not evald:
        why = rejected[:5] or ["tidak ada trigger T1-T4 terkonfirmasi"]
        G["G7"] = "NA"
        return end("NO_TRADE", why + g1["reasons"])
    active = [e for e in evald if e["c"]["status"] == "ACTIVE"]
    pool = active or evald
    best = max(pool, key=lambda e: e["sc"]["score"])
    c, sc = best["c"], best["sc"]["score"]
    G["G6"] = "PASS" if best["conf_ok"] else "FAIL"; G["G7"] = "PASS"; G["G8"] = f"{sc}"
    G["G1"] = g1["status"]
    reasons = list(g1["reasons"]) + se["notes"]
    if c["status"] != "ACTIVE":
        dec = "WAIT"; reasons.append(f"trigger {c['type']} belum aktif (menunggu retest/reclaim)")
    elif not best["conf_ok"]:
        dec = "WAIT"; reasons.append(f"konfirmasi {len(best['conf']['hits'])}/{best['need']} kurang")
    elif not ok_lim:
        dec = "NO_TRADE"; reasons.append(lim_why); G["G7"] = "FAIL"
    elif sc >= cfg["g8"]["trade_min"]:
        dec = "LONG_SCALP" if c["side"] == "long" else "SHORT_SCALP"
    elif sc >= cfg["g8"]["wait_min"]:
        dec = "WAIT"; reasons.append(f"skor {sc} di zona 60-74: tunggu konfirmasi/setengah ukuran")
    else:
        dec = "NO_TRADE"; reasons.append(f"skor {sc} < {cfg['g8']['wait_min']}")
    r = best["risk"]; loc = best["loc"]
    out["location"] = {"zone": loc["zone"], "pct_of_range": loc["pct_of_range"]}
    out["trigger"] = {"type": c["type"], "status": c["status"], "tf": c["tf"], "level": c["level_kind"],
                      "entry_type": c["entry_type"], "quality": c["quality"]}
    out["levels"] = {"entry": c["entry"], "stop": c["stop"], "tp1": c.get("tp1"), "tp2": c.get("tp2"),
                     "stop_pct": r["stop_pct"], "rr_tp1": r["rr_tp1"], "rr_tp2": r["rr_tp2"]}
    out["confirmations"] = best["conf"]["hits"]; out["score"] = sc; out["score_parts"] = best["sc"]["parts"]
    out["confluence"] = best["fams"]; out["counter_trend"] = best["counter"]
    out["size"] = {k: r[k] for k in ("risk_pct", "leverage_effective", "notional", "qty")}
    out["cost_pct"] = r["cost_pct"]
    out["invalidated_if"] = [f"close {'di bawah' if c['side']=='long' else 'di atas'} stop {c['stop']:.6g}",
                             "reclaim gagal (close kembali di luar level)", "time stop / bias berubah"]
    return end(dec, reasons + best["conf"]["notes"])
