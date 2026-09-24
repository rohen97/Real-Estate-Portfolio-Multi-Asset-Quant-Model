from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

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
        normal = rng.multivariate_normal(mean, cov, draws)
        tails = rng.multivariate_normal(np.zeros(len(FACTORS)), cov, draws)
        scale = rng.chisquare(5, draws)[:, None]
        return 0.8 * normal + 0.2 * (mean + tails / np.sqrt(scale / 5))
    except (TypeError, ValueError, np.linalg.LinAlgError):
        return None


def _draw_assumption_fallback(draws: int, rng: np.random.Generator) -> np.ndarray:
    normal = rng.multivariate_normal(np.zeros(6), CORRELATION, draws)
    tails = rng.standard_t(5, (draws, 6)) / np.sqrt(5 / 3)
    z = 0.7 * normal + 0.3 * tails
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


def simulate_actions(action_values: list[dict], draws: int = 5000, seed: int = 20260922) -> list[dict]:
    factors = factor_scenarios(draws, seed)
    results = []
    for index, action in enumerate(action_values):
        rng = np.random.default_rng(seed + 100 + index)
        base = action["incremental_npv_m"]
        development = 1 if action["action"] in ("Repurpose", "Redevelop") else 0.35 if action["action"] == "Retrofit" else 0.1
        shock = (
            (factors[:, 0] - 0.025) * 180 * (0.5 + development)
            + (factors[:, 1] - 0.07) * -90
            + (factors[:, 2] - 0.0475) * -420 * (0.4 + development)
            + (factors[:, 3] - 0.04) * -80 * development
            + (factors[:, 4] - 0.035) * -110 * development
            + (factors[:, 5] - 24) * -0.12 * development
            + rng.normal(0, 2 + development * 3, draws)
        )
        values = base + shock
        loss = -values
        value_at_risk = np.quantile(loss, 0.95)
        results.append(
            {
                **action,
                "expected_npv_m": round(float(values.mean()), 2),
                "p10_npv_m": round(float(np.quantile(values, 0.1)), 2),
                "p50_npv_m": round(float(np.quantile(values, 0.5)), 2),
                "p90_npv_m": round(float(np.quantile(values, 0.9)), 2),
                "probability_of_loss": round(float((values < 0).mean()), 4),
                "var_95_m": round(float(value_at_risk), 2),
                "cvar_95_m": round(float(loss[loss >= value_at_risk].mean()), 2),
                "scenario_seed": seed,
                "draws": draws,
            }
        )
    return results


def scenario_covariance() -> dict:
    payload = _calibration_payload()
    if payload:
        covariance = payload.get("covariance", {})
        correlation = covariance.get("correlation")
        if correlation:
            return {
                "factors": FACTORS,
                "correlation": correlation,
                "description": "Calibrated Ledoit-Wolf correlation matrix",
                "status": "calibrated",
                "version": payload.get("version"),
                "synthetic_training": payload.get("synthetic_training", False),
                "regime_artifact_available": _resolve_regime_artifact(payload) is not None,
            }
    return {
        "factors": FACTORS,
        "correlation": CORRELATION.tolist(),
        "description": "Fallback correlation assumptions for rent growth, vacancy, cap rate, interest rate, cost inflation and approval delay",
        "status": "assumption_fallback",
        "version": None,
        "synthetic_training": False,
        "regime_artifact_available": False,
    }


def action_scenario_samples(action_values: list[dict], draws: int = 600, seed: int = 20260922) -> dict:
    factors = factor_scenarios(draws, seed)
    output = {}
    for index, action in enumerate(action_values):
        rng = np.random.default_rng(seed + 100 + index)
        base = float(action.get("incremental_npv_m", action.get("expected_npv_m", 0)))
        development = 1 if action["action"] in ("Repurpose", "Redevelop") else 0.35 if action["action"] == "Retrofit" else 0.1
        shock = (
            (factors[:, 0] - 0.025) * 180 * (0.5 + development)
            + (factors[:, 1] - 0.07) * -90
            + (factors[:, 2] - 0.0475) * -420 * (0.4 + development)
            + (factors[:, 3] - 0.04) * -80 * development
            + (factors[:, 4] - 0.035) * -110 * development
            + (factors[:, 5] - 24) * -0.12 * development
            + rng.normal(0, 2 + development * 3, draws)
        )
        output[action["action"]] = np.round(base + shock, 3).tolist()
    return {"seed": seed, "draws": draws, "samples": output}
