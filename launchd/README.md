# launchd automation (this Mac only)

This folder tracks the `launchd` jobs (macOS's own native scheduler) that this Claude engagement
has added or fixed. Everything here runs entirely on this Mac - the Python process, the network
calls, and all trade/account data never leave this machine as part of any of this.

**Important:** this repo's `launchd/` folder is not the whole picture. Several other
`com.nqresearch.*` jobs (Fade, Trend, the original single-symbol Gap check, the NQ/ES pairs check,
and a daily archiver/weekly scorecard) were already installed on this Mac before this engagement
found them (see `research_log.md` Entry 32) and are not managed from this repo - they were set up
independently and their plists live only in `~/Library/LaunchAgents`, not here. To see the full
live picture at any time:

```bash
launchctl list | grep nqresearch
launchctl print gui/$(id -u)/com.nqresearch.<name>   # exact schedule + last exit code for one job
```

## What's tracked here

| plist | script | what it does | when (Pacific) |
|---|---|---|---|
| `com.nqresearch.volumegapcheck.plist` | `volume_confirmed_gap_forward_check.py` | opens today's volume-confirmed gap trade(s), 1.2x and 1.5x thresholds independently | 5:38 AM |
| `com.nqresearch.volumegapresolve.plist` | `volume_confirmed_gap_resolve.py` | resolves whatever the above opened, using the full day's price bars | 5:07 PM |
| `com.nqresearch.gapresolve.plist` | `gap_forward_resolve.py` | resolves today's unfiltered gap trade (opened by the pre-existing `com.nqresearch.gapforward` job at 5:37 AM - not this repo, see below) | 5:05 PM |
| `com.nqresearch.dashboard.plist` | `generate_dashboard.py` | regenerates `results/dashboard.html` from every currently-active strategy's state | 5:15 PM |
| `com.nqresearch.morningbrief.plist` | `generate_morning_brief.py` | short daily brief (`results/morning_brief.html`) - what resolved yesterday, what opened this morning, what's still carried over, plus a readiness snapshot | 5:45 AM |
| `com.nqresearch.trendforward.plist` | `trend_forward_daily.py` | manages (does not open new) Trend positions - retired strategy, Entry 6 | 5:10 PM |

`com.nqresearch.gapforward` (the pre-existing job that opens the unfiltered gap trade at 5:37 AM)
is NOT tracked here - it already existed, and this engagement only fixed the script it runs
(`gap_forward_check.py`, split into open-only + the new `gapresolve` step above - Entry 32) rather
than touching its schedule.

`com.nqresearch.trendforward.plist` IS tracked here even though the job predates this engagement -
its original schedule (2:15 PM) ran nearly 3 hours before `com.nqresearch.dailysave` (5:00 PM, not
tracked here) writes that day's archive file, so it was silently failing to find "today" in its own
data every single day since 2026-09-04, leaving an open position unmanaged for a week (Entry 34).
Moved to 5:10 PM - after the archiver, before the 5:15 PM dashboard job picks up its fresh state.

### Why an open step and a resolve step, run hours apart

The morning job only has a few minutes of real price history right after the entry bar - not
enough to know whether a trade would actually hit its stop or target that day. Trying to resolve
same-run almost always fell through to a placeholder "end of day, nothing happened" result that
then became the permanent record, even when the trade genuinely won or lost later that day. The
evening resolve job runs after the market closes, so it can walk the whole day's bars and record
what actually happened. This matches the pattern the pre-existing `fade_paper_check.py` /
`fade_paper_resolve.py` jobs already used correctly. Full writeup: `research_log.md` Entry 32.

## Install (for a plist you're adding or haven't installed yet)

```bash
mkdir -p ~/Library/LaunchAgents
cp ~/nq-research/launchd/com.nqresearch.<name>.plist ~/Library/LaunchAgents/
plutil -lint ~/Library/LaunchAgents/com.nqresearch.<name>.plist
chmod 644 ~/Library/LaunchAgents/com.nqresearch.<name>.plist
launchctl bootout gui/$(id -u)/com.nqresearch.<name> 2>/dev/null   # clear any stale registration - ok if this errors
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nqresearch.<name>.plist
```

Use `bootstrap`/`bootout`, not the older `load`/`unload` - those are deprecated on modern macOS and
tend to fail with a generic "Input/output error" instead of a real reason. `plutil -lint` catches a
malformed plist before that happens. Verify registration:

```bash
launchctl print gui/$(id -u)/com.nqresearch.<name>
```

If macOS shows a notification about a new background item, that's expected - System Settings ->
General -> Login Items & Extensions is where you can see or revoke it later.

Recommended: test any new script manually once first, exactly as launchd would run it:

```bash
cd ~/nq-research
/Users/aidaneast/nq-research/venv/bin/python3 src/<script>.py
```

## Replacing an existing job's plist (e.g. the dashboard fix in Entry 32)

Same as install, but `bootout` the currently-running job FIRST so the old registration doesn't
linger:

```bash
launchctl bootout gui/$(id -u)/com.nqresearch.dashboard
cp ~/nq-research/launchd/com.nqresearch.dashboard.plist ~/Library/LaunchAgents/
plutil -lint ~/Library/LaunchAgents/com.nqresearch.dashboard.plist
chmod 644 ~/Library/LaunchAgents/com.nqresearch.dashboard.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.nqresearch.dashboard.plist
```

## Check on a job

```bash
tail -50 ~/nq-research/data/<name>_log.txt
tail -50 ~/nq-research/data/<name>_errors.txt
```

## Uninstall / pause

```bash
launchctl bootout gui/$(id -u)/com.nqresearch.<name>
rm ~/Library/LaunchAgents/com.nqresearch.<name>.plist
```

(Booting out pauses it; removing the file makes it permanent. Scripts and data are untouched
either way - this only removes the schedule.)

## Changing the time or days

Edit the `Hour`/`Minute`/`Weekday` values in `~/Library/LaunchAgents/com.nqresearch.<name>.plist`
directly, then `bootout` + `bootstrap` again (same as replacing a plist, above).

## History

- 2026-09-10 (Entry 30): originally automated as a single job
  (`com.nq-research.forward-check` running `run_forward_checks.py`) before the pre-existing
  `com.nqresearch.*` system was discovered.
- 2026-09-10 (Entry 32): found and removed - it duplicated the pre-existing
  `com.nqresearch.gapforward` job (same script, twice a day) and its log paths collided with the
  pre-existing `com.nqresearch.forwardcheck` job's. Replaced by the four jobs listed above, each
  independently named and scheduled, matching this codebase's one-script-per-job convention.
