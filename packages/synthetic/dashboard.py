from __future__ import annotations

from collections import Counter
from datetime import date
from math import erf, sqrt
from statistics import mean
from typing import Any

import numpy as np

from packages.actions.real_options import evaluate_actions
from packages.optimisation.multiperiod import optimise_multi_period
from packages.synthetic.semisynthetic import GENERATOR_VERSION, stable_seed

DASHBOARD_VERSION = "digital-twin-dashboard-0.3.0"
ACTIONS = ["Hold", "Retrofit", "Repurpose", "Redevelop", "Sell"]
ACTION_RISK = {"Hold": 0.025, "Retrofit": 0.065, "Repurpose": 0.09, "Redevelop": 0.13, "Sell": 0.055}

ENVIRONMENTS: dict[str, dict[str, Any]] = {
    "base": {
        "label": "Base conditions",
        "description": "Normal rent, financing, approval and construction conditions.",
        "rent_change": 0.015,
        "cap_rate_shift": 0.0,
        "cost_multiplier": 1.0,
        "approval_multiplier": 1.0,
        "volatility_multiplier": 1.0,
        "segment_demand": {},
    },
    "stress": {
        "label": "Market and cost stress",
        "description": "Rent and occupancy pressure, higher cap rates, construction inflation and slower approvals.",
        "rent_change": -0.12,
        "cap_rate_shift": 0.012,
        "cost_multiplier": 1.18,
        "approval_multiplier": 0.72,
        "volatility_multiplier": 1.4,
        "segment_demand": {
            "Residential": -0.04,
            "Commercial": -0.1,
            "Mall": -0.13,
            "Hotel": -0.09,
            "Serviced Residence": -0.06,
            "Self-Storage": 0.01,
        },
    },
    "structural_change": {
        "label": "Structural demand change",
        "description": "Changing occupier demand, competing supply and selective redevelopment or repurposing opportunities.",
        "rent_change": 0.005,
        "cap_rate_shift": 0.003,
        "cost_multiplier": 1.08,
        "approval_multiplier": 0.86,
        "volatility_multiplier": 1.18,
        "segment_demand": {
            "Residential": 0.06,
            "Commercial": -0.035,
            "Mall": -0.075,
            "Hotel": 0.025,
            "Serviced Residence": 0.055,
            "Self-Storage": 0.045,
        },
    },
}


def _normal_cdf(value: float) -> float:
    return 0.5 * (1 + erf(value / sqrt(2)))


def _capacity_option_m(twin: dict[str, Any]) -> float:
    values = twin["underwriting"]
    additional_gfa = max(0, values["approved_gfa_sqm"] - values["current_gfa_sqm"])
    additional_nla = additional_gfa * values["nla_efficiency"]
    gross_value = additional_nla * values["market_value_per_nla_sqm"] / 1_000_000
    cost = additional_gfa * values["construction_cost_per_gfa_sqm"] / 1_000_000
    return round(max(0, gross_value - cost * 1.32) * 0.75, 4)


def _asset_signal_adjustment(twin: dict[str, Any], action: str) -> float:
    value = twin["underwriting"]["valuation_m"]
    scores = twin["legacy_inputs"]
    latent = twin["latent_simulation_truth"]
    if action == "Hold":
        return value * ((scores["financial"] + scores["market"] - 112) / 100) * 0.05
    if action == "Retrofit":
        return value * (latent["operational_gap"] / 100 * 0.075 + latent["sustainability_gap"] / 100 * 0.035)
    if action == "Repurpose":
        return value * (latent["market_mismatch"] * 0.12 + max(0, 62 - scores["market"]) / 100 * 0.06)
    if action == "Redevelop":
        return value * (latent["redevelopment_score"] / 100 * 0.12) + _capacity_option_m(twin) * 0.55
    return value * (max(0, 48 - scores["financial"]) / 100 * 0.035 + max(0, 42 - scores["market"]) / 100 * 0.018 - 0.09)


