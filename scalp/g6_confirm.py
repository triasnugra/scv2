"""Gate 6 - konfirmasi (tidak menggantikan trigger)."""
from __future__ import annotations
import numpy as np
from .indicators import ema, obv, rsi, vol_ratio
from .structure import pivots


def _rsi_div(df, side):
    d = df.iloc[-60:]; r = rsi(d["close"]).to_numpy()
    hi, lo = pivots(d, 2)
    pts = lo if side == "long" else hi
    if len(pts) < 2:
        return False
    (i1, p1), (i2, p2) = pts[-2], pts[-1]
    return (p2 < p1 and r[i2] > r[i1] + 2) if side == "long" else (p2 > p1 and r[i2] < r[i1] - 2)


def confirm(cand, closed, cfg, ctx, symbol, is_major, btc_closed=None) -> dict:
    c = cfg["g6"]; side = cand["side"]; hits, notes, veto = [], [], False
    df = closed[cand["tf"]]
    vr = cand["vol_ratio"] or vol_ratio(df["volume"].to_numpy(), len(df) - 3, len(df) - 1)
    if vr >= c["volume_spike_mult"]:
        hits.append("volume_spike")
    ob = ctx.get("orderbook")
    if ob and c["use_orderbook"]:
        e = cand["entry"]; tol = e * c["wall_tol_pct"] / 100
        rows = ob["bids"] if side == "long" else ob["asks"]
        med = float(np.median([r[1] for r in rows])) if rows else 0
        if any(c["wall_mult"] * med <= q and abs(p - e) <= tol for p, q in rows):
            hits.append("orderbook_wall")
    else:
        notes.append("orderbook tidak tersedia")
    if symbol in cfg["obv_symbols"]:
        o = obv(closed["1D"]); up = o.iloc[-1] > ema(o, 10).iloc[-1]
        if (side == "long") == bool(up):
            hits.append("obv_1D")
    if _rsi_div(df, side):
        hits.append("rsi_divergence")
    if btc_closed is not None and symbol != cfg["btc_symbol"]:
        b = btc_closed["5m"]["close"]; n = c["btc_bars"]
        mv = (b.iloc[-1] / b.iloc[-1 - n] - 1) * 100
        sgn = 1 if side == "long" else -1
        if sgn * mv >= c["btc_align_pct"]:
            hits.append("btc_searah")
        elif sgn * mv <= -c["btc_veto_pct"]:
            veto = True; notes.append(f"BTC bergerak melawan ({mv:+.2f}%)")
    return {"hits": hits, "veto": veto, "notes": notes, "ob_missing": ob is None}
