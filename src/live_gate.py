"""
Shared live-trading gate for every *_forward_check.py script (added 2026-09-15). Default is
CLOSED: a live script whose strategy_key isn't explicitly listed in LIVE_STRATEGIES below opens
no new positions, period.

Why this exists: Fade traded live for ~3 weeks after already failing its own original backtest
(research_log.md Entry 35) because Trend had a STRATEGY_RETIRED guard and Fade simply never got
one - two independent hand-written booleans in two different files, and it was easy for one to be
forgotten. This module makes "closed" the default for every strategy instead of something each new
script has to remember to opt out of - a new live script that is never added to LIVE_STRATEGIES
below trades nothing, rather than trading freely until an audit happens to catch it.

To promote a strategy: add it below with its current scorecard verdict and the research_log.md
entry that justified going live. To retire one: delete its entry, or change its verdict to
anything other than "PASS"/"WATCH" - either way, is_open_for_new_entries() starts returning False
on the very next run, no per-script edit required.

This only gates NEW entries. It intentionally does not touch resolve/close logic - an existing
open position is still managed and closed normally by its script's own resolve step even after a
strategy is retired here. Retiring a strategy is not the same as abandoning a live position.

Current registry mirrors what's actually live as of 2026-09-15 (see the corresponding
research_log.md entries for the numbers behind each verdict) - this is a snapshot to be kept
current, not something to treat as permanently correct.
"""

LIVE_STRATEGIES = {
    "gap_unfiltered": {"verdict": "WATCH", "entry": 16},
    "volume_confirmed_gap_nq": {"verdict": "WATCH", "entry": 25},
    "volume_confirmed_gap_es": {"verdict": "WATCH", "entry": 42},
    "volume_confirmed_gap_ym": {"verdict": "WATCH", "entry": 46},
    "pairs_nq_es": {"verdict": "WATCH", "entry": 23},
    "pairs_nq_ym": {"verdict": "WATCH", "entry": 23},
    "pairs_es_ym": {"verdict": "WATCH", "entry": 23},
     "vol_momentum_reversal_nq": {"verdict": "WATCH", "entry": 54},
}

_OPEN_VERDICTS = ("PASS", "WATCH")


def is_open_for_new_entries(strategy_key):
    """True only if strategy_key is explicitly registered here with a PASS or WATCH verdict.
    Anything not registered - a typo, a brand-new script nobody added yet, a strategy that was
    removed on retirement - is closed by default, not open by default."""
    info = LIVE_STRATEGIES.get(strategy_key)
    if info is None:
        return False
    return info.get("verdict") in _OPEN_VERDICTS


def gate_new_entry(strategy_key, label=None):
    """Call right before opening a new position in a *_forward_check.py script.

    Returns True if the strategy is open for new entries (caller proceeds normally). Returns
    False and prints an explanatory message if it is not (caller should skip opening a position
    for this run, exactly like the existing STRATEGY_RETIRED pattern in trend_forward_daily.py
    and fade_paper_check.py - this function does not exit the process itself, since some callers
    still need to save state or return from a per-pair function rather than sys.exit()).
    """
    if is_open_for_new_entries(strategy_key):
        return True
    tag = f"[{label}] " if label else ""
    print(f"{tag}'{strategy_key}' is not an open live strategy in live_gate.py - "
          f"no new position will be opened this run. "
          f"Registered/open strategies: {sorted(k for k in LIVE_STRATEGIES if is_open_for_new_entries(k))}")
    return False
