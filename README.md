# Mesin Analisis Scalping Crypto

Mesin **analisis & paper trading** (bukan auto-eksekusi, bukan nasihat keuangan) yang menerjemahkan metodologi scalping Eliz
menjadi pipeline deterministik: **Gate 0-9**, trigger **T1-T4**, semua keputusan tercatat beserta alasannya.
Scalping saja (5m/15m/1H trigger, 4H/1D konteks). Setup yang hanya masuk akal sebagai swing = `NO_TRADE`.

## Setup (sekali saja, semua via browser)
1. Upload seluruh isi folder ini ke repo (pastikan folder `.github/workflows/` ikut; bila tidak, buat file lewat *Add file > Create new file* dengan path `.github/workflows/scan.yml` dst).
2. **Settings > Pages > Build and deployment > Source: GitHub Actions.**
3. **Settings > Actions > General > Workflow permissions: Read and write.**
4. Tab **Actions**: jalankan **Tests** (harus hijau), lalu **Scan & Deploy** (Run workflow). Dashboard muncul di `https://<user>.github.io/<repo>/`.
5. Jalankan **Backtest** (Run workflow, `days` 60) untuk laporan; hasil tampil di dashboard pada scan berikutnya.
6. (Opsional) Secret `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` untuk notifikasi sinyal baru.

Catatan: cron GitHub *best-effort* (bisa telat), cocok untuk snapshot/alert tiap beberapa menit, **bukan eksekusi latensi rendah**.
Repo privat: ganti cron `*/5` jadi `*/15` agar tidak menghabiskan menit gratis. State disimpan di branch `data` (1 commit, di-overwrite), backtest di branch `backtest`.

## Struktur
```
config/config.yaml   semua parameter, bertanda [E] (aturan Eliz) / [C] (hipotesis)
config/events.yaml   event high-impact (ISI & verifikasi sendiri; weekly/monthly close otomatis)
scalp/g0_data.py ... g8_score.py   satu modul per gate
scalp/triggers/      t1_sweep, t2_breakout, t3_fib, t4_flip
scalp/engine.py      pipeline; sim.py simulator; backtest.py; limits.py batas harian
scripts/run_scan.py  scan live + jurnal paper;  scripts/run_backtest.py
tests/               tes per gate/trigger, simulator, anti look-ahead
```
Jalankan lokal (opsional): `pip install -r requirements.txt && pytest -q`.

## Output
Per simbol: ringkasan (<=5 baris), skenario bersyarat (maks 2), dan JSON (`site/data/latest.json`) berformat sesuai spesifikasi
(+ `score_parts`, `confluence`, `size.notional/qty`). Keputusan: `LONG_SCALP | SHORT_SCALP | WAIT | NO_TRADE`.
Skor >=75 TRADE, 60-74 WAIT, <60 NO_TRADE; gate keras (0-3, 7) selalu mengalahkan skor.

## Asumsi & batasan (jujur)
- Data: kline spot publik (Binance vision -> Binance -> OKX -> Bybit). Futures/funding/OI tidak dipakai.
- Heatmap likuidasi tidak ada sumber gratis: tidak diimplementasi. Order book (dinding) opsional; bila gagal skor dikurangi 3, bukan error.
- "TOTAL market cap" tidak tersedia: altcoin mengikuti musim BTC (BTC berlawanan => NEUTRAL_RANGE).
- Event FOMC/CPI harus kamu isi di `events.yaml`; contoh FOMC 9 Des 2026 perlu diverifikasi.
- Simulator konservatif: stop dicek lebih dulu dalam satu bar; biaya (fee+slippage+spread) masuk R:R; limit order kedaluwarsa 2 jam.
- Backtest: parameter tetap, dilaporkan per periode (walk-forward), batas harian per simbol. Sampel <100 trade = belum signifikan.
- Semua parameter [C] adalah **hipotesis**. Jangan pakai uang nyata sebelum backtest + forward-test (paper) membuktikan expectancy > 0 setelah biaya.
