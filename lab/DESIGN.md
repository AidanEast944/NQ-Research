# nq-research Lab: human-in-the-loop research agents (design v1)

Built ALONGSIDE the existing system. Nothing in src/, registry/, data/ or launchd/ is modified.
Everything new lives in `src/lab/`, `lab/`, and `src/tests/test_lab_*.py`.

## Principle
Agents (Claude, run by the human in a session, no paid API) may only WRITE PROPOSALS.
Deterministic Python owns data, backtests, statistics, costs, budget, dedup, queue, risk, logging.
Humans own: approving a spec, scoring a result, promotion, and anything live.

## Flow
1. Strategy Engineer (Claude) writes a spec JSON into `lab/proposals/`.
2. `python3 src/lab/orchestrator.py submit lab/proposals/X.json` validates it, checks the holdout
   rules, fingerprints it, rejects duplicates (recorded), checks trial budget and weekly allowance,
   then puts it in the queue (`lab/state/queue.json`). Every decision is appended to
   `lab/state/agent_log.jsonl`.
3. Human runs `orchestrator.py approve ID` (records the decision; it never runs anything).
4. Approved spec is turned into a pre-registered script and registered through the EXISTING
   `src/research_runner.py` (phase 2: script compiler). Run-once, committed-script, trial ledger
   rules of the runner are unchanged.
5. Independent Validator: `validator.py` runs deterministic vetoes (cost model applied, minimum
   samples, truncation-based leakage test, holdout untouched, trial count declared). A Claude review
   pass may add concerns but can only veto, never approve.
6. Human scores, records verdict via the runner, writes the log entry. Promotion stays in
   `promotion_queue.py` (human approval); `live_gate.py` is edited by Aidan only.
7. Reporter writes `lab/reports/weekly_YYYY-MM-DD.md` from the logs.

## Roles (MVP)
| Role | Who | Output |
|---|---|---|
| Research Director | deterministic orchestrator | queue, budget, dedup, status |
| Strategy Engineer | Claude (in session) | spec JSON in lab/proposals |
| Independent Validator | deterministic checks + Claude review (veto only) | validation JSON |
| Research Reporter | deterministic report from logs, Claude may annotate | weekly markdown |
Deferred: Discovery Researcher, Data Analyst, Risk Analyst (wrap coverage_report / decay_monitor).

## Data and holdout policy
* Historical NQ/ES/YM 2015-2026 is CONTAMINATED: many tests already used it. It is "discovery/known".
* Sealed holdout = RTY archive (`data/raw_rty_extended`) + all forward paper data after the lab start date.
  Specs may not name RTY in `discovery_data`; the holdout may only be touched by ONE final confirmation
  run per hypothesis, declared in the spec (`holdout_confirmation`). Enforced in `guard.py`.

## Budget policy (`lab/policy.json`)
* Total trials come from `registry/research_registry.json` (never raised by the lab).
* Weekly allowance for lab-originated trials: 2. Hard stop at remaining budget.
* Every spec declares `declared_trials`; submit refuses if over either limit.

## Non-negotiables (and where they are enforced)
* No live authority: no code in src/lab imports or writes live_gate.py / risk_limits.py / paper accounts;
  a test asserts this by scanning source.
* Agents write only to lab/proposals (test asserts orchestrator refuses spec paths elsewhere).
* Look-ahead: `leakage.truncation_test` (feature at time t must not change when future bars are removed).
* Costs: spec must set `cost_model` = project default (1 pt slippage + $4.50 round trip).
* Duplicates/failed experiments: fingerprint ledger `lab/state/hypotheses.jsonl`, rejections logged.
* Reproducibility: agent_log records spec hash, git commit, config, experiment id, timestamp.
* Cost control: no paid API calls; concurrency 1; weekly trial cap.
* Scorecard: unchanged; lab only calls it through registered scripts.

## Research families (added 2026-10-26, Entry 86)
`registry/families.json` is the allowed-idea map. Every spec must name a `family`.
* `gap_intraday`, `time_of_day`: FROZEN. The lab refuses new specs; the runner refuses `register --family` for them.
* `diversified_lowturnover`: PROPOSED, `approved_by_human=false`. No trial can be spent until Aidan edits the file to approve it
  and fixes the budget (proposed 12, counted separately from the global 100 with a deliberately harsh DSR rule: family trials + 20).
  Own universe (19 futures: equity index, rates, energy, metals, FX, ags), own periods (discovery 2010-2019, validation 2020-2023,
  sealed holdout 2024 onward, touched once per surviving rule), own cost model, canonical published parameters only.
* Specs whose data windows reach into a family's sealed holdout, or that name symbols outside its universe, are refused unless the
  spec is the declared one-time `holdout_confirmation`.
* Global-ledger families (no `budget_trials`) keep the old behaviour, including the 100-trial cap.
