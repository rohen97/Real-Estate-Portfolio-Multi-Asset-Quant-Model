"""Two-stage scenario commitments with executable schedules and funded Hold recourse."""
from __future__ import annotations

import copy
import math
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from packages.optimisation.common import (
    DEVELOPMENT, RESOURCE_UNITS, TIMING_INTERPRETATION, audit_plan, build_options,
    check, finite, public_selection, summarise_audit, validate_inputs, weighted_loss_cvar,
)


def default_scenarios():
    return [
        {"name": "Base", "probability": .5, "npv_multiplier": 1, "capex_multiplier": 1, "sale_receipt_multiplier": 1, "delay_years": 0},
        {"name": "Downside", "probability": .25, "npv_multiplier": .55, "capex_multiplier": 1.18, "sale_receipt_multiplier": .9, "delay_years": 1},
        {"name": "Upside", "probability": .25, "npv_multiplier": 1.35, "capex_multiplier": .95, "sale_receipt_multiplier": 1.05, "delay_years": 0},
    ]


def _scenario_execution(option, scenario, horizon):
    row = copy.deepcopy(option)
    delay = scenario["delay_years"] if row["action"] in DEVELOPMENT else 0
    row["planned_start_year"] = row["start_year"]
    row["start_year"] += delay
    row["delay_years"] = delay
    row["discount_factor"] *= (1 + row["discount_rate"]) ** -delay
    row["completes_within_horizon"] = row["action"] not in DEVELOPMENT or row["start_year"] - 1 + row["duration_years"] <= horizon
    for key in ("capex_schedule_m", "receipt_schedule_m", "lost_noi_m", "active_projects", "resource_schedule"):
        row[key] = ([0.] * delay + option[key])[:horizon]
    base_spend = row["capex_schedule_m"][:]
    row["capex_schedule_m"] = [v * scenario["capex_multiplier"] for v in base_spend]
    base_receipts = row["receipt_schedule_m"][:]
    row["receipt_schedule_m"] = [v * scenario["sale_receipt_multiplier"] for v in base_receipts]
    # A downside multiplier must worsen negative as well as positive NPVs.
    baseline = option["undiscounted_expected_npv_m"]
    stressed = baseline + abs(baseline) * (scenario["npv_multiplier"] - 1)
    extra_cost_pv = sum(v * (scenario["capex_multiplier"] - 1) / (1 + row["discount_rate"]) ** y
                        for y, v in enumerate(base_spend))
    receipt_change_pv = sum(v * (scenario["sale_receipt_multiplier"] - 1) / (1 + row["discount_rate"]) ** y
                            for y, v in enumerate(base_receipts))
    row["expected_npv_m"] = stressed * row["discount_factor"] - extra_cost_pv + receipt_change_pv
    row["capex_m"] = sum(row["capex_schedule_m"]) - sum(row["receipt_schedule_m"])
    row["capex"], row["receipts"] = row["capex_schedule_m"], row["receipt_schedule_m"]
    row["noi_loss"], row["resource"] = row["lost_noi_m"], row["resource_schedule"]
    row["scenario"] = scenario["name"]
    return row


def _cancel_to_hold(option, hold, scenario, horizon):
    if hold is None:
        return None
    row = _scenario_execution(hold, scenario, horizon)
    fee = option["cancel_cost_m"]
    row["cancelled_action"] = option["action"]
    row["cancelled_planned_start_year"] = option["start_year"]
    row["cancellation_cost_m"] = fee
    row["expected_npv_m"] -= fee
    # Scenarios resolve before construction. Cancellation is paid in decision year 1,
    # never discounted away by nominating a project to start late in the horizon.
    row["capex_schedule_m"][0] += fee
    row["capex_m"] += fee
    return row


def _completion_year(row):
    if row["action"] in DEVELOPMENT:
        return row["start_year"] - 1 + row["duration_years"]
    if row["action"] == "Sell":
        return row["start_year"] - 1 + row.get("sale_delay_years", 0)
    return row["start_year"] - 1


