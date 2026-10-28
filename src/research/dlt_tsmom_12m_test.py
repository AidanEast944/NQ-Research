"""
PRE-REGISTERED test dlt_tsmom_12m (lab spec lab/proposals/dlt_tsmom_12m.json, family diversified_lowturnover).
Thin wrapper: all rules are in dlt_engine.py and all procedure/pass criteria are in dlt_test.py (read its docstring).
Nothing here may be tuned after the run.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run dlt_tsmom_12m
"""
import dlt_test

CAND = {"id": "dlt_tsmom_12m", "kind": "tsmom", "months": 12, "declared_trials": 1}

if __name__ == "__main__":
    dlt_test.run(CAND)
