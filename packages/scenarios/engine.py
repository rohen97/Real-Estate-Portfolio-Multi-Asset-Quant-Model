from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import joblib
import numpy as np
from packages.optimisation.common import weighted_loss_cvar

ROOT = Path(__file__).resolve().parents[2]
FACTORS = [
    "rent_growth",
    "vacancy",
    "cap_rate",
    "interest_rate",
    "cost_inflation",
    "approval_delay",
]
CORRELATION = np.array(
    [
        [1, -0.45, -0.55, -0.2, 0.25, -0.15],
        [-0.45, 1, 0.35, 0.2, 0.1, 0.25],
        [-0.55, 0.35, 1, 0.45, 0.15, 0.25],
        [-0.2, 0.2, 0.45, 1, 0.35, 0.3],
        [0.25, 0.1, 0.15, 0.35, 1, 0.35],
        [-0.15, 0.25, 0.25, 0.3, 0.35, 1],
    ]
)


def _calibration_payload() -> dict | None:
    path = ROOT / "data/calibration/market_scenarios.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_regime_artifact(payload: dict | None) -> Path | None:
    if not payload:
        return None
    artifact = payload.get("regimes", {}).get("artifact")
    if not artifact:
        return None
    path = Path(artifact)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.exists() else None


def _positive_semidefinite(matrix: np.ndarray) -> np.ndarray:
    symmetric = (matrix + matrix.T) / 2
    values, vectors = np.linalg.eigh(symmetric)
    return vectors @ np.diag(np.maximum(values, 1e-12)) @ vectors.T


def _draw_calibrated_regimes(payload: dict, draws: int, rng: np.random.Generator) -> np.ndarray | None:
    artifact_path = _resolve_regime_artifact(payload)
    if artifact_path is None:
        return None
    try:
        artifact = joblib.load(artifact_path)
        model = artifact["model"]
        columns = list(artifact["columns"])
        order = [columns.index(name) for name in FACTORS]
        components = rng.choice(len(model.weights_), size=draws, p=model.weights_)
        samples = np.vstack(
            [rng.multivariate_normal(model.means_[component], model.covariances_[component]) for component in components]
        )
        return samples[:, order]
    except (OSError, KeyError, TypeError, ValueError):
        return None


def _draw_calibrated_covariance(payload: dict, draws: int, rng: np.random.Generator) -> np.ndarray | None:
    covariance = payload.get("covariance", {})
    if covariance.get("status") != "calibrated" or covariance.get("columns") != FACTORS:
        return None
    matrix = covariance.get("ledoit_wolf_covariance")
    means = covariance.get("means")
    if matrix is None or means is None:
        return None
    try:
        cov = _positive_semidefinite(np.asarray(matrix, dtype=float))
        mean = np.asarray(means, dtype=float)
        if cov.shape != (len(FACTORS), len(FACTORS)) or mean.shape != (len(FACTORS),):
            return None
        normal = rng.multivariate_normal(np.zeros(len(FACTORS)), cov, draws)
        tails = rng.multivariate_normal(np.zeros(len(FACTORS)), cov, draws)
        scale = rng.chisquare(5, draws)[:, None]
        return mean + (0.8 * normal + 0.2 * tails / np.sqrt(scale / 3)) / np.sqrt(0.8**2 + 0.2**2)
    except (TypeError, ValueError, np.linalg.LinAlgError):
        return None


def _draw_assumption_fallback(draws: int, rng: np.random.Generator) -> np.ndarray:
    normal = rng.multivariate_normal(np.zeros(6), CORRELATION, draws)
    tails = rng.multivariate_normal(np.zeros(6), CORRELATION, draws) / np.sqrt(rng.chisquare(5, draws)[:, None] / 3)
    z = (0.7 * normal + 0.3 * tails) / np.sqrt(0.7**2 + 0.3**2)
    return np.column_stack(
        [
            0.025 + 0.025 * z[:, 0],
            0.07 + 0.035 * z[:, 1],
            0.0475 + 0.009 * z[:, 2],
            0.04 + 0.012 * z[:, 3],
            0.035 + 0.025 * z[:, 4],
            24 + 10 * z[:, 5],
        ]
    )


