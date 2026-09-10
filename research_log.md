# NQ Research Platform — Decision Log

This log documents every strategy hypothesis tested, the method used, the result, and the final verdict. Entries are added chronologically as new ideas are tested.

---

## Format for each entry:
- **Hypothesis:**
- **Method:**
- **Sample:**
- **Result:**
- **Verdict:**
- **Reasoning:**

---

## Entry 1: Prior Day High/Low Breakout
- **Hypothesis:** Price closing beyond the prior day's high/low at 8:30 AM signals continuation in that direction.
- **Method:** Fixed stop/target (30/60 pts), tested on 15-min NQ data.
- **Sample:** 18 trades (initial), later 224 trades on extended archive; 175 trades on hourly data.
- **Result:** Small positive edge at scale (PF 1.07), but negative after realistic slippage/commission.
- **Verdict:** FAIL (thin edge destroyed by costs)
- **Reasoning:** Edge too small to survive real trading friction.

## Entry 2: Prior Day Fade (reversal)
- **Hypothesis:** Opposite of breakout — fade the break, betting on reversal.
- **Method:** Same structure as breakout, opposite direction.
- **Sample:** 20 trades initially (promising), 32 trades on extended archive.
- **Result:** Reversed from positive to negative as sample grew (0/5 scorecard at scale).
- **Verdict:** FAIL
- **Reasoning:** Small-sample illusion — did not hold up as more data accumulated.

## Entry 3: Overnight Range Break
- **Hypothesis:** Break of the overnight (6PM-8:30AM) range signals continuation.
- **Sample:** 9 trades.
- **Result:** Inconclusive, leaning negative.
- **Verdict:** FAIL (small sample, weak signal)

## Entry 4: ATR-Scaled Breakout/Fade
- **Hypothesis:** Volatility-scaled stops improve on fixed-point stops.
- **Sample:** Various multipliers, 14-18 trades each.
- **Result:** Mostly overfit noise; one ATR-fade combo (0.30x/0.60x) held up out-of-sample on a small sample.
- **Verdict:** FAIL (majority), WATCH (single combo, insufficient data)

## Entry 5: Opening Range Breakout (ORB)
- **Hypothesis:** Breakout of the first 30-min range after open signals continuation.
- **Sample:** 51 trades.
- **Result:** Consistently negative across all stop/target combos tested.
- **Verdict:** FAIL

## Entry 6: Trend Following (5-day MA)
- **Hypothesis:** Multi-day trend-following using a 5-day moving average filter.
- **Sample:** 28-29 trades (small archive), 823 days extended archive.
- **Result:** Walk-forward showed front-loaded performance (great in one early window, weak/negative later). Regime filter made results worse, not better.
- **Verdict:** FAIL (regime-dependent, not durable)

## Entry 7: VWAP Mean-Reversion
- **Hypothesis:** Price reverts to VWAP after stretching unusually far from it.
- **Sample:** 723 trades (largest single-strategy sample).
- **Result:** PF 0.80, large drawdown, decisively negative.
- **Verdict:** FAIL (large sample, clean rejection)

## Entry 8: Volatility Squeeze + Breakout
- **Hypothesis:** Low-volatility compression precedes a directional breakout.
- **Sample:** 43 trades.
- **Result:** 23.3% win rate, clean rejection.
- **Verdict:** FAIL

## Entry 9: NQ/ES Pairs Trading (Mean Reversion)
- **Hypothesis:** NQ/ES price ratio reverts to its rolling mean when stretched beyond 2 std deviations.
- **Sample:** 39 trades (extended archive, 2024-2026).
- **Result:** PF 2.52, out-of-sample expectancy improved vs in-sample, survives cost sensitivity, survivable drawdown at micro sizing.
- **Verdict:** PASS (4/5 scorecard) — pending 100-trade threshold
- **Reasoning:** Strongest, most consistent result to date at time of testing.

## Entry 10: Gap Continuation
- **Hypothesis:** NQ's overnight gap at the open tends to continue rather than fill.
- **Sample:** 70 trades (extended archive).
- **Result:** 67.1% win rate, PF 2.57, perfect 5/5 walk-forward, survives micro-sizing and cost sensitivity.
- **Verdict:** PASS (4/5 scorecard) — pending 100-trade threshold
- **Reasoning:** Best single result of the project. Now forward-testing live.
- **CORRECTION (2026-09-09): see Entry 16.** `get_gap_signals_from_archive()`'s "open" is the
  first bar of the calendar date, not the 08:30 RTH open. For Sunday, the first bar is the 6PM
  Globex reopen — so this "gap" is the Friday-close-to-Sunday-reopen weekend gap, not an
  intraday open-bell gap. Investigation found that 68 of these 70 trades are Sundays (the other
  2 are holiday-adjacent anomalies), and **all 70 exit via "eod"** — the stop_points/target_points
  never actually get checked against any bar, because a Sunday date has no 08:30–16:00 RTH bars
  at all. This PF 2.57 / 67.1% result is real, but it describes a weekly Sunday-reopen-momentum
  effect, not the strategy that `gap_forward_check.py` has actually been forward-testing live
  since it fires on ANY weekday's 08:30 gap. That strategy had never been backtested until Entry
  16. Treat this entry's numbers as validating a different, untested-live effect, not the live
  gap strategy.

## Entry 11: Day-of-Week Effect (Wednesday-Long)
- **Hypothesis:** NQ shows a statistically distinct positive drift on Wednesdays (and Mondays).
- **Sample:** 139 trades — largest clean directional sample tested.
- **Result:** Passes sample size and profit factor (1.56) cleanly. Fails drawdown (33.2%) even at micro sizing. Every stop-loss size tested made performance worse, not better.
- **Verdict:** FAIL (real signal, not tradeable at acceptable risk)
- **Reasoning:** Statistically real pattern that does not translate into a viable risk-managed strategy.