def _environment_adjustment(twin: dict[str, Any], action: dict[str, Any], environment_name: str) -> float:
    environment = ENVIRONMENTS[environment_name]
    name = action["action"]
    value = twin["underwriting"]["valuation_m"]
    segment = twin["real_context"]["segment"]
    demand = environment["segment_demand"].get(segment, 0)
    rent_effect = environment["rent_change"] + demand
    cap_rate_effect = environment["cap_rate_shift"]
    cost_penalty = max(0, action["capex_m"]) * (environment["cost_multiplier"] - 1)
    approval_penalty = max(0, action["capex_m"]) * (1 - environment["approval_multiplier"]) * 0.24
    if name == "Hold":
        return value * (rent_effect * 0.32 - cap_rate_effect * 3.2)
    if name == "Retrofit":
        return value * (rent_effect * 0.42 - cap_rate_effect * 2.8) - cost_penalty - approval_penalty * 0.35
    if name == "Repurpose":
        structural_bonus = value * max(0, -demand) * 0.2 if environment_name == "structural_change" else 0
        return value * (rent_effect * 0.52 - cap_rate_effect * 3.5) - cost_penalty - approval_penalty + structural_bonus
    if name == "Redevelop":
        structural_bonus = _capacity_option_m(twin) * 0.3 if environment_name == "structural_change" else 0
        return value * (rent_effect * 0.58 - cap_rate_effect * 4.2) - cost_penalty - approval_penalty + structural_bonus
    return value * (rent_effect * 0.38 - cap_rate_effect * 4.5)


def _simulated_truth_adjustment(twin: dict[str, Any], action: str, environment_name: str) -> float:
    value = twin["underwriting"]["valuation_m"]
    latent = twin["latent_simulation_truth"]
    execution = latent["execution_quality"]
    if action == "Hold":
        effect = (execution - 0.6) * value * 0.02
    elif action == "Retrofit":
        effect = ((latent["operational_gap"] + latent["sustainability_gap"]) / 200 - 0.35) * value * 0.055
    elif action == "Repurpose":
        effect = (latent["market_mismatch"] - 0.4) * value * 0.09 + (execution - 0.6) * value * 0.035
    elif action == "Redevelop":
        effect = (latent["redevelopment_score"] / 100 - 0.5) * value * 0.1 + (execution - 0.6) * value * 0.07
    else:
        effect = (0.55 - execution) * value * 0.025
    if environment_name == "stress" and action in {"Repurpose", "Redevelop"}:
        effect -= (0.7 - execution) * value * 0.08
    return effect


def evaluate_twin(twin: dict[str, Any], environment_name: str) -> dict[str, Any]:
    environment = ENVIRONMENTS[environment_name]
    values = twin["underwriting"]
    base_actions = evaluate_actions(values["valuation_m"], values["noi_m"], _capacity_option_m(twin), terminal_cap_rate=values["cap_rate"])
    rng = np.random.default_rng(stable_seed(twin["asset_id"], stable_seed(environment_name, 71)))
    actions = []
    for base_action in base_actions:
        name = base_action["action"]
        expected = base_action["incremental_npv_m"] + _asset_signal_adjustment(twin, name) + _environment_adjustment(twin, base_action, environment_name)
        sigma = max(0.15, values["valuation_m"] * ACTION_RISK[name] * environment["volatility_multiplier"])
        p10 = expected - 1.2815515655 * sigma
        p90 = expected + 1.2815515655 * sigma
        realised = expected + _simulated_truth_adjustment(twin, name, environment_name) + rng.normal(0, sigma * 0.82)
        actions.append(
            {
                "action": name,
                "expected_npv_m": round(float(expected), 4),
                "p10_npv_m": round(float(p10), 4),
                "p50_npv_m": round(float(expected), 4),
                "p90_npv_m": round(float(p90), 4),
                "probability_of_loss": round(float(_normal_cdf(-expected / sigma)), 5),
                "cvar_95_m": round(float(max(0, -expected + 2.0627128075 * sigma)), 4),
                "capex_m": base_action["capex_m"],
                "execution_years": base_action["execution_years"],
                "success_probability": round(base_action["success_probability"] * environment["approval_multiplier"], 4),
                "simulated_realised_npv_m": round(float(realised), 4),
                "interval_contains_realised": bool(p10 <= realised <= p90),
            }
        )
    recommendation = max(actions, key=lambda item: item["expected_npv_m"] - 0.3 * item["cvar_95_m"])
    oracle = max(actions, key=lambda item: item["simulated_realised_npv_m"])
    return {
        "environment": environment_name,
        "recommended_action": recommendation["action"],
        "simulation_oracle_action": oracle["action"],
        "recommendation_expected_npv_m": recommendation["expected_npv_m"],
        "recommendation_p10_m": recommendation["p10_npv_m"],
        "recommendation_p90_m": recommendation["p90_npv_m"],
        "recommendation_probability_of_loss": recommendation["probability_of_loss"],
        "recommendation_simulated_realised_npv_m": recommendation["simulated_realised_npv_m"],
        "decision_regret_m": round(oracle["simulated_realised_npv_m"] - recommendation["simulated_realised_npv_m"], 4),
        "actions": actions,
    }


