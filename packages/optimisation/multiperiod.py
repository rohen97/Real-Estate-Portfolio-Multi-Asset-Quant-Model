"""One action per asset, fully funded schedules, and optional joint scenario risk."""
from __future__ import annotations

import math
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from packages.optimisation.common import (
    DEVELOPMENT, DISRUPTION, TIMING_INTERPRETATION, audit_plan, build_options,
    public_selection, validate_inputs, weighted_loss_cvar,
)


def optimise_multi_period(asset_actions: list[dict], horizon_years=5, total_capital_budget_m=500,
                          annual_capital_budgets=None, minimum_liquidity_m=50, max_concurrent_projects=8,
                          max_development_share=.45, minimum_noi_ratio=.7, cvar_penalty=.3,
                          discount_rate=.078, scenario_probabilities=None, cvar_alpha=.95):
    annual = validate_inputs(asset_actions, horizon_years, total_capital_budget_m, minimum_liquidity_m,
                             annual_capital_budgets, max_concurrent_projects, minimum_noi_ratio, cvar_penalty)
    if not 0 <= max_development_share <= 1 or not 0 < cvar_alpha < 1:
        raise ValueError("development share must be in [0,1] and cvar_alpha in (0,1)")
    options = build_options(asset_actions, horizon_years, discount_rate)
    asset_ids = {a["asset_id"] for a in asset_actions}
    if not options or asset_ids - {o["asset_id"] for o in options}:
        return {"feasible": False, "status": "An asset has no action completing within the horizon", "selections": [], "horizon_years": horizon_years}
    n = len(options)
    has_scenarios = ["scenario_npvs_m" in o for o in options]
    if any(has_scenarios) and not all(has_scenarios):
        raise ValueError("Joint risk requires aligned scenario_npvs_m on every feasible action")
    joint = all(has_scenarios)
    if joint and len({len(o["scenario_npvs_m"]) for o in options}) != 1:
        raise ValueError("All scenario_npvs_m arrays must have identical lengths and aligned indices")
    scenario_matrix = np.array([o["scenario_npvs_m"] for o in options], dtype=float) if joint else None
    scenario_count = scenario_matrix.shape[1] if joint else 0
    probabilities = np.full(scenario_count, 1 / scenario_count) if joint else np.array([])
    if scenario_probabilities is not None:
        probabilities = np.asarray(scenario_probabilities, dtype=float)
        if not joint or probabilities.ndim != 1 or len(probabilities) != scenario_count or not np.isfinite(probabilities).all() or np.any(probabilities < 0) or not np.isclose(probabilities.sum(), 1):
            raise ValueError("scenario_probabilities must be finite, nonnegative and sum to one")
    # eta >= 0 gives CVaR of max(0, -portfolio NPV), never a reward for safe gains.
    size = n + 1 + scenario_count if joint else n
    c = np.zeros(size)
    c[:n] = [-o["expected_npv_m"] + (0 if joint else cvar_penalty * max(0, o["cvar_95_m"])) for o in options]
    lower, upper = np.zeros(size), np.ones(size)
    integer = np.zeros(size)
    integer[:n] = 1
    if joint:
        upper[n:] = np.inf
        c[n], c[n + 1:] = cvar_penalty, cvar_penalty * probabilities / (1 - cvar_alpha)
    constraints = []

    def add(values, bound, lb=-np.inf):
        row = np.zeros(size)
        row[:n] = values
        constraints.append(LinearConstraint(row, lb, bound))

    for aid in sorted(asset_ids):
        add([o["asset_id"] == aid for o in options], 1, 1)
    cumulative = np.zeros(n)
    total_noi = sum(float(a.get("base_noi_m", 0) or 0) for a in asset_actions)
    for year in range(horizon_years):
        net = np.array([o["capex_schedule_m"][year] - o["receipt_schedule_m"][year] for o in options])
        add(net, annual[year])
        cumulative += net
        add(cumulative.copy(), total_capital_budget_m - minimum_liquidity_m)
        add([o["active_projects"][year] for o in options], max_concurrent_projects)
        add([o["lost_noi_m"][year] for o in options], total_noi * (1 - minimum_noi_ratio))
    development_limit = math.floor(len(asset_ids) * max_development_share + 1e-12)
    add([o["action"] in DEVELOPMENT for o in options], development_limit)
    if joint:
        for scenario in range(scenario_count):
            row = np.zeros(size)
            row[:n] = -scenario_matrix[:, scenario]
            row[n] = row[n + 1 + scenario] = -1
            constraints.append(LinearConstraint(row, -np.inf, 0))
    result = milp(c, integrality=integer, bounds=Bounds(lower, upper), constraints=constraints,
                  options={"time_limit": 60, "mip_rel_gap": .005})
    if not result.success:
        return {"feasible": False, "status": result.message, "selections": [], "horizon_years": horizon_years}
    selected = [o for x, o in zip(result.x[:n], options) if x > .5]
    audit, annual_plan = audit_plan(selected, asset_actions, horizon_years, total_capital_budget_m,
                                    minimum_liquidity_m, annual, max_concurrent_projects,
                                    minimum_noi_ratio, development_limit)
    expected = sum(o["expected_npv_m"] for o in selected)
    input_marginal_risk = sum(max(0, o["cvar_95_m"]) for o in selected)
    marginal_risk = (sum(weighted_loss_cvar(o["scenario_npvs_m"], probabilities, cvar_alpha) for o in selected)
                     if joint else input_marginal_risk)
    scenario_npvs = np.sum([o["scenario_npvs_m"] for o in selected], axis=0) if joint else None
    risk = weighted_loss_cvar(scenario_npvs, probabilities, cvar_alpha) if joint else marginal_risk
    return {
        "feasible": audit["passed"], "status": result.message if audit["passed"] else "Independent constraint audit failed",
        "method": "Multi-period MILP with joint scenario loss CVaR" if joint else "Multi-period MILP with marginal downside-risk penalties",
        "horizon_years": horizon_years, "portfolio_expected_npv_m": round(expected, 6),
        "risk_adjusted_objective_m": round(expected - cvar_penalty * risk, 6),
        "portfolio_cvar_95_m": round(risk, 6) if joint and cvar_alpha == .95 else None,
        "portfolio_loss_cvar_m": round(risk, 6) if joint else None,
        "sum_of_marginal_cvar_95_m": round(marginal_risk, 6),
        "sum_of_input_marginal_cvar_95_m": round(input_marginal_risk, 6),
        "risk_measure": "joint_scenario_positive_part_loss_cvar" if joint else "sum_of_marginal_cvar_penalties",
        "risk_interpretation": ("CVaR of aggregate portfolio positive-part loss across aligned input scenarios; correlations are inherited from supplied joint scenarios."
                                if joint else "Sum of individual nonnegative CVaR penalties; not a joint portfolio CVaR or a diversification estimate."),
        "scenario_count": scenario_count, "scenario_probabilities": probabilities.tolist() if joint else [],
        "portfolio_scenario_npvs_m": scenario_npvs.tolist() if joint else [],
        "timing_interpretation": TIMING_INTERPRETATION,
        "selections": [public_selection(o) for o in selected], "annual_plan": annual_plan,
        "constraint_audit": audit, "constraint_violations": audit["violation_count"],
        "constraints": {"total_capital_budget_m": total_capital_budget_m, "annual_capital_budgets": annual,
                        "minimum_liquidity_m": minimum_liquidity_m, "max_concurrent_projects": max_concurrent_projects,
                        "max_development_share": max_development_share, "maximum_development_actions": development_limit,
                        "minimum_noi_ratio": minimum_noi_ratio, "cvar_penalty": cvar_penalty,
                        "cvar_alpha": cvar_alpha, "discount_rate": discount_rate},
    }