def factor_scenarios(draws: int = 5000, seed: int = 20260922) -> np.ndarray:
    if not isinstance(draws, int) or draws < 2:
        raise ValueError("draws must be an integer of at least two")
    rng = np.random.default_rng(seed)
    payload = _calibration_payload()
    levels = _draw_calibrated_regimes(payload, draws, rng) if payload else None
    if levels is None and payload:
        levels = _draw_calibrated_covariance(payload, draws, rng)
    if levels is None:
        levels = _draw_assumption_fallback(draws, rng)
    levels[:, 1] = np.clip(levels[:, 1], 0.01, 0.3)
    levels[:, 2] = np.clip(levels[:, 2], 0.025, 0.1)
    levels[:, 3] = np.clip(levels[:, 3], 0.005, 0.15)
    levels[:, 4] = np.clip(levels[:, 4], -0.03, 0.15)
    levels[:, 5] = np.clip(levels[:, 5], 3, 72)
    return levels


def _action_seed(asset_id: str | None, name: str, seed: int) -> int:
    return int.from_bytes(sha256(f"scenario-v3|{seed}|{asset_id or 'unspecified'}|{name}".encode()).digest()[:4], "big")


def empirical_tail_mean(losses: np.ndarray, alpha: float = .95) -> float:
    """Exact equal-weight upper tail, splitting the boundary observation."""
    ordered = np.sort(np.asarray(losses, dtype=float))[::-1]
    mass = (1 - alpha) * len(ordered)
    whole = int(np.floor(mass + 1e-12))
    fraction = max(0., mass - whole)
    total = ordered[:whole].sum()
    if fraction > 1e-12:
        total += fraction * ordered[whole]
    return float(total / mass)


def _action_samples(action: dict, factors: np.ndarray, seed: int, asset_id: str | None) -> np.ndarray:
    """Size-scaled incremental exposures; passive Hold is the common zero baseline."""
    name = action["action"]
    if name == "Hold":
        return np.zeros(len(factors))
    value = max(0., float(action.get("current_value_m", action.get("pv_without_m", abs(action.get("capex_m", 0))))))
    capex = max(0., float(action.get("capex_m", 0)))
    noi = max(0., float(action.get("base_noi_m", value * .045)))
    duration = max(0., float(action.get("execution_years", 1)))
    base = float(action.get("incremental_npv_m", action.get("expected_npv_m", 0)))
    reference = np.array([action.get("reference_rent_growth", .025), action.get("baseline_vacancy", .07),
                          action.get("reference_cap_rate", .0475), .04, .035, 24.])
    delta = factors - reference
    development = 1. if name in ("Repurpose", "Redevelop") else .35
    if name == "Sell":
        # Sale foregoes future Hold income: higher growth hurts the incremental sale case.
        exposures = np.array([-value * 1.8, value * .55, value * 4., 0., 0., 0.])
        sigma = value * .015
    else:
        exposures = np.array([value * 1.6 * development, -value * .55 * development,
                              -value * 3.5 * development, 0.,
                              -capex * duration, -noi * development / 12])
        sigma = capex * .06
    rng = np.random.default_rng(_action_seed(asset_id, name, seed))
    probability = float(np.clip(action.get("success_probability", 1), 0., 1.))
    success = float(action.get("success_incremental_npv_m", base))
    failure = float(action.get("failure_incremental_npv_m", base))
    approved = rng.random(len(factors)) < probability
    # Failed approval retains Hold income: only sunk-cost uncertainty remains.
    market_shock = np.where(approved, delta @ exposures, -0.55 * capex * duration * delta[:, 4])
    residual_scale = np.where(approved, sigma, capex * .03)
    return np.where(approved, success, failure) + market_shock + rng.standard_t(6, len(factors)) / np.sqrt(1.5) * residual_scale


