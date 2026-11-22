# Laporan Backtest (60 hari)

Sinyal: 481 | Trade tertutup: 148 | Batal/expired: 332
Win rate 18.9% | Expectancy -0.508R | Total -75.23R | Max DD 77.6R | PF 0.35

## Per trigger
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| T1 | 132 | 15.9 | -0.585 | -77.24 | 79.23 |
| T2 | 16 | 43.8 | 0.126 | 2.01 | 6.54 |

## Per simbol
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| BTCUSDT | 21 | 14.3 | -0.628 | -13.19 | 16.1 |
| ETHUSDT | 64 | 17.2 | -0.611 | -39.08 | 39.08 |
| SOLUSDT | 63 | 22.2 | -0.364 | -22.96 | 24.04 |

## Per sisi
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| long | 30 | 13.3 | -0.617 | -18.51 | 18.51 |
| short | 118 | 20.3 | -0.481 | -56.71 | 59.09 |

## Walk-forward (per periode)
| periode | n | win% | exp(R) |
|---|---|---|---|
| 2026-09-23..2026-10-08 | 31 | 9.7 | -0.76 |
| 2026-10-08..2026-10-23 | 33 | 24.2 | -0.255 |
| 2026-10-23..2026-11-07 | 38 | 10.5 | -0.736 |
| 2026-11-07..2026-11-22 | 46 | 28.3 | -0.332 |

## Catatan
- Expectancy <= 0R setelah biaya: aturan ini belum punya edge pada data ini.
- Ada fold dengan expectancy <= 0: hasil tidak stabil antar periode.
- Parameter [C] adalah hipotesis; jangan memakai uang nyata sebelum forward-test lolos.