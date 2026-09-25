import numpy as np
import pytest

from packages.scenarios.engine import action_scenario_samples, factor_scenarios, simulate_actions
from packages.scenarios import engine


def _actions(scale=1.):
    return [
        {"action": "Hold", "incremental_npv_m": 0., "capex_m": 0., "current_value_m": 100 * scale},
        {"action": "Retrofit", "incremental_npv_m": 5 * scale, "capex_m": 8 * scale,
         "current_value_m": 100 * scale, "base_noi_m": 4.5 * scale, "execution_years": 2,
         "success_probability": .9, "success_incremental_npv_m": 6 * scale, "failure_incremental_npv_m": -4 * scale},
        {"action": "Sell", "incremental_npv_m": 15 * scale, "capex_m": -97.5 * scale,
         "current_value_m": 100 * scale, "base_noi_m": 4.5 * scale, "execution_years": 0},
    ]


def test_stored_samples_reconcile_to_cards_and_ignore_visual_resampling_seed():
    results = simulate_actions(_actions(), 500, 17, asset_id="A", common_factor_seed=99)
    chart = action_scenario_samples(results, draws=20, seed=1234)
    assert chart["source"] == "stored_model_samples"
    assert chart["draws"] == 500
    for result in results:
        samples = np.array(chart["samples"][result["action"]])
        assert result["expected_npv_m"] == pytest.approx(samples.mean(), abs=5.1e-7)
        assert result["p10_npv_m"] == pytest.approx(np.quantile(samples, .1), abs=5.1e-7)
        assert result["cvar_95_m"] >= result["var_95_m"] >= 0
        assert len(result["scenario_npvs_m"]) == 128
    assert results[0]["expected_npv_m"] == results[0]["cvar_95_m"] == 0


def test_risk_scales_with_economic_size_and_does_not_depend_on_action_order():
    first = simulate_actions(_actions(), 400, 23, asset_id="A")
    doubled = simulate_actions(_actions(2), 400, 23, asset_id="A")
    reversed_actions = simulate_actions(list(reversed(_actions())), 400, 23, asset_id="A")
    for left, right in zip(first, doubled):
        np.testing.assert_allclose(np.array(left["scenario_samples_m"]) * 2, right["scenario_samples_m"], atol=1.1e-6)
    assert {row["action"]: row["scenario_samples_m"] for row in first} == {row["action"]: row["scenario_samples_m"] for row in reversed_actions}


def test_asset_idiosyncratic_noise_differs_but_common_factor_shock_is_shared():
    left = simulate_actions(_actions(), 1000, 23, asset_id="A", common_factor_seed=44)[1]
    right = simulate_actions(_actions(), 1000, 24, asset_id="B", common_factor_seed=44)[1]
    assert left["common_factor_seed"] == right["common_factor_seed"]
    assert left["scenario_samples_m"] != right["scenario_samples_m"]
    assert np.corrcoef(left["scenario_samples_m"], right["scenario_samples_m"])[0, 1] > .15


def test_factor_draw_shape_bounds_and_invalid_draw_count():
    factors = factor_scenarios(1000, 15)
    assert factors.shape == (1000, 6)
    assert np.isfinite(factors).all()
    assert np.all((factors[:, 2] >= .025) & (factors[:, 2] <= .1))
    assert np.all((factors[:, 5] >= 3) & (factors[:, 5] <= 72))
    with pytest.raises(ValueError):
        factor_scenarios(0)


def test_rare_losses_are_not_cancelled_by_gains_inside_the_loss_tail(monkeypatch):
    samples = np.array([-100.] * 2 + [100.] * 98)
    monkeypatch.setattr(engine, "_action_samples", lambda *args: samples)
    result = simulate_actions([_actions()[1]], draws=100)[0]
    assert result["cvar_95_m"] == pytest.approx(40.)
    assert result["signed_loss_cvar_95_m"] == pytest.approx(-20.)


def test_failed_approval_has_no_development_income_exposure_or_financing_penalty():
    action = {**_actions()[1], "success_probability": 0.}
    factors = np.tile([.025, .07, .0475, .04, .035, 24.], (100, 1))
    stressed = factors.copy()
    stressed[:, [0, 1, 2, 3, 5]] += [.05, .05, .01, .02, 12.]
    original = engine._action_samples(action, factors, 7, "A")
    np.testing.assert_array_equal(original, engine._action_samples(action, stressed, 7, "A"))
    action["success_probability"] = 1.
    interest_only = factors.copy()
    interest_only[:, 3] += .02
    np.testing.assert_array_equal(engine._action_samples(action, factors, 7, "A"), engine._action_samples(action, interest_only, 7, "A"))
