# Strategy discovery review 20261028-201339

**Searched 240 strategies on 2011-09 to 2019-12 only** (cumulative trials counted: 480). Validation (2020-2023) and the sealed holdout (2024+) were not read.

- Passed all filters: **2 of 240**.
- Best net Sharpe in the whole search: 0.67 (tsmom_L42_skip21_rebalM_vf).
- Best Sharpe you would expect from 480 strategies with NO real edge: about **0.69**. Anything near or below that is indistinguishable from luck.

Filters: net Sharpe >= 0.4, positive in both halves, >= 60% of markets contribute, neighbouring parameters keep >= 50% of the Sharpe, cost drag <= 3%/yr.

## Candidates for review (ranked by discovery net Sharpe)

| # | strategy | net Sharpe | gross | half 1 | half 2 | breadth | neighbours | turnover/yr | cost/yr | max DD | DSR@N |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `xsmom_L21_skip0_rebalM_vf` | 0.46 | 0.52 | 0.74 | 0.09 | 68% | 0.86 | 20x | 0.31% | -8% | 0.23 |
| 2 | `reversal_L5_rebalW` | 0.43 | 0.63 | 0.14 | 0.72 | 74% | 0.74 | 59x | 0.90% | -7% | 0.20 |

DSR@N = probability the Sharpe is real after correcting for trying N strategies; 0.95 is the project bar. Most survivors will sit well below it on discovery data alone, which is expected: this stage only chooses what is worth spending a validation trial on.

## Net return by year (top 3)

- `xsmom_L21_skip0_rebalM_vf`: 2011: +10.5%, 2012: +5.2%, 2013: +0.1%, 2014: +0.5%, 2015: +5.1%, 2016: -1.8%, 2017: -1.4%, 2018: +0.1%, 2019: +3.3%
- `reversal_L5_rebalW`: 2011: -0.9%, 2012: +1.3%, 2013: -2.9%, 2014: +2.7%, 2015: +3.0%, 2016: +3.3%, 2017: +3.3%, 2018: +1.9%, 2019: +4.2%

## What happens next (your decision)
Pick at most a few candidates worth a validation trial. Each becomes a pre-registered spec tested once on 2020-2023, then (only if it passes) once on the sealed holdout. Nothing here is validated, and nothing trades.