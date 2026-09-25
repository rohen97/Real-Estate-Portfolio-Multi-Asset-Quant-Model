from __future__ import annotations

from collections import Counter
from datetime import date
from math import sqrt
from statistics import mean
from typing import Any

import numpy as np

from packages.actions.real_options import evaluate_actions
from packages.optimisation.multiperiod import optimise_multi_period
from packages.optimisation.common import weighted_loss_cvar
from packages.scenarios.engine import empirical_tail_mean
from packages.synthetic.semisynthetic import GENERATOR_VERSION, stable_seed

DASHBOARD_VERSION = "digital-twin-dashboard-0.4.0"
PREDICTIVE_DRAWS = 2048
OPTIMISATION_DRAWS = 128
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
            "Industrial": -0.06,
            "Mixed Use": -0.07,
            "Other": -0.08,
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
            "Industrial": 0.035,
            "Mixed Use": 0.01,
            "Other": 0.0,
        },
    },
}


def _capacity_option_m(twin: dict[str, Any]) -> float:
    values = twin["underwriting"]
    additional_gfa = max(0, values["approved_gfa_sqm"] - values["current_gfa_sqm"])
    additional_nla = additional_gfa * values["nla_efficiency"]
    gross_value = additional_nla * values["market_value_per_nla_sqm"] / 1_000_000
    cost = additional_gfa * values["construction_cost_per_gfa_sqm"] / 1_000_000
    return round(max(0, gross_value - cost * 1.32) * 0.75, 4)


def _asset_signal_adjustment(twin: dict[str, Any], action: str) -> float:
    """Bounded screening assumptions use observable fields only, never latent truth."""
    value = twin["underwriting"]["valuation_m"]
    scores = twin["legacy_inputs"]
    values = twin["underwriting"]
    if action == "Hold":
        return 0.0
    if action == "Retrofit":
        effect = ((100 - scores["operational"]) / 100 + (100 - scores["sustainability"]) / 100 - 1) * 0.015
        return value * float(np.clip(effect, -0.015, 0.015))
    if action == "Repurpose":
        return value * float(np.clip((0.9 - values["occupancy"]) * 0.1, -0.02, 0.02))
    if action == "Redevelop":
        # Capacity is an unpriced diagnostic until legally and economically verified.
        return value * float(np.clip((values["building_age_years"] - 25) / 1000, -0.02, 0.02))
    return 0.0


def _environment_parameters(twin: dict[str, Any], environment_name: str) -> dict[str, float]:
    """Apply the same scenario to cash funding, sale receipts and valuation."""
    environment = ENVIRONMENTS[environment_name]
    values = twin["underwriting"]
    segment = twin["real_context"]["segment"]
    demand = environment["segment_demand"].get(segment, 0)
    rent_effect = environment["rent_change"] + demand
    cap_rate = float(np.clip(values["cap_rate"] + environment["cap_rate_shift"], 0.02, 0.15))
    return {
        "rent_growth": float(np.clip(0.025 + rent_effect * 0.1, -0.03, 0.08)),
        "terminal_cap_rate": cap_rate,
        "capex_multiplier": environment["cost_multiplier"],
        "approval_multiplier": environment["approval_multiplier"],
        "sale_price_multiplier": float(np.clip((1 + rent_effect) * values["cap_rate"] / cap_rate, 0.35, 1.75)),
    }


def _scenario_noise(twin: dict[str, Any], action: str, count: int, evaluation: bool = False) -> tuple[np.ndarray, np.ndarray]:
    """Common economic/cost draws align all assets; evaluation uses a disjoint seed."""
    tag = "held_out_evaluation" if evaluation else "predictive_risk"
    common = np.random.default_rng(stable_seed(f"{tag}:common", 901)).standard_t(6, (2, count)) / sqrt(1.5)
    asset_rng = np.random.default_rng(stable_seed(f"{tag}:{twin['asset_id']}:approval", 902))
    approval = asset_rng.random(count)
    idiosyncratic = np.random.default_rng(stable_seed(f"{tag}:{twin['asset_id']}:{action}", 903)).standard_t(6, count) / sqrt(1.5)
    cost_loading = -0.35 if action in {"Retrofit", "Repurpose", "Redevelop"} else 0.0
    noise = 0.65 * common[0] + cost_loading * common[1] + sqrt(1 - 0.65**2 - cost_loading**2) * idiosyncratic
    return noise, approval


def _failure_cost_noise(twin: dict[str, Any], action: str, count: int, evaluation: bool = False) -> np.ndarray:
    tag = "held_out_evaluation" if evaluation else "predictive_risk"
    common = np.random.default_rng(stable_seed(f"{tag}:common", 901)).standard_t(6, (2, count))[1] / sqrt(1.5)
    idiosyncratic = np.random.default_rng(stable_seed(f"{tag}:{twin['asset_id']}:{action}:sunk_cost", 904)).standard_t(6, count) / sqrt(1.5)
    return -0.35 * common + sqrt(1 - .35**2) * idiosyncratic


