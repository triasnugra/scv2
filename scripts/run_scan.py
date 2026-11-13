"""Scan live (paper). Menulis state/journal.json, site/data/*.json. Tidak ada eksekusi order."""
import json, sys, os, shutil, traceback
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scalp.config import load_config, load_events
from scalp.data import Fetcher
from scalp.engine import evaluate
from scalp.journal import make_signal
from scalp.report import stats
from scalp.sim import simulate
from scalp.util import snap
from scalp.notify import send


def resolve(journal, frames_by_symbol, cfg):
    for t in journal:
        if t["status"] not in ("PENDING", "OPEN"):
            continue
        df5 = frames_by_symbol.get(t["symbol"], {}).get("5m")
        if df5 is None:
            continue
        ts = pd.Timestamp(t["ts"])
        closed = df5[df5.index + pd.Timedelta(minutes=5) <= snap(pd.Timestamp.now(tz="UTC"))]
        bars = closed[closed.index >= ts]
        if len(bars) == 0 and ts < df5.index[0]:
            t.update(status="EXPIRED", outcome="DATA_HILANG"); continue
        t.update(simulate(t, bars, cfg))


def main():
    cfg = load_config(); events = load_events(cfg)
    state = ROOT / "state"; site = ROOT / "site" / "data"
    state.mkdir(exist_ok=True); site.mkdir(parents=True, exist_ok=True)
    jp = state / "journal.json"
    journal = json.loads(jp.read_text()) if jp.exists() else []
    f = Fetcher(cfg); now = snap(pd.Timestamp.now(tz="UTC"))
    frames, errors = {}, {}
    syms = list(dict.fromkeys([cfg["btc_symbol"]] + cfg["symbols"]))
    for s in syms:
        try:
            frames[s] = f.frames(s)
        except Exception as e:  # noqa
            errors[s] = str(e)[:200]
    resolve(journal, frames, cfg)
    decisions, new = [], []
    for s in syms:
        if s not in frames:
            decisions.append({"symbol": s, "decision": "NO_TRADE", "reasons": ["data gagal: " + errors[s]], "gates": {"G0": "FAIL"},
                              "timestamp": now.isoformat(), "summary": f"{s}: NO_TRADE (data gagal)", "score": 0})
            continue
        ctx = {"btc_frames": frames.get(cfg["btc_symbol"]), "events": events, "trades": journal, "orderbook": f.orderbook(s)}
        try:
            o = evaluate(s, frames[s], cfg, now, ctx)
        except Exception as e:  # noqa
            traceback.print_exc()
            o = {"symbol": s, "decision": "NO_TRADE", "reasons": [f"error engine: {type(e).__name__}"], "gates": {}, "score": 0,
                 "timestamp": now.isoformat(), "summary": f"{s}: error"}
        decisions.append(o)
        if o["decision"] in ("LONG_SCALP", "SHORT_SCALP"):
            sig = make_signal(o)
            busy = any(t["symbol"] == s and t["status"] in ("PENDING", "OPEN") for t in journal)
            if not busy and not any(t["id"] == sig["id"] for t in journal):
                journal.append(sig); new.append(sig)
                send(f"[SCALP {sig['side'].upper()}] {s} {sig['trigger']} entry {sig['entry']:.6g} stop {sig['stop']:.6g} "
                     f"TP1 {sig['tp1']:.6g} skor {sig['score']} (paper, bukan nasihat keuangan)")
    journal = journal[-500:]
    jp.write_text(json.dumps(journal, indent=1, default=str))
    latest = {"generated": now.isoformat(), "mode": cfg["mode"], "decisions": decisions, "stats": stats(journal),
              "new_signals": [s["id"] for s in new], "errors": errors, "disclaimer": "Analisis/paper trading. Bukan nasihat keuangan."}
    (site / "latest.json").write_text(json.dumps(latest, indent=1, default=str))
    (site / "journal.json").write_text(json.dumps(journal, indent=1, default=str))
    bt = ROOT / "state_bt" / "backtest.json"
    if bt.exists():
        shutil.copy(bt, site / "backtest.json")
    shutil.copy(ROOT / "web" / "index.html", ROOT / "site" / "index.html")
    print(f"selesai {now}: {len(decisions)} simbol, {len(new)} sinyal baru, {len(errors)} error data")


if __name__ == "__main__":
    main()
