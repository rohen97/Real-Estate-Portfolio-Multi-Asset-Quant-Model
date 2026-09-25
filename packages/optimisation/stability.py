"""Sensitivity of optimiser choices to explicit assumption perturbations."""
from __future__ import annotations

import copy
from collections import Counter, defaultdict
import numpy as np

from packages.optimisation.multiperiod import optimise_multi_period


def analyse_stability(asset_actions: list[dict], runs=40, seed=20260924, **optimizer_kwargs):
    if not isinstance(runs, int) or runs < 1:
        raise ValueError("runs must be a positive integer")
    rng = np.random.default_rng(seed)
    baseline = optimise_multi_period(asset_actions, **optimizer_kwargs)
    base = {x["asset_id"]: x["action"] for x in baseline.get("selections", [])}
    frequencies, objectives, expected_npvs, failures = defaultdict(Counter), [], [], []
    for run in range(runs):
        perturbed = copy.deepcopy(asset_actions)
        for asset in perturbed:
            for action in asset["actions"]:
                npv_multiplier = float(rng.normal(1, .06))
                risk_multiplier = float(max(.7, rng.normal(1, .08)))
                cost_multiplier = float(max(.75, rng.normal(1, .08)))
                original_cost = float(action.get("capex_m", 0))
                action["capex_m"] = original_cost * cost_multiplier
                cost_change = action["capex_m"] - original_cost
                action["expected_npv_m"] = float(action.get("expected_npv_m", 0)) * npv_multiplier - cost_change
                action["cvar_95_m"] = float(action.get("cvar_95_m", 0)) * risk_multiplier + cost_change
                if "scenario_npvs_m" in action:
                    action["scenario_npvs_m"] = (np.asarray(action["scenario_npvs_m"], dtype=float) * npv_multiplier - cost_change).tolist()
        result = optimise_multi_period(perturbed, **optimizer_kwargs)
        if not result.get("feasible"):
            failures.append({"run": run + 1, "status": result.get("status", "unknown")})
            continue
        objectives.append(result["risk_adjusted_objective_m"])
        expected_npvs.append(result["portfolio_expected_npv_m"])
        for selection in result["selections"]:
            frequencies[selection["asset_id"]][selection["action"]] += 1
    rows = []
    for asset in asset_actions:
        aid = asset["asset_id"]
        counts = frequencies[aid]
        total = sum(counts.values())
        modal, count = counts.most_common(1)[0] if counts else (None, 0)
        score = count / total if total else None
        rows.append({
            "asset_id": aid, "baseline_action": base.get(aid), "modal_action": modal,
            "robust_action": modal,  # compatibility alias, not a robust feasible portfolio
            "stability_score": round(score, 4) if score is not None else None,
            "baseline_action_frequency": round(counts[base.get(aid)] / total, 4) if total else None,
            "action_frequencies": {key: round(value / total, 4) for key, value in counts.items()},
            "successful_runs": total, "fragile": score < .7 if score is not None else None,
        })

    def summary(values, quantile=None):
        return float(np.quantile(values, quantile) if quantile is not None else np.mean(values)) if values else None

    objective_mean, objective_p10 = summary(objectives), summary(objectives, .1)
    return {
        "runs": runs, "seed": seed, "successful_runs": len(objectives), "failed_runs": len(failures),
        "feasible_run_rate": len(objectives) / runs, "failed_run_details": failures,
        "baseline_feasible": baseline.get("feasible", False), "baseline_status": baseline.get("status"),
        "assets": rows, "fragile_assets": sum(row["fragile"] is True for row in rows),
        "risk_adjusted_objective_mean_m": objective_mean, "risk_adjusted_objective_p10_m": objective_p10,
        "portfolio_expected_npv_mean_m": summary(expected_npvs),
        "portfolio_expected_npv_p10_m": summary(expected_npvs, .1),
        "objective_mean_m": objective_mean, "objective_p10_m": objective_p10,
        "frequency_denominator": "feasible audited perturbation runs only; infeasibility reported separately",
        "method": "Assumption sensitivity around the multi-period optimiser; this is neither forecast coverage nor validation of investment alpha.",
        "interpretation": "Modal actions are reported asset by asset and need not form a jointly feasible portfolio. The legacy robust_action field is an alias for modal_action. Objective summaries use the penalised objective; expected NPV summaries are separate.",
        "perturbation_assumptions": {"npv_multiplier_standard_deviation": .06, "marginal_cvar_multiplier_standard_deviation": .08,
                                     "capex_multiplier_standard_deviation": .08, "fragility_threshold": .7,
                                     "cost_change_treatment": "Capex/receipt changes affect both funding and incremental NPV; joint scenario arrays retain aligned indices."},
    }