def _simulated_truth_adjustment(twin: dict[str, Any], action: str, environment_name: str) -> float:
    value = twin["underwriting"]["valuation_m"]
    latent = twin["latent_simulation_truth"]
    execution = latent["execution_quality"]
    if action == "Hold":
        effect = 0.0
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
    parameters = _environment_parameters(twin, environment_name)
    rent_level = 1 + environment["rent_change"] + environment["segment_demand"].get(twin["real_context"]["segment"], 0)
    base_actions = evaluate_actions(values["valuation_m"], values["noi_m"] * rent_level, _capacity_option_m(twin), **parameters)
    actions = []
    for base_action in base_actions:
        name = base_action["action"]
        signal = _asset_signal_adjustment(twin, name)
        expected_formula = base_action["incremental_npv_m"] + signal * base_action["success_probability"]
        sigma = 0.0 if name == "Hold" else max(0.15, values["valuation_m"] * ACTION_RISK[name] * environment["volatility_multiplier"])
        noise, approval = _scenario_noise(twin, name, PREDICTIVE_DRAWS)
        evaluation_noise, evaluation_approval = _scenario_noise(twin, name, 1, evaluation=True)
        success = base_action.get("success_incremental_npv_m", base_action["incremental_npv_m"])
        failure = base_action.get("failure_incremental_npv_m", base_action["incremental_npv_m"])
        probability = base_action["success_probability"]
        failure_sigma = max(0., base_action["capex_m"]) * .03 * environment["volatility_multiplier"]
        samples = np.where(approval < probability, success + signal + sigma * noise,
                           failure + failure_sigma * _failure_cost_noise(twin, name, PREDICTIVE_DRAWS))
        evaluation_success = bool(evaluation_approval[0] < probability)
        realised = float(success + signal + sigma * evaluation_noise[0] + _simulated_truth_adjustment(twin, name, environment_name)) if evaluation_success else float(failure + failure_sigma * _failure_cost_noise(twin, name, 1, evaluation=True)[0])
        expected = float(samples.mean())
        p10, p50, p90 = np.quantile(samples, [0.1, 0.5, 0.9])
        losses = -samples
        var95 = np.quantile(losses, 0.95)
        signed_cvar95 = empirical_tail_mean(losses)
        cvar95 = weighted_loss_cvar(samples, np.full(PREDICTIVE_DRAWS, 1 / PREDICTIVE_DRAWS))
        actions.append(
            {
                "action": name,
                "expected_npv_m": round(float(expected), 4),
                "p10_npv_m": round(float(p10), 4),
                "p50_npv_m": round(float(p50), 4),
                "p90_npv_m": round(float(p90), 4),
                "probability_of_loss": round(float(np.mean(samples < 0)), 5),
                "cvar_95_m": round(cvar95, 4),
                "signed_loss_cvar_95_m": round(signed_cvar95, 4),
                "risk_definition": "CVaR of positive-part incremental NPV loss; exact finite 5% tail",
                "formula_expected_npv_m": round(float(expected_formula), 4),
                "sample_count": PREDICTIVE_DRAWS,
                "scenario_npvs_m": samples.tolist(),
                "predictor_source": "observable underwriting and explicit scenario assumptions",
                "status": "uncalibrated_synthetic_simulation",
                "baseline_pv_m": base_action.get("pv_without_m"),
                "capex_m": base_action["capex_m"],
                "execution_years": base_action["execution_years"],
                "success_probability": round(base_action["success_probability"], 4),
                "simulated_realised_npv_m": round(float(realised), 4),
                "interval_contains_realised": bool(p10 <= realised <= p90),
            }
        )
    recommendation = max(actions, key=lambda item: item["expected_npv_m"] - 0.3 * max(0, item["cvar_95_m"]))
    oracle = max(actions, key=lambda item: item["simulated_realised_npv_m"])
    return {
        "environment": environment_name,
        "baseline_noi_m": round(values["noi_m"] * rent_level, 6),
        "scenario_parameters": parameters,
        "evaluation_status": "independent_seed_synthetic_outcome_not_empirical_validation",
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
        # Preserve common scenario indexes while limiting mixed-integer tail variables.
        action["scenario_npvs_m"] = source["scenario_npvs_m"][::PREDICTIVE_DRAWS // OPTIMISATION_DRAWS]
        if use_simulated_truth:
            action["expected_npv_m"] = action["simulated_realised_npv_m"]
            action["cvar_95_m"] = 0
            action["probability_of_loss"] = float(action["simulated_realised_npv_m"] < 0)
            action.pop("scenario_npvs_m")
        actions.append(action)
    return {
        "asset_id": twin["asset_id"],
        "name": twin["name"],
        "base_noi_m": result.get("baseline_noi_m", twin["underwriting"]["noi_m"]),
        "actions": actions,
    }


def _selection_map(optimisation: dict[str, Any]) -> dict[str, str]:
    return {row["asset_id"]: row["action"] for row in optimisation.get("selections", [])}


def _distribution(selection: dict[str, str]) -> dict[str, int]:
    counts = Counter(selection.values())
    return {action: counts.get(action, 0) for action in ACTIONS}


def _simulated_total(results: dict[str, dict[str, Any]], selections: list[dict[str, Any]]) -> float:
    total = 0.0
    for row in selections:
        asset_id, action_name = row["asset_id"], row["action"]
        action = next(item for item in results[asset_id]["actions"] if item["action"] == action_name)
        total += action["simulated_realised_npv_m"] * row.get("discount_factor", 1.0)
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
    simulated_realised = _simulated_total(results, model["selections"])
    oracle_realised = _simulated_total(results, oracle["selections"])
    return {
        "feasible": True,
        "baseline_noi_m": round(sum(result["baseline_noi_m"] for result in results.values()), 6),
        "capital_budget_m": capital_budget,
        "minimum_liquidity_m": minimum_liquidity,
        "portfolio_expected_npv_m": model["portfolio_expected_npv_m"],
        "portfolio_risk_adjusted_objective_m": model["risk_adjusted_objective_m"],
        "portfolio_cvar_95_m": model.get("portfolio_cvar_95_m"),
        "risk_method": model.get("risk_measure", model.get("method")),
        "optimisation_scenario_count": OPTIMISATION_DRAWS,
        "portfolio_simulated_realised_npv_m": simulated_realised,
        "simulation_oracle_npv_m": oracle_realised,
        "portfolio_decision_regret_m": round(max(0, oracle_realised - simulated_realised), 4),
        "capital_required_m": round(sum(max(0, row.get("capex_m", 0)) for row in model["selections"]), 4),
        "capital_released_m": round(sum(max(0, -row.get("capex_m", 0)) for row in model["selections"]), 4),
        "allocation": _distribution(selection),
        "selections": model["selections"],
        "oracle_selections": oracle["selections"],
        "oracle_allocation": _distribution(oracle_selection),
        "annual_plan": model["annual_plan"],
        "constraint_violations": model.get("constraint_violations"),
        "constraint_audit": model.get("constraint_audit", {"passed": None, "status": "not_available"}),
        "oracle_constraint_audit": oracle.get("constraint_audit"),
        "constraints": model.get("constraints"),
        "regret_status": "synthetic_hindsight_comparison_under_same_funding_constraints",
    }


def build_dashboard(twins: list[dict[str, Any]]) -> dict[str, Any]:
    if not twins:
        raise ValueError("At least one eligible twin is required to build a dashboard")
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
                "correct_action_observations": len(twins),
                "mean_decision_regret_m": round(mean(result["decision_regret_m"] for result in results.values()), 4),
                "p10_p90_coverage": round(sum(interval_flags) / len(interval_flags), 4),
                "interval_coverage_observations": len(interval_flags),
                "evaluation_status": "separate_synthetic_sample_not_real_world_accuracy",
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
                "context_status": twin.get("context_status", "supplied_unverified"),
                "context_completeness_pct": twin["completeness"].get("context_completeness_pct", twin["completeness"]["real_context_pct"]),
                "verified_context_pct": twin["completeness"].get("verified_context_pct", 0.0),
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
                        "actions": [{key: value for key, value in action.items() if key != "scenario_npvs_m"} for action in result["actions"]],
                        "scenario_parameters": result["scenario_parameters"],
                        "evaluation_status": result["evaluation_status"],
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
        "methodology": {
            "prediction_inputs": "Observable underwriting only; no latent simulation truth",
            "risk_source": "Assumed shared economic and cost Student-t(6) factors, idiosyncratic shocks, approval branches",
            "predictive_scenario_count": PREDICTIVE_DRAWS,
            "optimisation_scenario_count": OPTIMISATION_DRAWS,
            "evaluation_source": "Separate random seed plus hidden simulation effects; one outcome per action/environment",
            "calibration_status": "assumption_only_not_empirically_calibrated",
            "scenario_bounds": {"terminal_cap_rate": [0.02, 0.15], "rent_growth": [-0.03, 0.08], "sale_price_multiplier": [0.35, 1.75]},
            "tail_bounds": "Student-t outcomes are unbounded and illustrate incremental-NPV model risk; not legal liability bounds",
            "hold_baseline": "Incremental Hold NPV and risk are zero; retained asset value remains in baseline PV",
            "context_coverage": "Populated fields, not verification; legacy real_context_pct is a compatibility alias",
        },
        "portfolio_summary": {
            "assets": len(twins),
            "real_portfolio_anchors": sum(twin.get("context_status") == "verified_source" for twin in twins),
            "fictional_asset_contexts": sum(twin.get("context_status") == "synthetic_fixture" for twin in twins),
            "supplied_unverified_contexts": sum(twin.get("context_status") == "supplied_unverified" for twin in twins),
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