## Entry 12: Cross-Market Lead-Lag (NQ/ES, 15-min)
- **Hypothesis:** ES's recent move predicts NQ's next move (or vice versa) at short timeframes.
- **Sample:** 3,101-7,057 trades across multiple lookback/hold variations.
- **Result:** ~49-51% win rate across every variation tested — no exploitable relationship.
- **Verdict:** FAIL (large sample, decisive rejection)

## Entry 13: NQ/YM and ES/YM Pairs Trading
- **Hypothesis:** Extension of Entry 9's logic to other large-cap index pairs.
- **Sample:** 37-38 trades each.
- **Result:** Both show 70-80% win rates, PF 1.97-2.25, out-of-sample results improved (not collapsed).
- **Verdict:** PASS (pending 100-trade threshold)
- **Reasoning:** Confirms Entry 9's edge generalizes across large-cap index correlations, not specific to one pair.

## Entry 14: RTY-Based Pairs (NQ/RTY, ES/RTY, YM/RTY)
- **Hypothesis:** Same mean-reversion logic extends to small-cap (Russell 2000) pairings.
- **Sample:** 30-31 trades each.
- **Result:** All three collapsed out-of-sample (positive in-sample, negative out-of-sample).
- **Verdict:** FAIL
- **Reasoning:** Valuable negative result — confirms the pairs edge is specific to large-cap correlation structure, not a universal "any two futures revert" effect. Strengthens confidence in Entries 9 and 13.

## Entry 15: Overnight-to-NY Session Reversion
- **Hypothesis:** Large overnight moves partially reverse during the NY session.
- **Sample:** 459 trades (diagnostic showed real directional tendency; converted to tradeable rule with 40/60 stop-target).
- **Result:** Diagnostic showed genuine reversal tendency (44.8% continuation on largest moves). As a tradeable strategy: PF 0.81, out-of-sample worse than in-sample.
- **Verdict:** FAIL
- **Reasoning:** Real statistical pattern did not survive conversion into a fixed stop/target trading rule — same failure mode as Entry 11.

## Entry 16: Gap Continuation, Corrected for the Definition Actually Live (`get_weekday_open_gap_signals_from_archive`)
- **Hypothesis:** Same as Entry 10, but using the gap definition `gap_forward_check.py` (the live
  script) actually uses: the entry-time bar's Open vs. the prior trading day's close, restricted
  to days that actually have an entry-time bar (which excludes Sunday by construction, unlike
  Entry 10's method).
- **Method:** MNQ sizing ($2/pt), 40/60/80-pt-style stop/target unchanged from Entry 10, full
  scorecard + 4-window walk-forward + cost sensitivity, same thresholds as every other entry.
- **Sample:** 468 trades (extended archive, all five weekdays represented ~86-98 each — no
  Sunday bias, confirming the fix). Exit reasons: 287 stop, 173 target, 8 eod — a real spread of
  outcomes, unlike Entry 10's 70-for-70 eod.
- **Result:** 38.5% win rate, PF 1.22, expectancy $10.98/trade gross ($4.48/trade after 1pt
  slippage + $4.50 commission) at MNQ sizing. Max drawdown $1,280 (12.8% of a $10k account) —
  comfortably survivable. Out-of-sample expectancy ($25.09) *improved* over in-sample ($4.90),
  a good sign against overfitting. Walk-forward across 4 windows: PF 0.96 (negative, -$2.36/trade)
  → 1.19 → 1.27 → 1.54 — 3 of 4 windows profitable, with a visible improving trend, not flat
  consistency.
- **Verdict:** WATCH (4/5 scorecard — passes sample size, drawdown, OOS sample size, OOS
  expectancy; fails only profit factor, 1.22 vs. the 1.3 bar, a close miss)
- **Reasoning:** This is the strategy that has actually been forward-testing live this whole
  time, and until now it had never been backtested at all — Entry 10 tested something else (a
  weekly Sunday-reopen effect). The real picture is more modest than Entry 10 suggested but not
  bad: a much larger sample (468 vs. 70), genuine stop/target usage, manageable drawdown, and an
  improving trend across time. Worth continued live tracking toward the 100-trade live-forward
  threshold using *this* definition as the benchmark, not Entry 10's numbers.

## Entry 17: Overnight Session Drift (unconditional, no filter)
- **Hypothesis:** NQ's overnight session (prior regular-session close → next day's regular-session
  open) has a structurally positive drift on its own, with no gap-size filter or other condition —
  distinct from Entry 10/16 (which trade *after* the open) and Entry 15 (which only fires on
  unusually large overnight moves and bets on partial reversal).
- **Method:** `get_overnight_drift_signals_from_archive()`, unconditional LONG every session, full
  scorecard + 4-window walk-forward + cost sensitivity, NQ point value for comparability.
- **Sample:** 525 overnight sessions (extended archive).
- **Result:** 56.4% win rate, PF 1.16, expectancy $161.64/session gross, barely dented by
  realistic costs (still $137.14/session at max commission+slippage tested). **4 of 4 walk-forward
  windows profitable** — genuinely consistent, not a lucky stretch. But max drawdown is $64,535
  (645% of a $10k account), because this version carries **no stop-loss** — it's a naked,
  unlimited-risk overnight hold.
- **Verdict:** WATCH (3/5 scorecard — passes sample size, OOS sample size, OOS expectancy; fails
  profit factor and drawdown)
