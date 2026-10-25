"""Independent Validator: deterministic vetoes. It can only reject or pass-to-human, never approve.

check_result(result, policy) expects the dict a registered test records, e.g.
{"n_trades":..,"n_oos_trades":..,"cost_model":{..},"net_profit_factor":..,"leakage_test_passed":bool,
 "holdout_touched":bool,"declared_trials":int,"scorecard_run":bool}
"""


def check_result(result, policy):
    vetoes = []
    if not result.get("scorecard_run"):
        vetoes.append("scorecard (7-check) was not run")
    if result.get("n_trades", 0) < policy["min_trades"]:
        vetoes.append(f"sample too small: {result.get('n_trades', 0)} < {policy['min_trades']}")
    if result.get("n_oos_trades", 0) < policy["min_oos_trades"]:
        vetoes.append(f"OOS sample too small: {result.get('n_oos_trades', 0)} < {policy['min_oos_trades']}")
    cm, req = result.get("cost_model") or {}, policy["required_cost_model"]
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
