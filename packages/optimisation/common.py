"""Shared scheduling conventions and an audit independent of the solver matrix."""
from __future__ import annotations

import math
from collections import Counter
import numpy as np

DEVELOPMENT = {"Retrofit", "Repurpose", "Redevelop"}
DISRUPTION = {"Hold": 0.0, "Retrofit": .12, "Repurpose": .35, "Redevelop": .8, "Sell": 1.0}
RESOURCE_UNITS = {"Hold": 0, "Retrofit": 1, "Repurpose": 2, "Redevelop": 3, "Sell": 0}


def finite(value, name):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def validate_inputs(assets, horizon, budget, reserve, annual, concurrency, noi_ratio, penalty):
    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon_years must be a positive integer")
    if not assets or len({a["asset_id"] for a in assets}) != len(assets):
        raise ValueError("Provide at least one asset, with unique asset_id values")
    for name, value in (("total_capital_budget_m", budget), ("minimum_liquidity_m", reserve),
                        ("max_concurrent_projects", concurrency), ("cvar_penalty", penalty)):
        if finite(value, name) < 0:
            raise ValueError(f"{name} must be nonnegative")
    if not 0 <= finite(noi_ratio, "minimum_noi_ratio") <= 1:
        raise ValueError("minimum_noi_ratio must be between zero and one")
    annual = [budget / horizon] * horizon if annual is None else list(annual)
    if len(annual) != horizon or any(finite(x, "annual budget") < 0 for x in annual):
        raise ValueError("annual_capital_budgets must contain one nonnegative amount per year")
    for asset in assets:
        if not asset.get("actions"):
            raise ValueError(f"Asset {asset['asset_id']} has no actions")
        if len({a["action"] for a in asset["actions"]}) != len(asset["actions"]):
            raise ValueError(f"Asset {asset['asset_id']} has duplicate action names")
        if finite(asset.get("base_noi_m", 0) or 0, "base_noi_m") < 0:
            raise ValueError("base_noi_m must be nonnegative")
    return annual


def build_options(assets, horizon, discount_rate):
    """NPV is valued at action start; pre-start passive baseline adds zero.

    Cash budgets are undiscounted. Annual buckets begin with decision year 1.
    Whole projects (including sale settlement) must fit inside the horizon.
    """
    options = []
    for asset in assets:
        for action in asset["actions"]:
            name = action["action"]
            if name not in DISRUPTION:
                raise ValueError(f"Unsupported action: {name}")
            raw_duration = finite(action.get("execution_years", 1), "execution_years")
            if raw_duration < 0 or (raw_duration == 0 and name in DEVELOPMENT):
                raise ValueError("execution_years must be nonnegative and positive for development")
            duration = max(1, math.ceil(raw_duration))
            raw_delay = finite(action.get("sale_delay_years", 0), "sale_delay_years")
            if raw_delay < 0:
                raise ValueError("sale_delay_years must be nonnegative")
            sale_delay = math.ceil(raw_delay)
            rate = finite(action.get("discount_rate", asset.get("discount_rate", discount_rate)), "discount_rate")
            if rate < 0:
                raise ValueError("discount_rate must be nonnegative")
            capex = finite(action.get("capex_m", 0), "capex_m")
            if capex < 0 and name != "Sell":
                raise ValueError("Only Sell may encode negative capex as sale receipts")
            if capex > 0 and name == "Sell":
                raise ValueError("Sell capex must be nonpositive and encode net sale receipts")
            npv = finite(action.get("expected_npv_m", 0), "expected_npv_m")
            risk = finite(action.get("cvar_95_m", 0), "cvar_95_m")
            starts = [0] if name in ("Hold", "Sell") else range(max(0, horizon - duration + 1))
            for start in starts:
                if (name == "Sell" and start + sale_delay >= horizon) or (name != "Sell" and start + duration > horizon):
                    continue
                factor = (1 + rate) ** -(start + (sale_delay if name == "Sell" else 0))
                spend, receipts, lost_noi, active, resource = ([0.] * horizon for _ in range(5))
                base_noi = float(asset.get("base_noi_m", 0) or 0)
                if name == "Sell":
                    settlement = start + sale_delay
                    receipts[settlement] = max(0, -capex)
                    lost_noi[settlement:] = [base_noi] * (horizon - settlement)
                else:
                    for year in range(start, start + duration):
                        spend[year] = max(0, capex) / duration
                        lost_noi[year] = base_noi * DISRUPTION[name]
                        active[year] = int(name in DEVELOPMENT)
                        resource[year] = RESOURCE_UNITS[name]
                row = {
                    "asset_id": asset["asset_id"], "asset_name": asset.get("name", asset["asset_id"]),
                    "segment": asset.get("segment", "Unknown"), "planning_area": asset.get("planning_area", "Unknown"),
                    "base_noi_m": base_noi, "action": name, "start_year": start + 1,
                    "duration_years": duration, "sale_delay_years": sale_delay,
                    "discount_rate": rate, "discount_factor": factor,
                    "undiscounted_expected_npv_m": npv, "expected_npv_m": npv * factor,
                    "cvar_95_m": risk * factor,
                    "probability_of_loss": float(action.get("probability_of_loss", 0)),
                    "capex_schedule_m": spend, "receipt_schedule_m": receipts,
                    "capex_m": sum(spend) - sum(receipts), "lost_noi_m": lost_noi,
                    "active_projects": active, "resource_schedule": resource,
                }
                if "scenario_npvs_m" in action:
                    values = np.asarray(action["scenario_npvs_m"], dtype=float)
                    if values.ndim != 1 or values.size == 0 or not np.isfinite(values).all():
                        raise ValueError("scenario_npvs_m must be a nonempty finite one-dimensional array")
                    row["scenario_npvs_m"] = (values * factor).tolist()
                options.append(row)
    return options


