# Laporan Backtest (60 hari)

Sinyal: 394 | Trade tertutup: 125 | Batal/expired: 269
Win rate 16.0% | Expectancy -0.549R | Total -68.65R | Max DD 71.61R | PF 0.33

## Per trigger
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| T1 | 110 | 12.7 | -0.639 | -70.28 | 70.28 |
| T2 | 15 | 40.0 | 0.109 | 1.64 | 6.54 |

## Per simbol
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| BTCUSDT | 14 | 7.1 | -0.793 | -11.1 | 11.1 |
| ETHUSDT | 57 | 12.3 | -0.697 | -39.7 | 39.86 |
| SOLUSDT | 54 | 22.2 | -0.33 | -17.84 | 22.1 |

## Per sisi
| grup | n | win% | exp(R) | total(R) | maxDD(R) |
|---|---|---|---|---|---|
| long | 36 | 11.1 | -0.7 | -25.22 | 25.22 |
| short | 89 | 18.0 | -0.488 | -43.43 | 47.44 |

## Walk-forward (per periode)
| periode | n | win% | exp(R) |
|---|---|---|---|
| 2026-09-16..2026-10-01 | 36 | 13.9 | -0.668 |
| 2026-10-01..2026-10-16 | 20 | 30.0 | -0.094 |
| 2026-10-16..2026-10-30 | 43 | 14.0 | -0.621 |
| 2026-10-30..2026-11-14 | 26 | 11.5 | -0.615 |

## Catatan
- Expectancy <= 0R setelah biaya: aturan ini belum punya edge pada data ini.
- Ada fold dengan expectancy <= 0: hasil tidak stabil antar periode.
- Parameter [C] adalah hipotesis; jangan memakai uang nyata sebelum forward-test lolos.