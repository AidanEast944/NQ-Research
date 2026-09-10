# Automated daily forward-test run (launchd)

Runs `run_forward_checks.py` (both `gap_forward_check.py` and
`volume_confirmed_gap_forward_check.py`, in that order) automatically on weekday mornings, entirely
on this Mac - `launchd` is macOS's own native scheduler. Nothing runs in the cloud and nothing
about your trades or account data leaves this machine as part of this automation; it's the exact
same scripts you've been running by hand, just triggered by the OS instead of by you.

## What it does

- Fires Monday-Friday at 6:35 AM (your Mac's local clock, currently Pacific) - a few minutes after
  the 9:30 AM Eastern market open.
- Logs everything to `data/forward_check_log.txt` (and errors to
  `data/forward_check_errors.txt`) - both already excluded from git via `.gitignore`, so they
  won't clutter commits.
- Sends a macOS notification only on days a trade actually opens or closes - stays silent on
  no-signal days.
- Safe to also keep running the scripts manually whenever you want - both scripts now skip an
  already-processed day rather than double-recording (Entry 29).

## Install

```bash
mkdir -p ~/Library/LaunchAgents
cp ~/nq-research/launchd/com.nq-research.forward-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.nq-research.forward-check.plist
```

Recommended: test it manually once BEFORE relying on the schedule, exactly as launchd would run it:

```bash
cd ~/nq-research/src
/Users/aidaneast/nq-research/venv/bin/python3 run_forward_checks.py
```

## Check on it

```bash
tail -50 ~/nq-research/data/forward_check_log.txt
```

## Uninstall / pause

```bash
launchctl unload ~/Library/LaunchAgents/com.nq-research.forward-check.plist
rm ~/Library/LaunchAgents/com.nq-research.forward-check.plist
```

(Unloading pauses it; removing the file makes it permanent. The scripts and your data are
untouched either way - this only removes the schedule.)

## Changing the time or days

Edit the `Hour`/`Minute`/`Weekday` values in
`~/Library/LaunchAgents/com.nq-research.forward-check.plist` directly, then:

```bash
launchctl unload ~/Library/LaunchAgents/com.nq-research.forward-check.plist
launchctl load ~/Library/LaunchAgents/com.nq-research.forward-check.plist
```
