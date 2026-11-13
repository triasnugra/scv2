import numpy as np
import pandas as pd
import pytest
from scalp.config import load_config
from scalp.engine import evaluate
from scalp import g0_data, g1_context, g3_regime, g7_risk, limits
from scalp.sim import simulate
from scalp.structure import detect_range
from scalp.triggers.t1_sweep import sweep_reclaim
from scalp.triggers.t2_breakout import breakout_retest
from scalp.util import prepare, closed_view
from .fixtures import make_5m, frames_from_5m, range_prices

CFG = load_config()
CFG["g0"]["min_quote_vol_24h"] = 0
CFG["g1"]["events_file"] = "config/none.yaml"
T1C = CFG["triggers"]["t1"]; T2C = CFG["triggers"]["t2"]


def df15(closes, highs=None, lows=None, vols=None, start="2026-03-03 00:00"):
    c = np.array(closes, float); n = len(c)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) * 1.0005 if highs is None else np.array(highs, float)
    l = np.minimum(o, c) * 0.9995 if lows is None else np.array(lows, float)
    v = np.full(n, 1000.0) if vols is None else np.array(vols, float)
    idx = pd.date_range(start, periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": v}, index=idx)


def base(n=60, price=102.0):
    return [price + (0.1 if i % 2 else -0.1) for i in range(n)]


# ---------- T1 ----------
def test_t1_long_deviation_reclaim():
    c = base(); lows = [x * 0.9995 for x in c]
    c[-2], lows[-2] = 99.9, 99.2          # spike di bawah L=100 lalu close di atas
    c[-1] = 100.3
    df = df15(c, lows=lows)
    r = sweep_reclaim(df, 100.0, "long", T1C, 0.4, "15m")
    assert r and r["status"] in ("ACTIVE", "PENDING")
    assert r["stop"] < 99.2 and r["entry"] == 100.0 and r["side"] == "long"


def test_t1_short_mirror():
    c = base(); highs = [x * 1.0005 for x in c]
    c[-2], highs[-2] = 104.1, 104.8
    c[-1] = 103.8
    df = df15(c, highs=highs)
    r = sweep_reclaim(df, 104.0, "short", T1C, 0.4, "15m")
    assert r and r["side"] == "short" and r["stop"] > 104.8


def test_t1_failed_reclaim():
    c = base(); lows = [x * 0.9995 for x in c]
    c[-3], lows[-3] = 99.9, 99.2
    c[-2] = 100.4; c[-1] = 99.7          # reclaim lalu gagal bertahan
    r = sweep_reclaim(df15(c, lows=lows), 100.0, "long", T1C, 0.4, "15m")
    assert r and r["status"] == "FAILED"


# ---------- T2 ----------
def test_t2_breakout_retest_active():
    c = base(40, 99.0) + [100.6, 100.7, 100.8, 100.5]
    v = [1000.0] * 40 + [3000, 1200, 1200, 1200]
    lows = [x * 0.9995 for x in c]; lows[-1] = 100.05
    r = breakout_retest(df15(c, lows=lows, vols=v), 100.0, "long", T2C, 0.4, "1H", T1C)
    assert r and r["type"] == "T2" and r["status"] == "ACTIVE" and r["entry_type"] == "MARKET"


def test_t2_false_breakout_becomes_t1_opposite():
    c = base(40, 99.0) + [100.6, 100.7, 99.8, 99.6]
    v = [1000.0] * 40 + [3000, 1200, 1200, 1200]
    highs = [x * 1.0005 for x in c]; highs[-3] = 101.0
    r = breakout_retest(df15(c, highs=highs, vols=v), 100.0, "long", T2C, 0.4, "1H", T1C)
    assert r and r["type"] == "T1" and r["side"] == "short" and r["meta"]["from_t2_fail"]


# ---------- G0 / G1 / G3 / G7 ----------
def test_g0_rejects_stale_and_gap():
    df5 = make_5m(range_prices(288 * 90)); fr = frames_from_5m(df5)
    now = df5.index[-1] + pd.Timedelta(minutes=5)
    assert g0_data.check("X", prepare(fr, now), CFG, now, True)["status"] == "PASS"
    stale = now + pd.Timedelta(hours=3)
    assert g0_data.check("X", prepare(fr, stale), CFG, stale, True)["status"] == "FAIL"
    gap = {k: v.drop(v.index[-20:-10]) if k == "5m" else v for k, v in fr.items()}
    assert g0_data.check("X", prepare(gap, now), CFG, now, True)["status"] == "FAIL"


def test_g1_event_and_monday():
    df5 = make_5m(range_prices(288 * 90)); fr = frames_from_5m(df5)
    wed = pd.Timestamp("2026-05-27 12:00", tz="UTC")
    ev = [{"name": "FOMC", "ts": wed + pd.Timedelta(minutes=30), "before_min": 60, "after_min": 60}]
    assert g1_context.check(prepare(fr, wed), CFG, wed, ev, True)["status"] == "STAND_ASIDE"
    mon = pd.Timestamp("2026-06-01 12:00", tz="UTC")
    r = g1_context.check(prepare(fr, mon), CFG, mon, [], True)
    assert r["status"] == "RESTRICT" and r["restrictions"]["min_confluence"] == 3


def test_g3_mid_range_no_edge():
    rng = {"rh": 104.0, "rl": 100.0, "mid": 102.0}
    assert g3_regime.locate(102.0, rng, [], CFG)["ok"] is False
    assert g3_regime.locate(100.1, rng, [], CFG)["zone"] == "RL"


def test_detect_range_found():
    df = make_5m(range_prices(288 * 10, period=96)).resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    r = detect_range(df, 72, 3, 2, 0.6, 0.8, 7.0)
    assert r and 99 < r["rl"] < 101.5 and 102.5 < r["rh"] < 105


def test_g7_stop_too_wide_and_rr():
    cand = {"side": "long", "entry": 100.0, "stop": 94.0, "tp1": 101.0, "tp2": 103.0}
    r = g7_risk.check(cand, CFG, False, {}, False, 1000)
    assert not r["ok"] and any("bukan scalp" in x for x in r["reasons"])
    cand = {"side": "long", "entry": 100.0, "stop": 99.5, "tp1": 100.6, "tp2": 101.5}
    r = g7_risk.check(cand, CFG, True, {}, False, 1000)
    assert r["rr_tp1"] < 1.0 and not r["ok"]
    cand = {"side": "long", "entry": 100.0, "stop": 99.5, "tp1": 100.9, "tp2": 102.0}
    r = g7_risk.check(cand, CFG, True, {}, False, 1000)
    assert r["ok"] and r["leverage_effective"] <= CFG["g7"]["max_leverage"]


# ---------- sim & limits ----------
def bars(ohlc):
    idx = pd.date_range("2026-03-03", periods=len(ohlc), freq="5min", tz="UTC")
    return pd.DataFrame(ohlc, columns=["open", "high", "low", "close"], index=idx).assign(volume=1.0)


SIG = {"side": "long", "entry": 100.0, "entry_type": "LIMIT", "stop": 99.0, "tp1": 101.0, "tp2": 102.0,
       "stop_pct": 1.0, "cost_pct": 0.15}


def test_sim_stop_loss_is_minus_one_r():
    r = simulate(SIG, bars([(100.5, 100.6, 99.9, 100.2), (100.2, 100.3, 98.9, 99.0)]), CFG)
    assert r["status"] == "CLOSED" and r["outcome"] == "SL" and r["r"] == pytest.approx(-1.0, abs=0.01)


def test_sim_tp1_then_breakeven_and_tp2():
    b = [(100.5, 100.6, 99.9, 100.2), (100.2, 101.2, 100.1, 101.0), (101.0, 101.1, 99.95, 100.0)]
    r = simulate(SIG, bars(b), CFG)
    assert r["outcome"] == "TP1_BE" and r["r"] > 0
    b = [(100.5, 100.6, 99.9, 100.2), (100.2, 101.2, 100.1, 101.0), (101.0, 102.3, 100.9, 102.0)]
    assert simulate(SIG, bars(b), CFG)["outcome"] == "TP2"


def test_sim_limit_not_filled_expires_and_cancels():
    far = [(100.5, 100.8, 100.4, 100.6)] * 30
    assert simulate(SIG, bars(far), CFG)["status"] == "EXPIRED"
    missed = [(100.6, 101.5, 100.5, 101.2)]
    assert simulate(SIG, bars(missed), CFG)["status"] == "CANCELLED"


def test_limits_daily_and_pause():
    now = pd.Timestamp("2026-03-03 12:00", tz="UTC")
    mk = lambda h, r: {"ts": str(now - pd.Timedelta(hours=h)), "status": "CLOSED", "r": r, "exit_ts": str(now - pd.Timedelta(hours=h - 0.5))}
    assert limits.check([mk(5, 1.0)], now, CFG)[0]
    assert not limits.check([mk(3, -1), mk(2, -1)], now, CFG)[0]            # jeda 2 loss
    assert not limits.check([mk(6, 1), mk(5, 1), mk(4, 1)], now, CFG)[0]    # 3 trade/hari


# ---------- engine ----------
def test_engine_schema_and_no_lookahead():
    n = 288 * 90
    df5 = make_5m(range_prices(n)); fr = frames_from_5m(df5)
    i = n - 700; now = df5.index[i] + pd.Timedelta(minutes=5)
    full = evaluate("SOLUSDT", fr, CFG, now)
    trunc = {tf: closed_view(d, tf, now) for tf, d in fr.items()}          # data hanya sampai `now`
    cut = evaluate("SOLUSDT", trunc, CFG, now)
    assert full["decision"] == cut["decision"] and full["levels"] == cut["levels"] and full["score"] == cut["score"]
    for k in ("symbol", "timestamp", "decision", "season", "regime", "location", "trigger", "levels",
              "confirmations", "score", "gates", "reasons", "invalidated_if", "size"):
        assert k in full
    assert full["decision"] in ("LONG_SCALP", "SHORT_SCALP", "WAIT", "NO_TRADE")


def test_engine_gate_fail_gives_no_trade_with_reason():
    df5 = make_5m(range_prices(288 * 90)); fr = frames_from_5m(df5)
    now = df5.index[-1] + pd.Timedelta(hours=5)
    o = evaluate("SOLUSDT", fr, CFG, now)
    assert o["decision"] == "NO_TRADE" and o["gates"]["G0"] == "FAIL" and o["reasons"]
