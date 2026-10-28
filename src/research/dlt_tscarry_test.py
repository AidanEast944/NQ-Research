"""
PRE-REGISTERED test dlt_tscarry (lab spec lab/proposals/dlt_tscarry.json, family diversified_lowturnover).
Thin wrapper: all rules are in dlt_engine.py and all procedure/pass criteria are in dlt_test.py (read its docstring).
Nothing here may be tuned after the run.
Run:  cd ~/nq-research && source venv/bin/activate && python3 src/research_runner.py run dlt_tscarry
"""
import dlt_test

CAND = {"id": "dlt_tscarry", "kind": "tscarry", "months": 0, "declared_trials": 1}

if __name__ == "__main__":
    dlt_test.run(CAND)
