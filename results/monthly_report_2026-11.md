# nq-research monthly report - November 2026

Paper only; nothing here is validated for real capital. Generated automatically, read-only.

## Paper tracks (change since last report)

| track | closed | open | balance | change |
|---|---|---|---|---|
| fade | 6 | 0 | 11,800 | first report |
| gap | 27 | 0 | 9,760 | first report |
| pairs | 4 | 0 | 10,296 | first report |
| volume_gap_1_2x | 5 | 0 | 10,080 | first report |
| volume_gap_1_5x | 3 | 0 | 10,240 | first report |
| volume_gap_es_1_2x | 4 | 0 | 9,800 | first report |
| volume_gap_ym_1_2x | 8 | 0 | 9,960 | first report |
| volume_gap_ym_1_5x | 6 | 0 | 10,000 | first report |

## Forward tracker (frozen daily candidates; only days after the roster start are scored)

Data through 2026-10-27, forward start 2026-11-02.

| candidate | status | days | cum net | max DD | net Sharpe |
|---|---|---|---|---|---|
| tsmom_L252_skip21_rebalM | no_forward_days_yet | - | - | - | - |
| xsmom_L21_skip0_rebalM_vf | no_forward_days_yet | - | - | - | - |
| reversal_L5_rebalW | no_forward_days_yet | - | - | - | - |
| dlt_tscarry | waiting_for_data | - | - | - | - |
| dlt_xscarry | waiting_for_data | - | - | - | - |

A Sharpe is only shown after 60 forward days, and even then a few months of data cannot separate skill from luck.

## System status snapshot

```
nq-research status  2026-11-03 06:26

TRIALS      96 of 100 used, 4 remain

PAPER ACCOUNTS (open positions / closed trades / balance)
   fade                   0 open /   6 closed / $ 11,800.00
   gap                    0 open /  27 closed / $  9,760.00
   pairs                  0 open /   4 closed / $ 10,296.00
   volume_gap_1_2x        0 open /   5 closed / $ 10,080.00
   volume_gap_1_5x        0 open /   3 closed / $ 10,240.00
   volume_gap_es_1_2x     0 open /   4 closed / $  9,800.00
   volume_gap_ym_1_2x     0 open /   8 closed / $  9,960.00
   volume_gap_ym_1_5x     0 open /   6 closed / $ 10,000.00

DECAY MONITOR  last run 2026-11-02T17:45, no flags

DATA ARCHIVES (newest file)
   NQ   2026-11-01
   ES   2026-11-01
   YM   2026-11-01
   RTY  2026-11-01

HEARTBEAT   PROBLEMS (4h ago, 27 jobs)
   - com.nqresearch.trendforward: last exit code 1
   - com.nqresearch.trendforward: error file has new Traceback/Error text (259 bytes)
BACKUP      none found in /sessions/rcw-01p3ltyq6hmyw2awzxghrzrb/Backups/nq-research

YM MINI SHADOW  8/100 forward trades, net $-476.00, PF 0.62 (too few to conclude)
LAB QUEUE   pct_gap_nq_es[registered], ym_mini_vol12[registered], dv_tsmom_L252_skip21_rebalM[registered], dlt_tscarry[queued], dlt_xscarry[queued]
```

## Reading this report
- Small samples dominate: compare tracks only at 50+ trades; the gap track's 50-trade decay check is due around early December 2026.
- Forward days are the only evidence that is free and unbiased; they accumulate whether or not anyone is looking.