- **Reasoning:** Same failure shape as Entry 11 (Wednesday effect): a real, cost-resistant,
  time-consistent edge that isn't risk-manageable as currently structured. Unlike Entry 11 (where
  every stop size tried made it worse), this hasn't been tested with a stop-loss yet — worth one
  more pass adding a max-adverse-move stop to the overnight hold before a final verdict, rather
  than assuming it's doomed.

## Entry 18: Cointegration Check on Live Pairs (NQ/ES, NQ/YM, ES/YM)
- **Hypothesis:** If the pairs relationships behind Entries 9 and 13 are a genuine long-run
  equilibrium (not just a rolling z-score that looks mean-reverting by construction on almost any
  two series), an Engle-Granger cointegration test should reject the null of no cointegration.
- **Method:** `check_cointegration()` (statsmodels `coint`), log daily closes, in-sample only
  (first 70% of overlapping history) to avoid look-ahead. Also run on the RTY pairs already
  rejected in Entry 14, as a confirmatory check.
- **Sample:** 583-584 in-sample days per pair.
- **Result:** None of the three live pairs are cointegrated at 5% significance: NQ/ES p=0.26,
  NQ/YM p=0.11, ES/YM p=0.06 (closest to significant). The rejected RTY pairs also aren't
  cointegrated (p=0.25-0.38) but aren't meaningfully weaker than the Tier-1 pairs either — so
  this test does *not* cleanly confirm Entry 14's "large-cap correlation structure" explanation.
- **Verdict:** CAUTION (not a kill signal for Entries 9/13, but a real reason for humility)
- **Reasoning:** The live and backtested pairs results are real and shouldn't be discarded on
  this alone, but there's no independent statistical confirmation that the underlying
  relationship is a durable equilibrium rather than a rolling-window artifact. Argues for smaller
  size and a faster kill-switch on the pairs trades rather than treating PF 2.0+ as proof of a
  permanent structural edge.

