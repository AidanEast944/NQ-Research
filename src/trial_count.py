"""
Single source of truth for how many independent strategy trials this project has run - used by
scorecard.py's Check 7 (Deflated Sharpe Ratio) so num_trials is never a hand-typed, driftable
literal scattered across call sites.

KNOWN UNDERCOUNT: this counts numbered "## Entry N" headers in research_log.md, which is a
reasonable proxy but not exact - some entries (e.g. Entry 25's 3-way volume threshold sweep)
contain multiple internal parameter trials counted as one entry here. Treat this as a
CONSERVATIVE FLOOR, not a precise count - the true DSR is likely even more skeptical than
what this produces.
"""
import re
import os

def count_research_trials(log_path=None):
    if log_path is None:
        log_path = os.path.join(os.path.dirname(__file__), "..", "research_log.md")

    if not os.path.exists(log_path):
        raise FileNotFoundError(
            f"research_log.md not found at {log_path} - num_trials cannot be determined. "
            "This is deliberate: silently falling back to a default would reintroduce the "
            "exact bug this function exists to fix."
        )

    with open(log_path, "r") as f:
        content = f.read()

    entries = re.findall(r"^## Entry (\d+):", content, re.MULTILINE)
    if not entries:
        raise ValueError(
            f"No '## Entry N:' headers found in {log_path} - num_trials cannot be determined."
        )

    return max(int(e) for e in entries)