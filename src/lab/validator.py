"""Independent Validator: deterministic vetoes. It can only reject or pass-to-human, never approve.

check_result(result, policy) expects the dict a registered test records, e.g.
{"n_trades":..,"n_oos_trades":..,"cost_model":{..},"net_profit_factor":..,"leakage_test_passed":bool,
 "holdout_touched":bool,"declared_trials":int,"scorecard_run":bool}
"""


def check_result(result, policy, families=None):
    vetoes = []
    if not result.get("scorecard_run"):
        vetoes.append("scorecard (7-check) was not run")
    if result.get("n_trades", 0) < policy["min_trades"]:
        vetoes.append(f"sample too small: {result.get('n_trades', 0)} < {policy['min_trades']}")
    if result.get("n_oos_trades", 0) < policy["min_oos_trades"]:
        vetoes.append(f"OOS sample too small: {result.get('n_oos_trades', 0)} < {policy['min_oos_trades']}")
    cm = result.get("cost_model") or {}
    fam = ((families or {}).get("families", {}) or {}).get(result.get("family"))
    if fam and fam.get("cost_model"):       # a family with its own approved cost model is held to that one
        if cm != fam["cost_model"]:
            vetoes.append("family cost model was not applied")
    else:
        req = policy["required_cost_model"]
        if cm.get("slippage_points") != req["slippage_points"] or cm.get("commission_round_trip") != req["commission_round_trip"]:
            vetoes.append("realistic project cost model was not applied")
    if result.get("leakage_test_passed") is not True:
        vetoes.append("leakage truncation test missing or failed")
    if result.get("holdout_touched"):
        vetoes.append("sealed holdout was touched during discovery")
    if not isinstance(result.get("declared_trials"), int):
        vetoes.append("trial count not declared")
    return {"passed_deterministic_checks": not vetoes, "vetoes": vetoes,
            "note": "Passing only means no automatic veto. A human scores against the pre-registered criteria."}


def check_many(result, policy, families=None):
    """Accepts one flat result dict, or a dict of per-symbol result dicts (what the test scripts write)."""
    if result and all(isinstance(v, dict) for v in result.values()):
        return {k: check_result(v, policy, families) for k, v in result.items()}
    return check_result(result, policy, families)