## Entry 19: Relative Momentum Rotation (NQ / ES / YM / RTY)
- **Hypothesis:** A genuinely different mechanism from the pairs book — instead of betting two
  correlated indices mean-revert together (weakened by Entry 18's cointegration result), rank all
  four index futures daily by trailing return and go long whichever is leading, betting momentum
  persists for that session. Long-only by design, so it carries real equity-index beta as a known
  confound.
- **Method:** `get_relative_momentum_rotation_signals_from_archive()` — trailing return computed
  only through the prior close (no lookahead), long the leader's RTH session. Swept
  `lookback_days` in [3, 5, 10, 20] and, on the 5-day case, a `min_lead` margin requiring the
  leader to be ahead of the runner-up by [0, 0.25, 0.5, 1.0] percentage points.
- **Sample:** 630-647 trades depending on lookback.
- **Result:** PF 0.90-1.00 across every lookback tested — never profitable. On the 5-day base
  case, walk-forward was 0/4 windows profitable, and out-of-sample expectancy was negative.
  Requiring a bigger momentum margin made results monotonically **worse** (PF 0.94 → 0.83 → 0.77
  → 0.80 as min_lead rose from 0 to 1.0pp) — mild evidence pointing the opposite direction from
  the hypothesis, not just noise.
- **Verdict:** FAIL (2/5 scorecard)
- **Reasoning:** No evidence this data supports single-day momentum persistence across these four
  indices. The clean, monotonic degradation under a stricter margin filter is a genuine (if mild)
  signal that leadership doesn't predict continuation here — not worth building a market-neutral
  long/short variant of this specific construction.

## Entry 20: Overnight Drift + Stop-Loss, Weekday Breakdown (and the Wednesday outlier investigation)
- **Hypothesis:** Entry 17's overnight drift needs a real stop to be viable at all. Separately,
  worth checking whether its aggregate edge concentrates on specific weekdays, given Entry 14's
  independently-discovered Wednesday RTH effect.
- **Method:** `get_overnight_drift_signals_with_stop_from_archive()` — bar-by-bar stop-loss
  checked across the actual overnight session (not just entry vs. exit price). Swept stop_points
  in [50, 75, 100, 150]; picked 100pt (matching the existing `get_day_of_week_stop_signals_from_archive`
  convention, not the best-looking sweep result) and split the result by exit weekday.
- **Sample:** 525 overnight sessions (2024-2026), 137 of them Wednesday.
- **Result (all weekdays combined, the un-cherry-picked base case):** PF 1.13, expectancy
  $11.21/trade gross ($4.71 net of realistic costs), 3/4 walk-forward windows profitable, but max
  drawdown $3,824 (38.2% of a $10k account) — **fails the drawdown bar**. Median trade is actually
  -$22 (loses more often than it wins) — the entire edge is carried by a small number of large
  winners: the top 5 trades account for 92.2% of total P&L, the top 20 for 260.5% (trades outside
  the top 20, taken together, lose money).
- **Result (Wednesday-only, the best of the 5 weekdays tested):** Technically passes 5/5 on the
  scorecard (PF 1.46, 13% drawdown, positive OOS) — but the single largest trade in the whole
  dataset (798.5 pts / $1,597, 32% of this subset's total P&L) turned out to be the 2026-04-08
  overnight session. Traced bar-by-bar in the raw archive and confirmed via web search: this was
  the US-Iran ceasefire / Strait of Hormuz reopening announcement (evening of 2026-04-07), a real,
  well-documented, one-off geopolitical event (Nasdaq cash closed +2.80% the next day, matching
  this move) — not a data error, but also not a "Wednesday" phenomenon. That kind of event could
  land on any weekday; it falling in this bucket looks incidental. With that one trade excluded,
  the Wednesday subset (n=136) still shows PF 1.31, expectancy $24.82/trade gross, and a low 13%
  drawdown — a genuinely encouraging *residual* result even without the outlier. But this is still
  the best-performing of 5 weekday buckets tested, so a real multiple-comparisons concern remains
  either way.
- **Verdict:** All-weekdays combined = WATCH (3/5, fails profit factor and drawdown). Wednesday
  subset = CAUTION / promising hypothesis, not yet validated — corroborates Entry 14's
  independent Wednesday finding, but needs real forward-testing time, not further historical
  re-slicing, before it means anything more than that.
- **Reasoning:** A smaller-scale echo of the Entry 10 lesson: an exciting aggregate number was
  partly manufactured by one rare, real event landing in a favorable bucket, not by a broad
  repeatable pattern. Next step is forward-testing the 100pt-stop overnight hold in real time
  (watching the Tuesday-close-to-Wednesday-open window in particular), not mining this same
  history further for a cleaner cut.

## Entry 21: Gap Continuation, Volatility-Regime Filter (follow-up to Entry 16)
- **Hypothesis:** Entry 16's corrected gap-continuation edge (468 trades, PF 1.22, just under the
  1.3 bar) is a momentum/persistence effect that should be stronger in higher-volatility regimes.
  Tested by splitting the SAME 468 trades (identical stop/target, no re-fit) by entry-day ATR
  percentile rank against the trailing 60 sessions.
- **Method:** `get_weekday_open_gap_signals_with_vol_regime_from_archive()` — RTH session true
  range → rolling ATR (lagged 1 day, no lookahead) → rolling percentile rank. Split at the median
  and into terciles. Three follow-up checks run on the high-vol (>=median) subset specifically,
  given the Entry 10/Entry 20 lesson that an exciting aggregate number needs to survive scrutiny
  before it means anything:
  1. **Outlier concentration** — does this filter's edge depend on a few huge trades?
  2. **Confound check** — does the LOW-vol subset show the same "improves over time" walk-forward
     shape as the high-vol subset? If so, the filter isn't adding real information beyond a
     generic calendar-time trend already present in Entry 16's unfiltered walk-forward
     (0.96→1.19→1.27→1.54).
  3. **Cost sensitivity** — the standardized scorecard has NO cost check built in; verified
     separately using `trading_costs.apply_costs()`.
- **Sample:** 452 usable trades (16 dropped for insufficient ATR warmup), split 186 low-vol / 266
  high-vol.
- **Result:** High-vol subset: PF 1.32 gross, expectancy $15.27/trade gross, 5/5 scorecard PASS
  on paper. But:
  1. **Outlier check: clean.** Top 10 winning trades are only 39.4% of total P&L, median trade is
     a normal -$80 stop-out (matches the 39.8% win rate on a 2:1 reward:risk setup). Unlike Entry
     20's Wednesday result, this strategy's fixed 40pt stop/80pt target structurally prevents any
     single trade from dominating - confirmed empirically, not just assumed.
  2. **Confound check: the filter passed.** Low-vol's own walk-forward is 1.23→1.41→0.80→1.10 -
     NOT a steady climb like the unfiltered baseline or the high-vol subset. It craters (PF 0.80,
     -$105/trade) in the exact window (2025-06-25 to 2026-01-02) where the high-vol subset was
     having its best run. If this were purely a calendar-time effect, both subsets would move
     together: they diverge instead, which is real evidence the volatility split is capturing
     something distinct from "the strategy just got better over time."
  3. **Cost check: fails the bar.** Net of realistic slippage+commission, PF drops from 1.32 to
     **1.17** - below the 1.3 threshold. Net expectancy $8.77/trade - a real improvement over
     Entry 16's unfiltered baseline (~$4.48/trade net) but not enough to clear the scorecard on a
     cost-adjusted basis. The scorecard's "5/5 PASS" is gross-only and would have overstated this.
  4. Walk-forward itself is officially "3/4 windows, mixed/inconclusive" per its own summary text
     (window 1 lost money, PF 0.92) - worth noting the scorecard's headline PASS/FAIL line and the
     walk-forward's own consistency verdict can disagree, and both need to be read, not just the
     scorecard.
- **Verdict:** WATCH, upgraded confidence - a credible, evidence-backed refinement to Entry 16
  (not a confound artifact, not outlier-dependent), but still short of the profit-factor bar once
  real costs are applied. Roughly doubles net expectancy per trade vs. the unfiltered baseline.
- **Reasoning:** This is the most defensible incremental improvement found in today's research
  push - it survived exactly the kind of scrutiny that sank Entry 20's Wednesday result. Worth
  adopting as the working definition of the gap-continuation edge going forward (trade the
  high-vol-regime subset preferentially), but "worth adopting as the better definition" is not the
  same as "validated" - it still needs the 1.3 net-of-cost profit factor bar cleared, likely via
  more accumulated live data, before it's more than a well-supported refinement.

## Entry 22: Crude Oil Gap Continuation (independent-asset-class candidate) — outlier-dependency check
- **Hypothesis:** Crude oil's daily open-gap continuation, as a second, genuinely independent
  (different asset class) strategy candidate alongside the NQ/ES/YM/RTY book. 26 years of daily
  history (2000-2026, 6539 bars), no fixed stop/target (enter at open, exit at close, daily-only
  resolution).
- **Method:** `get_crude_oil_gap_signals_from_history()` — swept continuation/reversion x 1%/2%/3%
  gap thresholds. On first run, the standardized scorecard's new cost check (Entry 21's fix)
  immediately caught that `trading_costs.py`'s default slippage (1.0 points = $1.00/barrel) is
  calibrated for equity-index tick size and wildly wrong for crude's penny-tick structure — same
  category of bug as an earlier MNQ/NQ point-value mixup. Re-ran with corrected MCL cost
  assumptions (0.02 pts / 2 ticks slippage, $3 commission, both flagged as estimates, not the
  user's real broker fees). The (continuation, 3%) cut passed 6/6 on the corrected scorecard, with
  positive profit factor across all three multi-decade eras tested (2000-2008 PF 1.23, 2009-2019
  PF 3.57, 2020-2026 PF 1.52). Given the Entry 20 lesson — a clean-looking, no-fixed-stop result
  that turned out to hinge on one trade — ran the same outlier-concentration check here before
  accepting the result: top-N-winning-trades as % of total P&L, largest trades identified by date,
  and `full_stats` recomputed with the top 1 and top 3 trades excluded.
- **Sample:** 108 trades.
- **Result:** FAILS the outlier check, decisively — worse than Entry 20's case.
  - Top 1 trade = 55.9% of total P&L ($2,401 of $4,298 total). That trade is **2020-04-21** — the
    day immediately after the May 2020 WTI contract settled at -$37.63, the first-ever negative
    settlement in crude oil history (a contract-expiry/forced-liquidation event, not a normal gap).
    The function's existing data-quality carve-out (`prior_close.abs() > 1.0`) was written to
    exclude the literal negative-price rows, but doesn't catch this one: the *prior* close
    (-37.63) has `abs() > 1.0`, so the carve-out only removes exact zero-crossing rows, not the
    surrounding contract-roll chaos.
  - Top 3 trades = 102.8% of total P&L — meaning the other 105 trades combined are net *negative*.
  - Excluding just the single largest trade: profit factor 1.25, expectancy $17.73/trade.
  - Excluding the top 3 trades: profit factor 0.98, expectancy **-$1.16/trade**, total P&L
    **-$122** across the remaining 105 trades. The edge disappears entirely.
- **Verdict:** FAIL — outlier-dependent, not a real edge.
- **Reasoning:** Same failure mode as Entry 20's Wednesday result, but more extreme: 3 trades out
  of 108 (2.8% of the sample) account for more than the *entire* total P&L, and the single largest
  trade is the direct product of a once-in-history negative-price/contract-roll anomaly, not a
  repeatable continuation mechanism. The "positive in every era" framing from the initial pass was
  misleading — the 2020-2026 era's result was substantially this one trade. Crude oil daily-gap
  continuation at these thresholds is not validated. No further work planned on this exact
  formulation without a fixed stop/target, which (per Entry 21) would structurally cap this kind
  of single-trade domination rather than merely avoiding it by luck. General lesson for any future
  daily-frequency crude oil work: data-quality carve-outs around the April 2020 negative-price
  event need to consider the surrounding days, not just the exact anomalous rows.

## Entry 23: Pairs Book (NQ/ES, NQ/YM, ES/YM) Re-Validated: Micro Sizing, Real 2-Leg Costs, Outlier Check
- **Hypothesis/purpose:** Entries 9 and 13's original "PASS" verdicts came from `pairs_scorecard.py`,
  a hand-rolled, one-off scorecard that reimplements 5 of the 6 standard checks directly on the
  `pnl_dollars` column - it never called `scorecard.py` at all, so those verdicts predate AND
  bypass the Check 6 cost-adjustment fix (Entry 21). The pairs book has never actually been judged
  against realistic 2-leg trading costs, nor checked for outlier concentration the way every other
  strategy this month has been.
- **Method:** `pairs_scorecard_v2.py` (new) re-runs all three pairs at MICRO sizing (MNQ/MES/MYM -
  exactly 1/10th of the full-size dollar P&L `get_pairs_trading_signals_from_archive()` /
  `get_generic_pairs_signals_from_archive()` produce, matching this project's micro-first
  convention) through the real `scorecard.run_scorecard()`, using a 2-LEG cost model (both legs'
  slippage + both legs' commission, since a pairs trade is really two simultaneous trades) built
  from this project's existing 1.0pt-slippage/$4.50-commission convention applied per-leg at each
  leg's own micro point value: NQ/ES = $16.00/trade, NQ/YM = $11.50/trade, ES/YM = $14.50/trade
  round-trip (estimates, not verified against real broker fills for a 2-leg spread order).
  Building this also surfaced and fixed a real bug in `walk_forward.py`: it silently ignored
  whatever `point_value` a caller passed and always used the NQ default (20) internally for its
  window-by-window dollar figures - harmless for point_value=20 callers, but would have silently
  under/over-stated every window's dollars for point_value=1 signal sets (Relative Momentum
  Rotation, and now pairs). Fixed by adding a real `point_value` parameter (default 20, backward
  compatible). Entry 19's FAIL verdict is unaffected (sign of each window's profitability doesn't
  change under uniform rescaling).
  NQ/YM's walk-forward output showed a window with profit factor 107.53 (avg loss only -$23.79 vs
  avg win $730.96, in 9 trades) - the same lopsided shape that turned out to be the whole story
  for Entry 20's Wednesday result and Entry 22's crude oil result. Built `pairs_outlier_check.py`
  to check top-1/3/5-winning-trade concentration and re-computed stats with the top 1 and top 3
  trades excluded, on all three pairs (not just NQ/YM), to avoid missing a quieter version of the
  same problem in the other two.
