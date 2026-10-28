# Strategy discovery review 20261028-200235

**Searched 240 strategies on 2011-09 to 2019-12 only** (cumulative trials counted: 240). Validation (2020-2023) and the sealed holdout (2024+) were not read.

- Passed all filters: **50 of 240**.
- Best net Sharpe in the whole search: 0.81 (tsmom_L252_skip21_rebalM).
- Best Sharpe you would expect from 240 strategies with NO real edge: about **0.80**. Anything near or below that is indistinguishable from luck.

Filters: net Sharpe >= 0.4, positive in both halves, >= 60% of markets contribute, neighbouring parameters keep >= 50% of the Sharpe, cost drag <= 3%/yr.

## Candidates for review (ranked by discovery net Sharpe)

| # | strategy | net Sharpe | gross | half 1 | half 2 | breadth | neighbours | turnover/yr | cost/yr | max DD | DSR@N |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `tsmom_L252_skip21_rebalM` | 0.81 | 0.82 | 1.20 | 0.44 | 85% | 0.62 | 7x | 0.10% | -12% | 0.51 |
| 2 | `tsmom_L315_skip21_rebalM` | 0.66 | 0.67 | 1.01 | 0.34 | 77% | 0.96 | 7x | 0.10% | -14% | 0.33 |
| 3 | `macross_fast40_slow250_rebalM` | 0.59 | 0.60 | 0.70 | 0.48 | 69% | 0.83 | 7x | 0.10% | -12% | 0.25 |
| 4 | `xsmom_L252_skip0_rebalW` | 0.58 | 0.63 | 0.85 | 0.20 | 67% | 0.59 | 16x | 0.23% | -7% | 0.24 |
| 5 | `breakout_N250_rebalM` | 0.57 | 0.58 | 0.80 | 0.34 | 69% | 0.79 | 6x | 0.09% | -16% | 0.23 |
| 6 | `macross_fast10_slow200_rebalM` | 0.56 | 0.58 | 0.81 | 0.35 | 69% | 0.85 | 8x | 0.11% | -11% | 0.22 |
| 7 | `tsmom_L315_skip21_rebalW` | 0.55 | 0.58 | 0.71 | 0.42 | 69% | 0.70 | 13x | 0.19% | -11% | 0.22 |
| 8 | `breakout_N250_rebalW` | 0.52 | 0.54 | 0.74 | 0.31 | 69% | 0.55 | 10x | 0.14% | -15% | 0.19 |
| 9 | `macross_fast50_slow100_rebalM_vf` | 0.52 | 0.53 | 0.66 | 0.44 | 73% | 0.89 | 7x | 0.11% | -22% | 0.19 |
| 10 | `macross_fast5_slow200_rebalM` | 0.51 | 0.53 | 0.83 | 0.25 | 62% | 0.80 | 8x | 0.11% | -11% | 0.18 |

DSR@N = probability the Sharpe is real after correcting for trying N strategies; 0.95 is the project bar. Most survivors will sit well below it on discovery data alone, which is expected: this stage only chooses what is worth spending a validation trial on.

## Net return by year (top 3)

- `tsmom_L252_skip21_rebalM`: 2011: +0.6%, 2012: +6.0%, 2013: +10.6%, 2014: +17.4%, 2015: +1.5%, 2016: -1.4%, 2017: +13.5%, 2018: -1.9%, 2019: +4.2%
- `tsmom_L315_skip21_rebalM`: 2011: +1.8%, 2012: +9.6%, 2013: +0.6%, 2014: +16.1%, 2015: +3.0%, 2016: -4.1%, 2017: +13.6%, 2018: -2.6%, 2019: +3.7%
- `macross_fast40_slow250_rebalM`: 2011: +0.6%, 2012: +2.5%, 2013: -1.4%, 2014: +18.0%, 2015: -0.8%, 2016: +4.5%, 2017: +11.0%, 2018: +2.5%, 2019: -0.7%

## What happens next (your decision)
Pick at most a few candidates worth a validation trial. Each becomes a pre-registered spec tested once on 2020-2023, then (only if it passes) once on the sealed holdout. Nothing here is validated, and nothing trades.