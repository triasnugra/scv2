"""Backtest: python scripts/run_backtest.py [--days 60] [--out reports]"""
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scalp.config import load_config, load_events
from scalp.data import Fetcher
from scalp.backtest import run_symbol, summarize, to_markdown


def need(cfg, days):
    return {"5m": days * 288 + 300 + 45 * 288, "15m": days * 96 + 400, "1H": days * 24 + 600, "4H": days * 6 + 400, "1D": days + 300}


def work(args):
    symbol, cfg, days = args
    f = Fetcher(cfg); n = need(cfg, days)
    fr = f.frames(symbol, n)
    btc = fr if symbol == cfg["btc_symbol"] else f.frames(cfg["btc_symbol"], n)
    t0 = time.time()
    tr = run_symbol(symbol, fr, cfg, days, btc, load_events(cfg))
    print(f"{symbol}: {len(tr)} sinyal ({time.time()-t0:.0f}s)", flush=True)
    return tr


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int); ap.add_argument("--out", default="reports")
    ap.add_argument("--symbols", nargs="*"); a = ap.parse_args()
    cfg = load_config(); days = a.days or cfg["backtest"]["days"]
    syms = a.symbols or cfg["backtest"]["symbols"]
    with ProcessPoolExecutor(max_workers=cfg["backtest"]["workers"]) as ex:
        res = list(ex.map(work, [(s, cfg, days) for s in syms]))
    trades = sorted([t for r in res for t in r], key=lambda t: t["ts"])
    summ = summarize(trades, cfg); summ["days"] = days; summ["symbols"] = syms
    out = Path(a.out); out.mkdir(exist_ok=True)
    (out / "backtest.json").write_text(json.dumps(summ, indent=1, default=str))
    md = to_markdown(summ, days); (out / "backtest.md").write_text(md); print(md)