- **Sample:** 39 trades (NQ/ES), 37 (NQ/YM), 38 (ES/YM).
- **Result:** All three clear the outlier-concentration bar cleanly - a real difference from the
  two rejected results this month:
  - NQ/ES: top 3 trades = 46.7% of total P&L; excluding them, PF 2.16 → 1.81, still comfortably
    above 1.3. 4/4 walk-forward windows profitable, no wild window-to-window swings.
  - NQ/YM: top 3 trades = 40.0% of total P&L; excluding them, PF drops to 1.75, still solidly
    above 1.3. The suspicious window-3 result turns out NOT to be one dominant trade - it's a
    window where the LOSERS happened to be unusually small (avg loss -$23.79), while the top 3
    trades overall are spread across three different dates, none of which single-handedly define
    the result. Real, if worth continued monitoring for whether that loss-size pattern repeats.
  - ES/YM: top 3 trades = 46.1% of total P&L; excluding them, PF drops furthest of the three (1.97
    gross → 1.52), the thinnest remaining margin above the 1.3 bar, though still a PASS.
  Cost-adjusted (net) profit factors at micro sizing: NQ/ES 2.33, NQ/YM 2.19, ES/YM 1.76 - all
  clear 1.3 with room, even before removing any outliers. All three: 4/6 on the standardized
  scorecard, failing only sample size (37-39 vs. 100) and out-of-sample sample size (12 vs. 20) -
  both pure function-of-time gates, not evidence against the edge.