def _optimisation_payload(twin: dict[str, Any], result: dict[str, Any], use_simulated_truth: bool = False) -> dict[str, Any]:
    actions = []
    for source in result["actions"]:
        action = dict(source)
        if use_simulated_truth:
            action["expected_npv_m"] = action["simulated_realised_npv_m"]
            action["cvar_95_m"] = 0
            action["probability_of_loss"] = float(action["simulated_realised_npv_m"] < 0)
        actions.append(action)
    return {
        "asset_id": twin["asset_id"],
        "name": twin["name"],
        "base_noi_m": twin["underwriting"]["noi_m"],
        "actions": actions,
    }


def _selection_map(optimisation: dict[str, Any]) -> dict[str, str]:
    return {row["asset_id"]: row["action"] for row in optimisation.get("selections", [])}


def _distribution(selection: dict[str, str]) -> dict[str, int]:
    counts = Counter(selection.values())
    return {action: counts.get(action, 0) for action in ACTIONS}


def _simulated_total(results: dict[str, dict[str, Any]], selection: dict[str, str]) -> float:
    total = 0.0
    for asset_id, action_name in selection.items():
        action = next(item for item in results[asset_id]["actions"] if item["action"] == action_name)
        total += action["simulated_realised_npv_m"]
    return round(total, 4)


