from pathlib import Path
import json
import tempfile

import numpy as np
from shapely.geometry import box, mapping

from packages.actions.detailed_cashflow import DetailedActionInputs, evaluate_detailed_action
from packages.actions.enbloc import EnBlocInputs, evaluate_enbloc
from packages.economics.singapore_costs import buyer_stamp_duty, land_betterment_charge
from packages.governance.review import ReviewLedger
from packages.optimisation.stability import analyse_stability
from packages.optimisation.two_stage import optimise_two_stage
from packages.scenarios import engine as scenario_engine
from packages.scenarios.covariance import calibrate_covariance
from packages.scenarios.regimes import fit_regimes
from packages.zoning.envelope3d import EnvelopeInputs, generate_envelopes
from packages.zoning.viewshed import viewshed


def test_singapore_transaction_costs_and_lbc_gate():
    assert buyer_stamp_duty(3_000_000, 1)["total_sgd"] > 0
    assert land_betterment_charge(1000, None)["status"] == "required"


def test_detailed_development_cashflow():
    inputs = DetailedActionInputs(
        action="Redevelop",
        current_value_m=120,
        current_noi_m=5.8,
        site_area_sqm=8000,
        current_gfa_sqm=16000,
        approved_gfa_sqm=24000,
        nla_efficiency=0.78,
        market_value_per_nla_sqm=12000,
        construction_cost_per_gfa_sqm=4200,
        lbc_rate_per_sqm=1800,
    )
    result = evaluate_detailed_action(inputs)
    assert len(result["monthly_cashflows_m"]) > 50
    assert result["construction_m"] > 0
    assert result["lbc"]["status"] == "calculated"


def test_3d_envelope_options():
    polygon = mapping(box(103.8, 1.3, 103.801, 1.301))
    result = generate_envelopes(EnvelopeInputs(polygon, 3.5, 100, 0.45))
    assert result["preferred"]
    assert result["preferred"]["gross_gfa_sqm"] <= result["legal_gfa_sqm"] + 0.1
    assert result["preferred"]["boxes"]


def test_angular_viewshed():
    result = viewshed(
        30,
        [{"id": "A", "distance_m": 80, "height_m": 100, "width_m": 40, "bearing_deg": 90}],
        current_value_m=100,
    )
    assert result["blocked_azimuth_share"] > 0
    assert result["view_premium_loss_m"] > 0


def test_enbloc_residual_and_consent():
    inputs = EnBlocInputs(200, 10000, 18000, 2.8, 0.78, 14000, 4200, 1800, 70, 120)
    result = evaluate_enbloc(inputs)
    assert "owner_consent_probability" in result
    assert result["gross_development_value_m"] > 0


def test_covariance_calibration():
    rows = [{"a": float(i) + np.sin(i), "b": float(i) * 0.5 + np.cos(i)} for i in range(40)]
    result = calibrate_covariance(rows, ["a", "b"])
    assert result["status"] == "calibrated"
    assert len(result["correlation"]) == 2
    assert len(result["means"]) == 2


def _market_rows(count=60, rent_mean=0.09):
    return [
        {
            "rent_growth": rent_mean + 0.004 * np.sin(index),
            "vacancy": 0.045 + 0.003 * np.cos(index / 2),
            "cap_rate": 0.04 + 0.002 * np.sin(index / 3),
            "interest_rate": 0.03 + 0.002 * np.cos(index / 4),
            "cost_inflation": 0.025 + 0.004 * np.sin(index / 5),
            "approval_delay": 48 + 3 * np.cos(index / 6),
        }
        for index in range(count)
    ]


def test_factor_scenarios_use_calibrated_covariance_before_assumption_fallback(tmp_path, monkeypatch):
    rows = _market_rows()
    covariance = calibrate_covariance(rows, scenario_engine.FACTORS)
    calibration = tmp_path / "data/calibration"
    calibration.mkdir(parents=True)
    (calibration / "market_scenarios.json").write_text(
        json.dumps({"version": "1.0.0", "synthetic_training": False, "covariance": covariance, "regimes": {"status": "blocked"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(scenario_engine, "ROOT", tmp_path)
    scenarios = scenario_engine.factor_scenarios(draws=400, seed=17)
    assert scenarios.shape == (400, 6)
    assert scenarios[:, 0].mean() > 0.07


def test_factor_scenarios_resolve_manifest_versioned_regime_artifact(tmp_path, monkeypatch):
    rows = _market_rows()
    artifact = tmp_path / "models/market-regimes/1.0.0/regimes.joblib"
    regimes = fit_regimes(rows, scenario_engine.FACTORS, artifact, 3)
    regimes["artifact"] = "models/market-regimes/1.0.0/regimes.joblib"
    covariance = calibrate_covariance(rows, scenario_engine.FACTORS)
    calibration = tmp_path / "data/calibration"
    calibration.mkdir(parents=True)
    (calibration / "market_scenarios.json").write_text(
        json.dumps({"version": "1.0.0", "synthetic_training": False, "covariance": covariance, "regimes": regimes}),
        encoding="utf-8",
    )
    monkeypatch.setattr(scenario_engine, "ROOT", tmp_path)
    scenarios = scenario_engine.factor_scenarios(draws=400, seed=19)
    status = scenario_engine.scenario_covariance()
    assert scenarios[:, 0].mean() > 0.07
    assert status["version"] == "1.0.0"
    assert status["regime_artifact_available"] is True


def sample_actions():
    actions = [
        {"action": "Hold", "expected_npv_m": 3, "cvar_95_m": 1, "capex_m": 1, "execution_years": 1, "probability_of_loss": 0.1},
        {"action": "Retrofit", "expected_npv_m": 8, "cvar_95_m": 3, "capex_m": 12, "execution_years": 2, "probability_of_loss": 0.25},
        {"action": "Repurpose", "expected_npv_m": 12, "cvar_95_m": 6, "capex_m": 25, "execution_years": 3, "probability_of_loss": 0.35},
        {"action": "Redevelop", "expected_npv_m": 18, "cvar_95_m": 10, "capex_m": 45, "execution_years": 4, "probability_of_loss": 0.45},
        {"action": "Sell", "expected_npv_m": 6, "cvar_95_m": 2, "capex_m": -90, "execution_years": 1, "probability_of_loss": 0.1},
    ]
    return [
        {
            "asset_id": f"A{index}",
            "name": f"Asset {index}",
            "segment": "Residential",
            "planning_area": "Area 1",
            "base_noi_m": 5,
            "current_value_m": 100,
            "actions": actions,
        }
        for index in range(3)
    ]


def test_two_stage_and_stability():
    assets = sample_actions()
    result = optimise_two_stage(assets, total_capital_budget_m=150, minimum_liquidity_m=10, max_concurrent_projects=2)
    assert result["feasible"]
    assert len(result["first_stage"]) == 3
    assert len(result["recourse"]) == 3
    stability = analyse_stability(assets, runs=4, total_capital_budget_m=150, minimum_liquidity_m=10, max_concurrent_projects=2)
    assert stability["runs"] == 4


def test_independent_review_gate():
    with tempfile.TemporaryDirectory() as directory:
        ledger = ReviewLedger(Path(directory) / "review.sqlite")
        case = ledger.create_case("A1", "Redevelop", "v1", "snap1")
        assert not ledger.status(case)["can_implement"]
        for role in ledger.status(case)["required_roles"]:
            ledger.signoff(case, role, "Reviewer", "approved")
        assert ledger.status(case)["can_implement"]