def optimise_two_stage(asset_actions: list[dict], scenarios=None, horizon_years=5,
                       total_capital_budget_m=500, annual_capital_budgets=None,
                       minimum_liquidity_m=50, max_concurrent_projects=8, contractor_capacity=None,
                       minimum_noi_ratio=.7, cvar_alpha=.95, cvar_penalty=.25, max_leverage=.65,
                       dependencies=None, concentration_limits=None, discount_rate=.078,
                       max_development_share=1.0, cancellation_cost_rate=.08):
    annual = validate_inputs(asset_actions, horizon_years, total_capital_budget_m, minimum_liquidity_m,
                             annual_capital_budgets, max_concurrent_projects, minimum_noi_ratio, cvar_penalty)
    if not 0 < cvar_alpha < 1 or not 0 <= max_development_share <= 1:
        raise ValueError("cvar_alpha must be in (0,1), development share in [0,1]")
    if finite(max_leverage, "max_leverage") < 0 or finite(cancellation_cost_rate, "cancellation_cost_rate") < 0:
        raise ValueError("max_leverage and cancellation_cost_rate must be nonnegative")
    capacity = [12] * horizon_years if contractor_capacity is None else list(contractor_capacity)
    if len(capacity) != horizon_years or any(finite(x, "contractor capacity") < 0 for x in capacity):
        raise ValueError("contractor_capacity must have one nonnegative value per year")
    scenarios = copy.deepcopy(default_scenarios() if scenarios is None else scenarios)
    if not scenarios or len({s["name"] for s in scenarios}) != len(scenarios):
        raise ValueError("Provide nonempty scenarios with unique names")
    for sc in scenarios:
        for field, default in (("probability", 0), ("npv_multiplier", 1), ("capex_multiplier", 1), ("sale_receipt_multiplier", 1), ("delay_years", 0)):
            sc[field] = finite(sc.get(field, default), field)
            if sc[field] < 0:
                raise ValueError(f"{field} must be nonnegative")
        sc["delay_years"] = math.ceil(sc["delay_years"])
    probabilities = np.array([s["probability"] for s in scenarios])
    if not np.isclose(probabilities.sum(), 1):
        raise ValueError("Scenario probabilities must sum to one")
    dependencies, concentration_limits = dependencies or [], concentration_limits or {}
    for field, limits in concentration_limits.items():
        if field not in ("segment", "planning_area") or any(finite(x, "concentration limit") < 0 for x in limits.values()):
            raise ValueError("Concentration limits must use segment/planning_area and nonnegative action counts")
    options = build_options(asset_actions, horizon_years, discount_rate)
    asset_ids = {a["asset_id"] for a in asset_actions}
    if not options or asset_ids - {o["asset_id"] for o in options}:
        return {"feasible": False, "status": "An asset has no action completing within the horizon", "selections": [], "first_stage": []}
    holds = {o["asset_id"]: o for o in options if o["action"] == "Hold"}
    for o in options:
        o["base_npv_m"] = o["expected_npv_m"]  # backward-compatible aliases
        o["capex"], o["receipts"] = o["capex_schedule_m"], o["receipt_schedule_m"]
        o["noi_loss"], o["resource"] = o["lost_noi_m"], o["resource_schedule"]
        o["commitment_m"] = sum(o["capex_schedule_m"]) * .1
        o["cancel_cost_m"] = sum(o["capex_schedule_m"]) * cancellation_cost_rate if o["action"] in DEVELOPMENT else 0.
    execution = [[_scenario_execution(o, s, horizon_years) for o in options] for s in scenarios]
    cancellation = [[_cancel_to_hold(o, holds.get(o["asset_id"]), s, horizon_years)
                     if o["action"] in DEVELOPMENT else None for o in options] for s in scenarios]
    n, count = len(options), len(scenarios)
    eta = n * (count + 1)
    size = eta + 1 + count
    c, lower, upper, integer = np.zeros(size), np.zeros(size), np.ones(size), np.zeros(size)
    integer[:eta] = 1
    upper[eta:] = np.inf  # eta is nonnegative: positive-part portfolio losses only.
    c[eta], c[eta + 1:] = cvar_penalty, cvar_penalty * probabilities / (1 - cvar_alpha)
    constraints = []

    def add(row, bound, lb=-np.inf):
        constraints.append(LinearConstraint(row, lb, bound))

    def scenario_coefficients(index, values):
        row = np.zeros(size)
        for j in range(n):
            cancelled = cancellation[index][j]
            fallback = values(cancelled) if cancelled is not None else 0.
            row[j] = fallback
            row[n + index * n + j] = values(execution[index][j]) - fallback
        return row

    for aid in sorted(asset_ids):
        row = np.zeros(size)
        row[:n] = [o["asset_id"] == aid for o in options]
        add(row, 1, 1)
    total_noi = sum(float(a.get("base_noi_m", 0) or 0) for a in asset_actions)
    development_limit = math.floor(len(asset_ids) * max_development_share + 1e-12)
    row = np.zeros(size)
    row[:n] = [o["action"] in DEVELOPMENT for o in options]
    add(row, development_limit)
    for s in range(count):
        for j, o in enumerate(options):
            execute_index = n + s * n + j
            row = np.zeros(size)
            row[execute_index], row[j] = 1, -1
            add(row, 0, 0 if cancellation[s][j] is None else -np.inf)
            if not execution[s][j]["completes_within_horizon"]:
                upper[execute_index] = 0
        cumulative = np.zeros(size)
        for year in range(horizon_years):
            cash = scenario_coefficients(s, lambda o: o["capex_schedule_m"][year] - o["receipt_schedule_m"][year])
            add(cash, annual[year])
            cumulative += cash
            add(cumulative.copy(), total_capital_budget_m - minimum_liquidity_m)
            add(scenario_coefficients(s, lambda o: o["active_projects"][year]), max_concurrent_projects)
            add(scenario_coefficients(s, lambda o: o["resource_schedule"][year]), capacity[year])
            add(scenario_coefficients(s, lambda o: o["lost_noi_m"][year]), total_noi * (1 - minimum_noi_ratio))
        payoff = scenario_coefficients(s, lambda o: o["expected_npv_m"])
        c -= probabilities[s] * payoff
        loss = -payoff
        loss[eta] = loss[eta + 1 + s] = -1
        add(loss, 0)
    total_value = sum(finite(a.get("current_value_m", 0), "current_value_m") for a in asset_actions)
    leverage_limit = (total_value if total_value else total_capital_budget_m) * max_leverage
    row = np.zeros(size)
    row[:n] = [sum(o["capex_schedule_m"]) * .6 for o in options]
    add(row, leverage_limit)
    for field, limits in concentration_limits.items():
        for value, limit in limits.items():
            row = np.zeros(size)
            row[:n] = [o.get(field) == value and o["action"] in DEVELOPMENT for o in options]
            add(row, limit)
    # Dependencies apply to every start option and to actual recourse execution.
    for dependency in dependencies:
        for j, child in enumerate(options):
            if (child["asset_id"], child["action"]) != (dependency["asset_id"], dependency["action"]):
                continue
            row = np.zeros(size)
            row[j] = 1
            for k, parent in enumerate(options):
                if (parent["asset_id"], parent["action"]) == (dependency["requires_asset_id"], dependency["requires_action"]) and _completion_year(parent) <= child["start_year"] - 1:
                    row[k] -= 1
            add(row, 0)
            for s in range(count):
                row = np.zeros(size)
                row[n + s * n + j] = 1
                for k, parent in enumerate(execution[s]):
                    if (parent["asset_id"], parent["action"]) == (dependency["requires_asset_id"], dependency["requires_action"]) and _completion_year(parent) <= execution[s][j]["start_year"] - 1:
                        row[n + s * n + k] -= 1
                add(row, 0)
    result = milp(c, integrality=integer, bounds=Bounds(lower, upper), constraints=constraints,
                  options={"time_limit": 90, "mip_rel_gap": .005})
    if not result.success:
        return {"feasible": False, "status": result.message, "selections": [], "first_stage": []}
    indices = [j for j in range(n) if result.x[j] > .5]
    selected = [options[j] for j in indices]
    recourse, all_checks, outcomes = [], [], []
    for s, scenario in enumerate(scenarios):
        executed, cancelled, realised = [], [], []
        for j in indices:
            if result.x[n + s * n + j] > .5:
                row = execution[s][j]
                executed.append(public_selection(row))
            else:
                row = cancellation[s][j]
                cancelled.append({"asset_id": options[j]["asset_id"], "action": options[j]["action"],
                                  "fallback_action": "Hold", "cancellation_cost_m": options[j]["cancel_cost_m"],
                                  "fallback_expected_npv_m": row["expected_npv_m"]})
            realised.append(row)
        audit, plan = audit_plan(realised, asset_actions, horizon_years, total_capital_budget_m,
                                minimum_liquidity_m, annual, max_concurrent_projects, minimum_noi_ratio,
                                contractor_capacity=capacity)
        scenario_checks = audit["checks"]
        for row in realised:
            scenario_checks.append(check(f"completion:{row['asset_id']}", int(not row["completes_within_horizon"]), 0))
        for d in dependencies:
            for child in executed:
                if (child["asset_id"], child["action"]) == (d["asset_id"], d["action"]):
                    parents = [p for p in executed if (p["asset_id"], p["action"]) == (d["requires_asset_id"], d["requires_action"]) and _completion_year(p) <= child["start_year"] - 1]
                    scenario_checks.append(check(f"dependency:{child['asset_id']}", len(parents), lower=1))
        audit = summarise_audit(scenario_checks)
        all_checks.extend({**item, "constraint": scenario["name"] + ":" + item["constraint"]} for item in audit["checks"])
        outcome = sum(o["expected_npv_m"] for o in realised)
        outcomes.append(outcome)
        recourse.append({"scenario": scenario["name"], "probability": scenario["probability"],
                        "executed": executed, "cancelled": cancelled,
                        "selections": [public_selection(o) for o in realised],
                        "portfolio_npv_m": outcome, "portfolio_positive_loss_m": max(0, -outcome),
                        "annual_plan": plan, "constraint_audit": audit})
    all_checks.append(check("first_stage:leverage_proxy", sum(sum(o["capex_schedule_m"]) * .6 for o in selected), leverage_limit))
    all_checks.append(check("first_stage:development_action_count", sum(o["action"] in DEVELOPMENT for o in selected), development_limit))
    for field, limits in concentration_limits.items():
        for value, limit in limits.items():
            all_checks.append(check(f"first_stage:concentration:{field}:{value}", sum(o.get(field) == value and o["action"] in DEVELOPMENT for o in selected), limit))
    for d in dependencies:
        for child in selected:
            if (child["asset_id"], child["action"]) == (d["asset_id"], d["action"]):
                parents = [p for p in selected if (p["asset_id"], p["action"]) == (d["requires_asset_id"], d["requires_action"]) and _completion_year(p) <= child["start_year"] - 1]
                all_checks.append(check(f"first_stage:dependency:{child['asset_id']}", len(parents), lower=1))
    audit = summarise_audit(all_checks)
    expected = float(np.dot(probabilities, outcomes))
    risk = weighted_loss_cvar(outcomes, probabilities, cvar_alpha)
    objective = expected - cvar_penalty * risk
    first_stage = [public_selection(o) for o in selected]
    for selection in first_stage:
        selection["recourse_expected_npv_m"] = sum(s["probability"] * next(r["expected_npv_m"] for r in s["selections"] if r["asset_id"] == selection["asset_id"]) for s in recourse)
    annual_plan = [{"year": year + 1, **{key: sum(s["probability"] * s["annual_plan"][year][key] for s in recourse)
                                       for key in recourse[0]["annual_plan"][year] if key != "year"}}
                   for year in range(horizon_years)]
    return {
        "feasible": audit["passed"], "status": result.message if audit["passed"] else "Independent constraint audit failed",
        "method": "Two-stage stochastic MILP with funded Hold recourse and joint scenario loss CVaR",
        "horizon_years": horizon_years, "first_stage": first_stage, "selections": first_stage,
        "recourse": recourse, "annual_plan": annual_plan, "annual_plan_basis": "probability_weighted_recourse",
        "portfolio_expected_npv_m": expected, "risk_adjusted_objective_m": objective, "objective": objective,
        "portfolio_loss_cvar_m": risk, "portfolio_cvar_95_m": risk if cvar_alpha == .95 else None,
        "cvar_eta": float(result.x[eta]), "cvar_alpha": cvar_alpha,
        "risk_measure": "joint_scenario_positive_part_loss_cvar",
        "risk_interpretation": "CVaR of aggregate positive-part NPV loss across the supplied joint scenarios; coarse scenario assumptions are not calibrated loss probabilities.",
        "timing_interpretation": TIMING_INTERPRETATION,
        "recourse_interpretation": "Scenarios resolve before construction. A cancellation retains the explicit Hold economics and funding plus a decision-year cancellation fee. Missing Hold disables cancellation. Scenario delays shift capex, income loss, contractor load and completion; uncompleted projects cannot execute.",
        "leverage_interpretation": "60% of committed gross capex versus supplied portfolio value is a financing proxy, not balance-sheet loan-to-value or a covenant test.",
        "constraint_audit": audit, "constraint_violations": audit["violation_count"],
        "scenario_assumptions": scenarios,
        "constraints": {"horizon_years": horizon_years, "total_capital_budget_m": total_capital_budget_m,
                        "minimum_liquidity_m": minimum_liquidity_m, "annual_capital_budgets": annual,
                        "max_concurrent_projects": max_concurrent_projects, "contractor_capacity": capacity,
                        "minimum_noi_ratio": minimum_noi_ratio, "cvar_alpha": cvar_alpha, "cvar_penalty": cvar_penalty,
                        "max_leverage": max_leverage, "discount_rate": discount_rate,
                        "max_development_share": max_development_share, "maximum_development_actions": development_limit,
                        "cancellation_cost_rate": cancellation_cost_rate},
    }