def optimise_environment(twins: list[dict[str, Any]], results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    total_value = sum(twin["underwriting"]["valuation_m"] for twin in twins)
    capital_budget = round(max(300, min(2200, total_value * 0.085)), 2)
    minimum_liquidity = round(capital_budget * 0.1, 2)
    max_projects = max(8, int(len(twins) * 0.14))
    arguments = {
        "horizon_years": 5,
        "total_capital_budget_m": capital_budget,
        "minimum_liquidity_m": minimum_liquidity,
        "max_concurrent_projects": max_projects,
        "max_development_share": 0.35,
        "minimum_noi_ratio": 0.7,
    }
    model_assets = [_optimisation_payload(twin, results[twin["asset_id"]]) for twin in twins]
    oracle_assets = [_optimisation_payload(twin, results[twin["asset_id"]], use_simulated_truth=True) for twin in twins]
    model = optimise_multi_period(model_assets, cvar_penalty=0.3, **arguments)
    oracle = optimise_multi_period(oracle_assets, cvar_penalty=0.0, **arguments)
    if not model.get("feasible") or not oracle.get("feasible"):
        return {"feasible": False, "model_status": model.get("status"), "oracle_status": oracle.get("status")}
    selection = _selection_map(model)
    oracle_selection = _selection_map(oracle)
    simulated_realised = _simulated_total(results, selection)
    oracle_realised = _simulated_total(results, oracle_selection)
    return {
        "feasible": True,
        "capital_budget_m": capital_budget,
        "minimum_liquidity_m": minimum_liquidity,
        "portfolio_expected_npv_m": model["portfolio_expected_npv_m"],
        "portfolio_risk_adjusted_objective_m": model["risk_adjusted_objective_m"],
        "portfolio_simulated_realised_npv_m": simulated_realised,
        "simulation_oracle_npv_m": oracle_realised,
        "portfolio_decision_regret_m": round(max(0, oracle_realised - simulated_realised), 4),
        "capital_required_m": round(sum(max(0, row.get("capex_m", 0)) for row in model["selections"]), 4),
        "capital_released_m": round(sum(max(0, -row.get("capex_m", 0)) for row in model["selections"]), 4),
        "allocation": _distribution(selection),
        "annual_plan": model["annual_plan"],
        "constraint_violations": 0,
    }


def build_dashboard(twins: list[dict[str, Any]]) -> dict[str, Any]:
    results_by_asset: dict[str, dict[str, dict[str, Any]]] = {twin["asset_id"]: {} for twin in twins}
    environment_summaries = []
    for environment_name, environment in ENVIRONMENTS.items():
        results = {}
        for twin in twins:
            result = evaluate_twin(twin, environment_name)
            results[twin["asset_id"]] = result
            results_by_asset[twin["asset_id"]][environment_name] = result
        correct = sum(result["recommended_action"] == result["simulation_oracle_action"] for result in results.values())
        interval_flags = [action["interval_contains_realised"] for result in results.values() for action in result["actions"]]
        downside = sum(min(0, result["recommendation_simulated_realised_npv_m"]) for result in results.values())
        recommendation_counts = Counter(result["recommended_action"] for result in results.values())
        environment_summaries.append(
            {
                "id": environment_name,
                "label": environment["label"],
                "description": environment["description"],
                "assumptions": {
                    "rent_change": environment["rent_change"],
                    "cap_rate_shift": environment["cap_rate_shift"],
                    "construction_cost_multiplier": environment["cost_multiplier"],
                    "approval_multiplier": environment["approval_multiplier"],
                },
                "assets": len(twins),
                "recommendation_distribution": {action: recommendation_counts.get(action, 0) for action in ACTIONS},
                "correct_action_rate_vs_simulation": round(correct / len(twins), 4),
                "mean_decision_regret_m": round(mean(result["decision_regret_m"] for result in results.values()), 4),
                "p10_p90_coverage": round(sum(interval_flags) / len(interval_flags), 4),
                "recommendation_downside_m": round(downside, 4),
                "portfolio": optimise_environment(twins, results),
            }
        )
    assets = []
    fragile_assets = 0
    for twin in twins:
        asset_results = results_by_asset[twin["asset_id"]]
        recommendations = [asset_results[name]["recommended_action"] for name in ENVIRONMENTS]
        frequencies = Counter(recommendations)
        robust_action, robust_count = frequencies.most_common(1)[0]
        stability_score = robust_count / len(ENVIRONMENTS)
        fragile = stability_score < 1
        fragile_assets += int(fragile)
        assets.append(
            {
                "asset_id": twin["asset_id"],
                "name": twin["name"],
                "segment": twin["real_context"]["segment"],
                "planning_area": twin["real_context"]["planning_area"],
                "ura_land_use": twin["real_context"]["ura_land_use"],
                "real_context_pct": twin["completeness"]["real_context_pct"],
                "verified_underwriting_pct": twin["completeness"]["verified_underwriting_pct"],
                "valuation_m": twin["underwriting"]["valuation_m"],
                "noi_m": twin["underwriting"]["noi_m"],
                "occupancy": twin["underwriting"]["occupancy"],
                "capacity_gap_sqm": twin["underwriting"]["capacity_gap_sqm"],
                "stability_score": round(stability_score, 4),
                "robust_action": robust_action,
                "fragile": fragile,
                "environments": {
                    name: {
                        "recommended_action": result["recommended_action"],
                        "simulation_oracle_action": result["simulation_oracle_action"],
                        "expected_npv_m": result["recommendation_expected_npv_m"],
                        "p10_m": result["recommendation_p10_m"],
                        "p90_m": result["recommendation_p90_m"],
                        "probability_of_loss": result["recommendation_probability_of_loss"],
                        "decision_regret_m": result["decision_regret_m"],
                        "actions": result["actions"],
                    }
                    for name, result in asset_results.items()
                },
            }
        )
    segment_distribution = Counter(twin["real_context"]["segment"] for twin in twins)
    return {
        "status": "synthetic_software_validation",
        "warning": "Financial and outcome fields are synthetic. The dashboard demonstrates the new model and does not establish real investment performance.",
        "dashboard_version": DASHBOARD_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generated_on": date.today().isoformat(),
        "portfolio_summary": {
            "assets": len(twins),
            "real_portfolio_anchors": len(twins),
            "average_real_context_pct": round(mean(twin["completeness"]["real_context_pct"] for twin in twins), 4),
            "verified_underwriting_pct": 0.0,
            "financial_history_years": 12,
            "environments": len(ENVIRONMENTS),
            "fragile_assets": fragile_assets,
            "segment_distribution": dict(segment_distribution),
        },
        "environments": environment_summaries,
        "assets": assets,
    }
