from copy import deepcopy

import numpy as np
import pytest

from packages.synthetic.dashboard import (
    ENVIRONMENTS, OPTIMISATION_DRAWS, PREDICTIVE_DRAWS, _optimisation_payload,
    _scenario_noise, _simulated_total, evaluate_twin,
)
from packages.synthetic.semisynthetic import generate_twin, segment_group
from packages.optimisation.common import weighted_loss_cvar
from scripts.create_public_demo import build_demo_assets, forecast_diagnostics, zoning_fixtures


@pytest.mark.parametrize("label,expected", [
    ("Office", "Commercial"), ("Logistics", "Industrial"), ("Warehouse", "Industrial"),
    ("Business park", "Industrial"), ("Industrial", "Industrial"),
    ("Hospitality", "Hotel"), ("Mixed use", "Mixed Use"), ("Mixed-use", "Mixed Use"),
    ("Residential", "Residential"), ("Serviced residence", "Serviced Residence"),
    ("Self-storage", "Self-Storage"), ("Unrecognised", "Other"), ("", "Other"),
])
def test_segment_mapping_does_not_silently_default_to_residential(label, expected):
    assert segment_group({"segments": [label]}) == expected


def test_fictional_and_unverified_context_cannot_become_verified_anchors():
    asset = build_demo_assets()[0]
    twin = generate_twin(asset)
    assert twin["context_status"] == "synthetic_fixture"
    assert twin["field_provenance"]["address"]["status"] == "synthetic_fixture"
    assert twin["completeness"]["verified_context_pct"] == 0
    assert twin["completeness"]["real_context_fields"] == 0
    assert 0 <= twin["completeness"]["context_completeness_pct"] <= 1
    asset["synthetic"] = False
    asset["ura_zoning"]["match_method"] = "supplied_match"
    assert generate_twin(asset)["context_status"] == "supplied_unverified"


def test_predictive_recommendations_are_independent_of_hidden_simulation_truth():
    twin = generate_twin(build_demo_assets()[1])
    altered = deepcopy(twin)
    altered["latent_simulation_truth"] = {key: 0.0 for key in altered["latent_simulation_truth"]}
    before, after = evaluate_twin(twin, "base"), evaluate_twin(altered, "base")
    assert before["recommended_action"] == after["recommended_action"]
    for left, right in zip(before["actions"], after["actions"]):
        for key in ("expected_npv_m", "p10_npv_m", "p50_npv_m", "p90_npv_m", "cvar_95_m", "probability_of_loss", "scenario_npvs_m"):
            assert left[key] == right[key]
    assert any(left["simulated_realised_npv_m"] != right["simulated_realised_npv_m"] for left, right in zip(before["actions"], after["actions"]))


def test_common_scenarios_are_reproducible_correlated_and_separate_from_evaluation():
    first, second = [generate_twin(asset) for asset in build_demo_assets()[:2]]
    noise1, approvals = _scenario_noise(first, "Redevelop", PREDICTIVE_DRAWS)
    noise2, _ = _scenario_noise(second, "Redevelop", PREDICTIVE_DRAWS)
    repeat, _ = _scenario_noise(first, "Redevelop", PREDICTIVE_DRAWS)
    held_out, held_out_approvals = _scenario_noise(first, "Redevelop", PREDICTIVE_DRAWS, evaluation=True)
    assert np.array_equal(noise1, repeat)
    assert np.corrcoef(noise1, noise2)[0, 1] > .35
    assert not np.array_equal(noise1, held_out)
    assert not np.array_equal(approvals, held_out_approvals)


def test_empirical_risk_cards_reconcile_to_predictive_rows():
    twin = generate_twin(build_demo_assets()[2])
    result = evaluate_twin(twin, "base")
    assert result == evaluate_twin(twin, "base")
    for action in result["actions"]:
        values = np.array(action["scenario_npvs_m"])
        assert len(values) == PREDICTIVE_DRAWS
        assert action["expected_npv_m"] == pytest.approx(values.mean(), abs=.000051)
        assert action["p10_npv_m"] == pytest.approx(np.quantile(values, .1), abs=.000051)
        losses = -values
        assert action["cvar_95_m"] == pytest.approx(weighted_loss_cvar(values, np.full(len(values), 1 / len(values))), abs=.000051)
        assert action["probability_of_loss"] == pytest.approx(np.mean(values < 0), abs=.0000051)
    payload = _optimisation_payload(twin, result)
    assert payload["base_noi_m"] == result["baseline_noi_m"]
    assert all(len(action["scenario_npvs_m"]) == OPTIMISATION_DRAWS for action in payload["actions"])
    assert all("scenario_npvs_m" not in action for action in _optimisation_payload(twin, result, True)["actions"])


def test_hold_is_zero_incremental_and_environment_changes_cash_funding():
    twin = generate_twin(build_demo_assets()[1])
    cases = {environment: {row["action"]: row for row in evaluate_twin(twin, environment)["actions"]} for environment in ENVIRONMENTS}
    for actions in cases.values():
        hold = actions["Hold"]
        assert hold["expected_npv_m"] == hold["p10_npv_m"] == hold["p90_npv_m"] == hold["cvar_95_m"] == hold["simulated_realised_npv_m"] == 0
        assert hold["baseline_pv_m"] > 0
    assert cases["stress"]["Redevelop"]["capex_m"] == pytest.approx(cases["base"]["Redevelop"]["capex_m"] * 1.18, abs=1e-5)
    assert abs(cases["stress"]["Sell"]["capex_m"]) < abs(cases["base"]["Sell"]["capex_m"])


def test_simulated_comparison_respects_selected_start_year_discount():
    results = {"A": {"actions": [{"action": "Retrofit", "simulated_realised_npv_m": 12.0}]}}
    rows = [{"asset_id": "A", "action": "Retrofit", "discount_factor": .8}]
    assert _simulated_total(results, rows) == 9.6


def test_fixture_metrics_are_calculated_from_displayed_rows():
    rows = [{"actual_noi_m": 1., "point": 1.2, "p10": .9, "p90": 1.3},
            {"actual_noi_m": 2., "point": 1.9, "p10": 1.7, "p90": 1.95}]
    metrics = forecast_diagnostics(rows)
    assert metrics["mae_m"] == pytest.approx(.15)
    assert metrics["bias_m"] == pytest.approx(.05)
    assert metrics["p10_p90_coverage"] == .5
    assert metrics["observations"] == 2
    assert forecast_diagnostics([])["mae_m"] is None


def test_zoning_geojson_carries_fixture_labels_without_legal_or_ml_certainty():
    predictions, geojson = zoning_fixtures(build_demo_assets())
    for prediction, feature in zip(predictions, geojson["features"]):
        properties = feature["properties"]
        assert properties["legal_core"] == prediction["discrepancy"]["legal_core"]
        assert properties["legal_land_use"] == prediction["legal_land_use"]
        assert properties["legal_status"] == "fictional_not_statutory"
        assert properties["status"] == "unverified_fixture"
        assert prediction["prediction"]["trained"] is False
        assert prediction["prediction"]["core"]["abstain"] is True