def simulate_actions(action_values: list[dict], draws: int = 5000, seed: int = 20260922,
                     *, asset_id: str | None = None, common_factor_seed: int | None = None) -> list[dict]:
    factor_seed = seed if common_factor_seed is None else common_factor_seed
    factors = factor_scenarios(draws, factor_seed)
    results = []
    for action in action_values:
        values = np.round(_action_samples(action, factors, seed, asset_id), 6)
        loss = -values
        value_at_risk = float(np.quantile(loss, .95))
        loss_cvar = empirical_tail_mean(loss)
        positive_loss_cvar = weighted_loss_cvar(values, np.full(draws, 1 / draws))
        indices = np.linspace(0, draws - 1, min(128, draws), dtype=int)
        results.append({
            **action, "expected_npv_m": round(float(values.mean()), 6),
            "p10_npv_m": round(float(np.quantile(values, .1)), 6),
            "p50_npv_m": round(float(np.quantile(values, .5)), 6),
            "p90_npv_m": round(float(np.quantile(values, .9)), 6),
            "probability_of_loss": round(float((values < 0).mean()), 6),
            "var_95_m": round(max(0., value_at_risk), 6),
            "cvar_95_m": round(positive_loss_cvar, 6),
            "signed_loss_var_95_m": round(value_at_risk, 6),
            "signed_loss_cvar_95_m": round(loss_cvar, 6),
            "risk_definition": "Displayed VaR/CVaR use positive-part loss=max(0,-incremental NPV); CVaR uses exact 5% tail weights, signed loss-tail statistics retained separately",
            "scenario_samples_m": values.tolist(), "scenario_npvs_m": values[indices].tolist(),
            "scenario_seed": seed, "common_factor_seed": factor_seed, "scenario_asset_id": asset_id,
            "scenario_source": "shared_factor_simulation_with_size_scaled_exposures_and_approval_branches",
            "scenario_calibration_status": "factor_calibration_if_available; action_exposures_are_unvalidated_assumptions",
            "draws": draws, "optimisation_draws": len(indices),
        })
    return results


def scenario_covariance() -> dict:
    payload = _calibration_payload()
    realised = np.corrcoef(factor_scenarios(5000, 20260922), rowvar=False).tolist()
    if payload:
        covariance = payload.get("covariance", {})
        correlation = covariance.get("correlation")
        if correlation:
            return {
                "factors": FACTORS,
                "correlation": realised,
                "input_correlation": correlation,
                "description": "Realised correlation of 5,000 bounded factor draws; source calibration matrix is recorded separately",
                "status": "calibrated",
                "version": payload.get("version"),
                "synthetic_training": payload.get("synthetic_training", False),
                "regime_artifact_available": _resolve_regime_artifact(payload) is not None,
            }
    return {
        "factors": FACTORS,
        "correlation": realised,
        "input_correlation": CORRELATION.tolist(),
        "description": "Realised correlation of 5,000 bounded factor draws under fallback assumptions, not measured market correlation",
        "status": "assumption_fallback",
        "version": None,
        "synthetic_training": False,
        "regime_artifact_available": False,
    }


def action_scenario_samples(action_values: list[dict], draws: int = 600, seed: int = 20260922) -> dict:
    stored = bool(action_values) and all(action.get("scenario_samples_m") is not None for action in action_values)
    if stored:
        output = {action["action"]: action["scenario_samples_m"] for action in action_values}
        counts = {len(values) for values in output.values()}
        if len(counts) != 1:
            raise ValueError("Stored action samples must share a common draw count")
        return {"seed": action_values[0].get("scenario_seed"), "draws": counts.pop(), "samples": output,
                "source": "stored_model_samples", "reconciles_to_reported_metrics": True,
                "common_factor_seed": action_values[0].get("common_factor_seed")}
    generated = simulate_actions(action_values, draws, seed)
    return {"seed": seed, "draws": draws, "samples": {action["action"]: action["scenario_samples_m"] for action in generated},
            "source": "fallback_resimulation_no_stored_samples", "reconciles_to_reported_metrics": False}