- **Verdict:** WATCH (upgraded confidence) for all three - genuinely stress-tested now (cost model,
  outlier concentration) and still standing, unlike Entries 20 and 22. Not yet PASS: still gated
  by the 100-trade / 20-trade-OOS thresholds, and Entry 18's cointegration caution (none of the
  three show formal statistical cointegration) still applies as a standing caveat on *why* this
  works, even though *whether* it currently works now has better evidence behind it than before
  this entry. ES/YM is the one to watch most closely given its thinner cost-adjusted and
  outlier-adjusted margins - not because anything wrong was found, but because it has the least
  room for slippage-model error before falling under the bar.
- **Reasoning:** This is the first time in the search-for-new-strategies push that a "looks clean"
  result actually survived the full scrutiny (costs + outliers) rather than collapsing under it -
  worth noting explicitly since Entries 20 and 22 both failed this exact same battery of checks.
  The pairs book remains the strongest live candidate in the project, now on firmer ground than
  the original Entry 9/13 verdicts, which were never actually cost-checked.

## Entry 24: Risk Limits Wired Into the Pairs Book + volume_confirmed_gap_test.py Rebuilt
- **Purpose:** Two housekeeping items, both previously flagged as pending and left undone.
- **Part A — volume_confirmed_gap_test.py.** This script crashed/was invalid for the same reason
  Entry 10 was corrected in Entry 16: it called `get_gap_signals_with_volume_from_archive()`,
  whose gap is defined off the first bar of the calendar date (the Sunday Globex reopen for most
  of its trades), not an intraday open-bell gap. Added
  `get_weekday_open_gap_signals_with_volume_from_archive()` - the volume-aware counterpart of
  Entry 16's corrected definition - and rebuilt the test script on it. Not yet run against real
  data (needs the user's archive); no verdict yet, just unblocked.
- **Part B — risk_limits.py wiring.** `risk_limits.py` and `position_sizing.py` existed but were
  never actually connected to the pairs forward-check scripts (`pairs_forward_check.py`,
  `generic_pairs_forward_check.py`) - unlike `gap_forward_check.py`, which already used both
  correctly via a `PaperBroker`. Followed that same proven pattern:
  - Position sizing: `position_sizing.fixed_fractional_size()`, sized off each pair's own average
    losing-trade dollar size from Entry 23's backtest (NQ/ES $514.89, NQ/YM $981.80, ES/YM
    $324.92, all at 1x leg-A-equivalent micro sizing), at HALF `risk_limits.MAX_RISK_PER_TRADE_PCT`
    (1.0% of account, not the full 2.0% cap) as a buffer against any single loss exceeding the
    historical average - these are two-leg trades, and real-world worst-case can exceed the mean.
    Leg B's contract count is `round(hedge_ratio * contracts_a)`, min 1 - real execution can't hold
    fractional contracts the way the backtest's continuous hedge ratio implicitly could, so this
    introduces a small, unavoidable hedge-tracking error versus the idealized backtest.
  - All three pairs scripts now share ONE `PaperBroker` account file
    (`data/pairs_paper_account.json`) and ONE risk-limits state file
    (`data/pairs_risk_limits_state.json`), so `MAX_OPEN_POSITIONS`/drawdown/daily-loss are enforced
    across the pairs book as a whole, not siloed per-pair. Added a `state_file` parameter to every
    function in `risk_limits.py` (default preserved, so `gap_forward_check.py` is untouched and
    keeps its own separate `risk_limits_state.json` - the two strategy families' circuit breakers
    don't get mixed together).
  - Each leg is opened/closed under a pair-tagged symbol (e.g. `"MNQ (NQ/ES)"`, `"MNQ (NQ/YM)"`),
    not a bare `"MNQ"` - since the account file is shared, two pairs can each have an open MNQ-type
    leg on the same day, and a bare symbol would risk closing the wrong pair's position.
  - Each pairs trade now consumes 2 of `MAX_OPEN_POSITIONS`' 3 slots (one per leg) - a deliberately
    conservative reading of real simultaneous market exposure, meaning at most 1 pairs trade can
    reliably be open before a 2nd is blocked, and a 3rd is blocked outright.
  - Added `src/tests/test_pairs_risk_wiring.py` (6 unit tests, self-contained via `tempfile` - no
    archive data or network needed): sizing never returns 0 contracts, tagged symbols don't
    collide across pairs sharing the account file, the open-positions gate actually blocks a 4th
    leg, closing both legs produces the correct combined balance, the pairs risk state is provably
    isolated from a simulated gap-strategy risk state, and the drawdown halt triggers correctly
    with a custom `state_file`. All 6 pass.
- **Caveats, stated plainly:** the $10,000 starting balance and the average-loss-based sizing are
  both estimates/placeholders, not verified against the user's actual intended paper-trading
  capital or a worst-case (rather than average-case) loss - update `PAIRS_STARTING_BALANCE` and the
  `AVG_LOSS_PER_UNIT_DOLLARS`/`avg_loss_per_unit` figures if either assumption should change. This
  wiring has NOT yet been run live (needs the user's actual venv + market data) - the mechanics are
  unit-tested, not yet forward-tested.
- **Reasoning:** Closes a real gap between "the pairs book passed Entry 23's re-validation" and
  "the pairs book is actually risk-managed the way the gap strategy already is" - until this entry,
  a live pairs signal would have opened a position with no sizing logic and no circuit breaker at
  all, in contrast to gap_forward_check.py's existing protection.

---

## Current Status Summary (as of 2026-09-10)
**Tier 1 — Live forward-testing:** Gap Continuation (re-rated WATCH per Entry 16, refined by
Entry 21's volatility-regime filter — real, evidence-backed improvement, but net-of-cost PF 1.17
still misses the 1.3 bar), NQ/ES Pairs, NQ/YM Pairs, ES/YM Pairs (re-validated WATCH per Entry 23 -
cost-aware and outlier-checked now, still short of the 100-trade/20-OOS-trade bar; Entry 18's
cointegration caution still stands as a caveat on the underlying mechanism; now risk-managed via
Entry 24's wiring, matching the gap strategy's existing protection)
**Flagship candidate:** Volume-Confirmed Gap Continuation (Entry 25) — the project's first outright
6/6 scorecard PASS, cost-adjusted PF 1.39, 4/4 improving walk-forward windows, structurally immune
to single-trade domination (fixed 40/80 stop/target). Still backtest-only - not yet forward-tested
live, and an open decision remains on whether to point the live `gap_forward_check.py` at this
definition. Not yet "validated for real capital" under this project's two-step bar.
**Watching, not yet live:** Overnight Session Drift (Entry 17/20) — stop-loss variant now tested;
all-weekdays version fails the scorecard on drawdown, but the Wednesday-specific subset is a
genuine (if unproven) hypothesis worth forward-testing
**Rejected:** Relative Momentum Rotation (Entry 19) — no momentum-persistence edge found across
NQ/ES/YM/RTY at a 1-day RTH hold. Crude Oil Gap Continuation (Entry 22) — outlier-dependent on the
2020-04-21 negative-oil-price anomaly; edge vanishes once the top 3 trades are excluded. Gold Gap,
Fixed Stop/Target (Entry 26) — no edge found across an 18-combination sweep (both directions, 3 gap
thresholds, 3 stop/target ratios); best cut in the whole sweep still fell short of the 1.3 bar.
**Second independent-asset-class candidate search:** 0 for 2 (crude oil, Entry 22; gold, Entry 26).
Deferred: the deeper intraday Databento crude-oil archive (`~/.databento/GLBX.MDP3/CL_c_0/`) was
not pulled for either pass (chose free yfinance daily history instead) and remains a possible
upgrade later - though for crude oil specifically, a fixed-stop structure (not just finer data) is
what would actually address the outlier-domination problem found there. For gold, worth considering
ATR-relative (volatility-scaled) sizing instead of flat percentages before concluding daily-gap
mechanics categorically don't transfer to commodities/metals.
**Process note:** the standardized scorecard (scorecard.py) now includes a cost-adjusted check
(Check 6, added after Entry 21) with per-instrument `slippage_points`/`commission` overrides, and
`walk_forward.py` now respects a `point_value` override (Entry 23) instead of silently defaulting
to 20. Every verdict from before these fixes that used a non-NQ point value should be treated with
that in mind until re-run - the pairs book (Entry 23) and the crude oil work (Entry 22) are now
both re-validated against the fixed tooling; the gap/overnight-drift book (Entries 16/17/20/21)
always used point_value correctly since MNQ's point_value=2 was passed explicitly throughout.
**All pending:** 100+ trade validation threshold at their respective (corrected, where applicable)
definitions.
**Validated for real capital:** None

---

## Entry 25: Volume-Confirmed Gap Continuation — First Outright 6/6 PASS in the Project
- **Hypothesis:** Now-corrected version of the test volume_confirmed_gap_test.py was meant to run
  (Entry 24 fixed the script; this is the first real result from it). Same as Entry 16's
  gap-continuation edge, filtered to only fire when the entry-time bar's opening volume is above
  its trailing 20-day average - the idea being a gap accompanied by real participation is more
  likely to be genuine order flow than a gap on thin volume.
- **Method:** `get_weekday_open_gap_signals_with_volume_from_archive()`, same stop/target (40/80
  pts) and MNQ sizing as Entry 16, swept volume-ratio thresholds [1.0x, 1.2x, 1.5x] across both
  continuation and reversion. Continuation improved monotonically as the threshold rose (PF 1.40 →
  1.57 → 1.88, on shrinking samples of 175 → 132 → 93 trades) - picked the MIDDLE cut (1.2x, 132
  trades) rather than the best-looking one (1.5x, PF 1.88, 93 trades), the same anti-cherry-picking
  principle used for every other threshold sweep in this project, since picking the most extreme
  cut off a monotonic sweep is close to picking the best of several looks at shrinking data.
- **Sample:** 132 trades (in-sample 92, out-of-sample 40).
- **Result:** 38.7% baseline win rate rising to 43.9% at this threshold, gross PF 1.57, net (cost-
  adjusted) PF **1.39** - clears the 1.3 bar on a cost-adjusted basis, not just gross. Expectancy
  $25.45/trade gross, $18.95/trade net. OOS expectancy ($34.00) again *higher* than in-sample
  ($21.74), same reassuring anti-overfitting pattern seen in Entry 16 and Entry 21. **4 of 4
  walk-forward windows profitable**, each one stronger than the last (PF 1.14 → 1.67 → 1.47 →
  2.12) - consistent, not just a single lucky window. Structurally bounded per Entry 21's lesson:
  avg win is essentially always exactly 80 pts and avg loss exactly -40 pts across every subset
  shown, confirming this inherits Entry 16's fixed stop/target and is not vulnerable to the kind of
  single-trade domination that sank Entries 20 and 22 - no separate outlier check needed given that
  structural guarantee (unlike the unbounded strategies, where the check was the only way to know).
  **Standardized scorecard: 6/6 - the first outright PASS (not PARTIAL/WATCH) in the project.**
- **Verdict:** PASS on the backtest, real methodological caveat attached. This is genuinely the
  strongest single result in the project's history - clears every check including cost-adjustment,
  on a real sample size, with consistent walk-forward improvement and no outlier-domination
  vulnerability by construction. The caveat: the threshold itself came from a 3-way sweep with a
  monotonic improve-with-smaller-sample pattern, which is exactly the shape you'd see from EITHER a
  real "more volume = more genuine continuation" mechanism (economically plausible) OR mild
  selection luck on a shrinking sample - picking the middle cut instead of the best one mitigates
  but does not eliminate this. A "PASSES SCORECARD" verdict on the backtest is not the same as
  "validated for real capital" per this project's standing two-step bar (backtest evidence, then
  live forward-validation) - the honest next step is forward-testing THIS specific calibration
  (1.2x) live, the same as every other WATCH-tier strategy, not skipping straight to deployment.
- **Open decision, not yet made:** whether to point `gap_forward_check.py` (the live script) at
  this volume-confirmed definition instead of Entry 16's unfiltered one, run it as a separate
  parallel forward-test, or leave live tracking as-is until more forward data accumulates. This is
  a real choice with real tradeoffs (this filter looks meaningfully better on the backtest, but
  changing what's live-tracked resets the forward-testing clock) that should be made deliberately,
  not automatically.
- **Reasoning:** The strongest evidence yet that gap-continuation has a real, exploitable core
  (Entry 16) with real, non-spurious refinements available (Entry 21's vol-regime filter, and now
  this) - each incremental filter has been checked for the specific failure modes (confounds,
  outliers, costs) that killed other candidates, and each has survived. Worth treating as the
  flagship candidate in the project, still short of real-capital status only because "passes every
  backtest check" and "proven in live, unseen conditions" are deliberately different bars here.

---

## Entry 26: Gold Gap, Fixed Stop/Target — Rejected, No Edge Found Across a Broad Sweep
- **Hypothesis:** Gold (COMEX GC=F), the second independent-asset-class candidate after Entry 22
  rejected crude oil, built with a FIXED stop/target from the start this time (Entry 21's lesson
  applied up front, not discovered after a failure) so single-trade domination is structurally
  impossible regardless of what the data shows.
- **Method:** `get_gold_gap_signals_with_stop_from_history()` - 26 years of free daily history
  (2000-2026, 6530 bars), swept BOTH continuation and reversion across 3 gap thresholds (0.5%,
  1.0%, 1.5%) and 3 stop/target combinations ([0.5%/1.0%], [0.5%/0.75%], [1.0%/2.0%]) - 18
  combinations total, deliberately broad given no prior basis for picking one.
- **Sample:** 237-1763 trades per combination depending on threshold.
- **Result:** No combination shows a real edge. Profit factors across the full sweep cluster
  between roughly 0.68 and 1.29, mostly below the 1.3 bar; the single best-looking cut in the
  entire sweep (reversion, 1.5% gap, 0.5%/1.0% stop-target) reaches only PF 1.29 on 237 trades -
  still short of the bar, on the smallest sample tested. The script's own placeholder "final pick"
  (continuation, 1.0% gap, 0.5%/1.0% stop-target - left un-updated after the sweep, a mistake worth
  owning rather than glossing over) scored worse still: gross PF 0.96, net (cost-adjusted) PF 0.83,
  3/6 on the standardized scorecard, FAIL. Its walk-forward was 1 of 4 windows profitable (windows
  1-3, spanning 2000-2019, were all net losers; window 4, 2019-2026, was profitable) - notably,
  2019-2026 is also gold's biggest secular bull run in this dataset, so that one profitable window
  is plausibly just directional beta to a rising gold market riding along with a LONG-biased
  continuation signal, not evidence of a real gap-specific mechanism (the same kind of confound
  Entry 21 checked for and ruled out in its own case - not required here since the aggregate result
  already fails decisively regardless). The outlier-concentration check's percentages are not
  meaningful for this combination (total P&L is already negative, so "top N trades as % of a
  negative total" produces confusing negative/over-100% figures) - a script gap worth fixing before
  reuse, but moot here since a strategy with negative expectancy doesn't need an outlier check to
  be rejected.
- **Verdict:** FAIL - reject gold gap trading (this formulation) as a strategy candidate.
- **Reasoning:** This is a clean, broad rejection (Entry 19's shape - no edge across many
  parameter combinations - not Entry 20/22's shape of one outlier-driven false positive), which is
  actually a reassuring kind of negative result: gold gaps just don't show the same
  momentum-continuation OR mean-reversion tendency NQ/ES/YM's opening gaps do, at either
  percentage-based threshold tested. Second independent-asset-class search is now 0-for-2 (crude
  oil, Entry 22; gold, Entry 26). Worth noting for any future attempt: both rejected candidates
  used PERCENTAGE-based gap/stop/target sizing because of decades of wide price-level history -
  worth considering whether an ATR-relative (volatility-scaled) sizing, rather than a flat
  percentage, might behave differently before concluding daily-gap mechanics categorically don't
  transfer to commodities/metals.