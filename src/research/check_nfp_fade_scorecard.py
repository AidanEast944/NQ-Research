import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nfp_fade_strategy import get_nfp_fade_signals
from scorecard import run_scorecard
from trial_count import count_research_trials

signals = get_nfp_fade_signals()
run_scorecard(
    signals,
    "NFP Fade Strategy",
    entry_col="entry_price",
    date_col="date",
    point_value=2,
    num_trials=count_research_trials()
)