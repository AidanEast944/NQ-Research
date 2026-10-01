"""
Standing stale-position sanity check (research_log.md Entry 58).

Runs independent of any single strategy's own resolve logic - the whole point is to catch a
resolve bug like Entry 57's even in a script this check doesn't know the internals of, by just
looking at account state + real price action from the outside.

For every known live account:
  - "intraday" strategies (gap family, vol+momentum): any open position not opened today is
    flagged STALE - by design these should always close same day via stop/target/EOD, so still
    being open on a later day means its resolve script missed a run.
  - "multiday" strategies (pairs): flagged WATCH (not necessarily broken) once held longer than a
    generous reference threshold, since these are allowed to run for a while, but an unbounded
    hold could also indicate the exit check itself has stopped running.

Where a fresh local price archive is available for the traded instrument, this also independently
checks whether the position's stop or target has already been breached by real price action since
entry - this doesn't rely on trusting the strategy's own resolve script at all. That's the part
that would have caught Entry 57's bug on day one instead of needing a manual review six days later.

Meant to run daily, after the normal resolve jobs. Purely diagnostic - never touches account state.
"""
import glob
import os
import sys
import pandas as pd
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
from paper_broker import PaperBroker

TODAY = date.today()

REGISTRY = [
    {"label": "Gap (unfiltered)", "account_file": "data/gap_paper_account.json",
     "kind": "intraday", "symbol": "NQ"},
    {"label": "Volume-Confirmed Gap NQ 1.2x", "account_file": "data/volume_gap_1_2x_paper_account.json",
     "kind": "intraday", "symbol": "NQ"},
    {"label": "Volume-Confirmed Gap NQ 1.5x", "account_file": "data/volume_gap_1_5x_paper_account.json",
     "kind": "intraday", "symbol": "NQ"},
    {"label": "Volume-Confirmed Gap YM 1.2x", "account_file": "data/volume_gap_ym_1_2x_paper_account.json",
     "kind": "intraday", "symbol": "YM"},
    {"label": "Volume-Confirmed Gap YM 1.5x", "account_file": "data/volume_gap_ym_1_5x_paper_account.json",
     "kind": "intraday", "symbol": "YM"},
    {"label": "Volume-Confirmed Gap ES 1.2x", "account_file": "data/volume_gap_es_1_2x_paper_account.json",
     "kind": "intraday", "symbol": "ES"},
    {"label": "Vol+Momentum Reversal (NQ)", "account_file": "data/vol_momentum_reversal_paper_account.json",
     "kind": "intraday", "symbol": "NQ"},
    {"label": "Pairs (NQ/ES, NQ/YM, ES/YM)", "account_file": "data/pairs_paper_account.json",
     "kind": "multiday", "symbol": None, "max_days": 25},
]

# Only NQ's archive (data/raw/) is reliably kept current as of this check's writing - YM/ES
# archives (data/raw_ym, data/raw_es, and the *_extended variants) stopped updating around
# 2026-09-09. Rather than silently skip or guess, the price-based check below only runs for
# symbols listed here, and says so explicitly for the rest.
ARCHIVE_GLOBS = {
    "NQ": "data/raw/nq_15m_*.csv",
}


def latest_archive_bars(symbol, since_date):
    pattern = ARCHIVE_GLOBS.get(symbol)
    if not pattern:
        return None
    frames = []
    for fn in sorted(glob.glob(pattern)):
        base = os.path.basename(fn)
        try:
            file_date = date.fromisoformat(base.rsplit("_", 1)[-1].replace(".csv", ""))
        except ValueError:
            continue
        if file_date >= since_date:
            frames.append(pd.read_csv(fn))
    if not frames:
        return None
    return pd.concat(frames, ignore_index=True)


def check_account(entry):
    path = entry["account_file"]
    flags = []

    if not os.path.exists(path):
        print(f"[{entry['label']}] no account file yet - never traded.")
        return flags

    broker = PaperBroker(starting_balance=10000, state_file=path)
    if not broker.positions:
        print(f"[{entry['label']}] no open positions. OK.")
        return flags

    for position in broker.positions:
        entry_date = date.fromisoformat(position["entry_date"])
        age_days = (TODAY - entry_date).days

        if entry["kind"] == "intraday":
            if entry_date != TODAY:
                flags.append(
                    f"[{entry['label']}] STALE: position opened {entry_date} ({age_days}d ago) is "
                    f"still open, but this strategy is intraday-only and should always close same "
                    f"day. Its resolve script likely missed a run - check {path} and the matching "
                    f"*resolve*.py / its log file."
                )
            else:
                print(f"[{entry['label']}] position opened today, not yet due to resolve. OK.")

            bars = latest_archive_bars(entry["symbol"], entry_date)
            if bars is None:
                print(f"[{entry['label']}] (no current local archive for {entry['symbol']} - "
                      f"skipping independent price check, not assuming OK.)")
            elif not bars.empty:
                direction = position["direction"]
                stop_price = position["stop_price"]
                target_price = position["target_price"]
                if direction == "LONG":
                    breached = (bars["Low"] <= stop_price).any() or (bars["High"] >= target_price).any()
                else:
                    breached = (bars["High"] >= stop_price).any() or (bars["Low"] <= target_price).any()
                if breached:
                    flags.append(
                        f"[{entry['label']}] PRICE CHECK: local archive shows price has already "
                        f"crossed this position's stop or target since entry ({entry_date}) - it "
                        f"should have been resolved already, independent of the entry-date flag above."
                    )
        else:  # multiday
            max_days = entry.get("max_days", 25)
            if age_days > max_days:
                flags.append(
                    f"[{entry['label']}] WATCH: a position from {entry_date} has been open "
                    f"{age_days}d, past the {max_days}d reference threshold. Not necessarily a "
                    f"bug (this strategy holds for z-score reversion, not a fixed window), but "
                    f"worth a manual look - verify the exit check is still running for it."
                )
            else:
                print(f"[{entry['label']}] position from {entry_date} ({age_days}d) within normal range. OK.")

    return flags


def main():
    all_flags = []
    for entry in REGISTRY:
        all_flags.extend(check_account(entry))

    print()
    if all_flags:
        print(f"=== {len(all_flags)} FLAG(S) ===")
        for f in all_flags:
            print(f"- {f}")
    else:
        print("=== No stale or suspicious positions found. ===")


if __name__ == "__main__":
    main()