def weighted_loss_cvar(npvs, probabilities, alpha=.95):
    """Exact finite-distribution CVaR of positive-part loss, with tail splitting."""
    losses = np.maximum(0, -np.asarray(npvs, dtype=float))
    tail, integral = 1 - alpha, 0.0
    for index in np.argsort(losses)[::-1]:
        weight = min(tail, float(probabilities[index]))
        integral += weight * losses[index]
        tail -= weight
        if tail <= 1e-12:
            break
    return float(integral / (1 - alpha))


def check(name, lhs, upper=None, lower=None, tolerance=1e-6):
    violation = max(0., (lower - lhs) if lower is not None else 0.,
                    (lhs - upper) if upper is not None else 0.)
    return {"constraint": name, "lhs": float(lhs), "lower": lower, "upper": upper,
            "violation": float(violation), "passed": violation <= tolerance}


def summarise_audit(checks, tolerance=1e-6):
    return {"passed": all(c["passed"] for c in checks), "tolerance": tolerance,
            "violation_count": sum(not c["passed"] for c in checks),
            "max_violation": max((c["violation"] for c in checks), default=0.), "checks": checks}


def audit_plan(selections, assets, horizon, budget, reserve, annual, concurrency,
               noi_ratio, development_limit=None, contractor_capacity=None):
    """Recompute residuals from selected schedules, never the solver matrix.

    This audits modelled constraints, not correctness of underwriting inputs.
    """
    counts = Counter(row["asset_id"] for row in selections)
    checks = [check(f"one_action:{a['asset_id']}", counts[a["asset_id"]], 1, 1) for a in assets]
    known = {a["asset_id"] for a in assets}
    checks.append(check("unknown_asset_selections", sum(row["asset_id"] not in known for row in selections), 0))
    total_noi = sum(float(a.get("base_noi_m", 0) or 0) for a in assets)
    cumulative = 0.
    annual_plan = []
    for year in range(horizon):
        spend = sum(row["capex_schedule_m"][year] for row in selections)
        receipts = sum(row["receipt_schedule_m"][year] for row in selections)
        noi = sum(row["lost_noi_m"][year] for row in selections)
        active = sum(row["active_projects"][year] for row in selections)
        resource = sum(row["resource_schedule"][year] for row in selections)
        net = spend - receipts
        cumulative += net
        checks.extend((check(f"annual_capital:year_{year + 1}", net, annual[year]),
                       check(f"liquidity:year_{year + 1}", cumulative, budget - reserve),
                       check(f"concurrency:year_{year + 1}", active, concurrency),
                       check(f"noi_continuity:year_{year + 1}", noi, total_noi * (1 - noi_ratio))))
        if contractor_capacity is not None:
            checks.append(check(f"contractor_capacity:year_{year + 1}", resource, contractor_capacity[year]))
        annual_plan.append({"year": year + 1, "capex_m": round(spend, 6),
                            "capital_released_m": round(receipts, 6), "net_funding_m": round(net, 6),
                            "cumulative_net_funding_m": round(cumulative, 6),
                            "remaining_liquidity_m": round(budget - cumulative, 6),
                            "noi_disruption_m": round(noi, 6), "active_projects": int(active),
                            "contractor_units": resource})
    if development_limit is not None:
        checks.append(check("development_action_count", sum(row["action"] in DEVELOPMENT for row in selections), development_limit))
    return summarise_audit(checks), annual_plan


def public_selection(row):
    return {key: value for key, value in row.items() if key != "scenario_npvs_m"}


TIMING_INTERPRETATION = (
    "Action NPVs are incremental to the supplied passive baseline at action start and discounted "
    "to decision time; passive pre-start carry contributes zero incremental NPV. Aggregate NPV "
    "discounting is an approximation, not a cash-flow re-underwriting of deferred operations. "
    "Annual budgets use undiscounted net spending; sale cash becomes available only at settlement."
)
