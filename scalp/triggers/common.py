from __future__ import annotations
import numpy as np


def arrays(df, side):
    """Ruang 'long-like': untuk short semua harga dinegatifkan."""
    if side == "long":
        return (df["low"].to_numpy(), df["high"].to_numpy(), df["close"].to_numpy(), df["open"].to_numpy(), 1)
    return (-df["high"].to_numpy(), -df["low"].to_numpy(), -df["close"].to_numpy(), -df["open"].to_numpy(), -1)


def mk(ttype, tf, side, status, entry, entry_type, stop, level, kind, quality=None, vol_ratio=0.0, **meta):
    return {"type": ttype, "tf": tf, "side": side, "status": status, "entry": float(entry),
            "entry_type": entry_type, "stop": float(stop), "level_price": float(level), "level_kind": kind,
            "quality": quality or [], "vol_ratio": float(vol_ratio), "meta": meta}


def pick_targets(cand, levels, atr1h, cfg):
    """TP1 = level terdekat searah; TP2 = level berikutnya dengan R:R kasar >= min_rr_tp2."""
    g = cfg["g7"]; e = cand["entry"]; s = 1 if cand["side"] == "long" else -1
    risk = abs(e - cand["stop"])
    min_d = max(g["tp_min_atr_1h"] * atr1h, e * 0.001)
    buf = g["tp_buffer_pct"] / 100
    cs = sorted({round(lv["price"], 8) for lv in levels if lv["target_ok"] and s * (lv["price"] - e) > min_d},
                key=lambda p: s * p)
    cs = [p for p in cs if abs(p - e) / e * 100 <= g["tp2_max_pct"]]
    adj = lambda p: p * (1 - s * buf)
    tp1 = adj(cs[0]) if cs else None
    tp2 = None
    for p in cs[1:]:
        if s * (p - cs[0]) < min_d:
            continue
        if risk > 0 and abs(adj(p) - e) / risk >= g["min_rr_tp2"]:
            tp2 = adj(p); break
    cand["tp1"], cand["tp2"] = tp1, tp2
    return cand
