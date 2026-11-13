"""Gate 8 - skor 0-100."""
from __future__ import annotations


def score(cfg, season, side, counter, loc, n_conf, cand, conf, risk, restr, thin, ob_missing) -> dict:
    w = cfg["g8"]["weights"]; mx = cfg["g7"]
    if counter:
        tr = 0.25
    elif season["season"] == "NEUTRAL_RANGE":
        tr = 0.6
    else:
        tr = 0.7 + 0.3 * min(1, abs(season["total"]) / 6)
    z = loc["zone"]
    lo_f = 1.0 if z in ("RL", "RH", "FIB_0.75", "FIB_0.786") else 0.65 if loc["near_n"] else 0.25
    cf = min(1, n_conf / 4)
    tg = 0.5 + 0.5 * min(4, len(cand["quality"])) / 4
    cn = min(1, len(conf["hits"]) / 3)
    mx_stop = mx["max_stop_pct_major"] if cand.get("_major") else mx["max_stop_pct_alt"]
    rr = (min(1, (risk["rr_tp2"] or 0) / 4) * 10 + max(0, 1 - risk["stop_pct"] / mx_stop) * 5) / 15
    mk = 1.0 - (0.6 if restr else 0) - (0.2 if thin else 0)
    parts = {"trend": w["trend"] * tr, "location": w["location"] * lo_f, "confluence": w["confluence"] * cf,
             "trigger": w["trigger"] * tg, "confirm": w["confirm"] * cn, "rr": w["rr"] * rr, "market": w["market"] * max(0, mk)}
    total = sum(parts.values()) - (cfg["g8"]["optional_missing_penalty"] if ob_missing else 0)
    return {"score": round(max(0, min(100, total)), 1), "parts": {k: round(v, 1) for k, v in parts.items()}}
