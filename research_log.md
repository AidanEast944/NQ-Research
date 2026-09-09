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

---

## Current Status Summary (as of 2026-09-09)
**Tier 1 — Live forward-testing:** Gap Continuation (re-rated WATCH per Entry 16, not the PASS
Entry 10 implied — same live script, corrected backtest), NQ/ES Pairs, NQ/YM Pairs, ES/YM Pairs
(PASS per Entries 9/13, but see Entry 18's cointegration caution)
**Watching, not yet live:** Overnight Session Drift (Entry 17) — pending a stop-loss variant
**All pending:** 100+ trade validation threshold at their respective (corrected, where applicable) definitions
**Validated for real capital:** None