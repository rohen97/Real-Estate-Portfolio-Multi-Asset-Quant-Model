"""Regression cases for funding, recourse, timing and portfolio-risk invariants."""
import copy
import pytest

from packages.optimisation.common import audit_plan, build_options, weighted_loss_cvar
from packages.optimisation.multiperiod import optimise_multi_period
from packages.optimisation.two_stage import optimise_two_stage
from packages.optimisation.stability import analyse_stability

BASE = [{"name": "Base", "probability": 1, "npv_multiplier": 1, "capex_multiplier": 1, "delay_years": 0}]


def action(name, npv=0, capex=0, duration=1, risk=0, **kwargs):
    return {"action": name, "expected_npv_m": npv, "capex_m": capex,
            "execution_years": duration, "cvar_95_m": risk, **kwargs}


def asset(aid, actions):
    return {"asset_id": aid, "name": aid, "base_noi_m": 1, "current_value_m": 1000, "actions": actions}


def two(assets, **kwargs):
    params = dict(scenarios=BASE, horizon_years=3, total_capital_budget_m=1000,
                  minimum_liquidity_m=0, minimum_noi_ratio=0, cvar_penalty=.25)
    params.update(kwargs)
    return optimise_two_stage(assets, **params)


def test_zero_and_fractional_development_share_are_hard_limits():
    assets = [asset("A", [action("Hold"), action("Redevelop", 100, 1)])]
    for share in (0, .45):
        result = optimise_multi_period(assets, max_development_share=share)
        assert result["feasible"]
        assert result["selections"][0]["action"] == "Hold"
        assert result["constraints"]["maximum_development_actions"] == 0


def test_projects_longer_than_horizon_are_not_partially_costed():
    assets = [asset("A", [action("Hold", duration=0), action("Redevelop", 100, 30, 3)])]
    result = optimise_multi_period(assets, horizon_years=2, max_development_share=1)
    assert result["selections"][0]["action"] == "Hold"


def test_deferred_start_discounts_npv_and_keeps_full_funding():
    assets = [asset("A", [action("Hold"), action("Retrofit", 110, 10, 1)])]
    result = optimise_multi_period(assets, horizon_years=2, total_capital_budget_m=100,
                                  minimum_liquidity_m=0, annual_capital_budgets=[0, 100],
                                  max_development_share=1, discount_rate=.1)
    selected = result["selections"][0]
    assert selected["start_year"] == 2
    assert selected["expected_npv_m"] == pytest.approx(100)
    assert selected["capex_schedule_m"] == [0, 10]
    assert result["constraint_audit"]["passed"]


def test_two_stage_limits_concurrent_projects_and_can_stagger():
    assets = [asset(aid, [action("Hold"), action("Retrofit", 100, 10, 2)]) for aid in ("A", "B")]
    result = two(assets, horizon_years=4, max_concurrent_projects=1)
    assert result["feasible"]
    assert len(result["recourse"][0]["executed"]) == 2
    assert sorted(row["start_year"] for row in result["selections"]) == [1, 3]
    assert max(row["active_projects"] for row in result["recourse"][0]["annual_plan"]) == 1


def test_future_sale_receipts_cannot_fund_earlier_years():
    assets = [asset("A", [action("Redevelop", 100, 100)]),
              asset("B", [action("Sell", 0, -100, sale_delay_years=2)])]
    result = two(assets, total_capital_budget_m=50, annual_capital_budgets=[100, 100, 100])
    assert result["feasible"]
    assert next(row for row in result["selections"] if row["asset_id"] == "A")["start_year"] == 3
    assert all(row["cumulative_net_funding_m"] <= 50 for row in result["recourse"][0]["annual_plan"])
    sale = next(row for row in result["recourse"][0]["selections"] if row["action"] == "Sell")
    assert sale["lost_noi_m"] == [0, 0, 1]


def test_scenario_delay_moves_all_execution_resources():
    scenarios = [{**BASE[0], "delay_years": 1}]
    assets = [asset("A", [action("Hold"), action("Retrofit", 110, 10, 2)])]
    result = two(assets, scenarios=scenarios, discount_rate=.1)
    executed = result["recourse"][0]["executed"][0]
    assert executed["planned_start_year"] == 1 and executed["start_year"] == 2
    assert executed["capex_schedule_m"] == [0, 5, 5]
    assert executed["active_projects"] == [0, 1, 1]
    assert executed["lost_noi_m"] == [0, .12, .12]
    assert executed["expected_npv_m"] == pytest.approx(100)


def test_delay_cannot_hide_unfunded_completion_past_horizon():
    assets = [asset("A", [action("Hold"), action("Retrofit", 100, 10, 2)])]
    result = two(assets, horizon_years=2, scenarios=[{**BASE[0], "delay_years": 1}])
    assert result["selections"][0]["action"] == "Hold"


def test_cancelled_project_cannot_create_a_cheaper_hold():
    assets = [asset("A", [action("Hold", -10, 1), action("Retrofit", -100, 1)])]
    result = two(assets)
    assert result["selections"][0]["action"] == "Hold"
    assert result["portfolio_expected_npv_m"] == pytest.approx(-10)
    assert result["objective"] == pytest.approx(-12.5)


def test_cancellation_keeps_hold_cost_and_charges_fee_to_liquidity():
    scenarios = [{**BASE[0], "probability": .9},
                 {**BASE[0], "name": "Delay", "probability": .1, "delay_years": 3}]
    assets = [asset("A", [action("Hold", -2, 2), action("Retrofit", 100, 10)])]
    result = two(assets, scenarios=scenarios, cvar_penalty=0)
    delayed = result["recourse"][1]
    assert delayed["cancelled"][0]["fallback_action"] == "Hold"
    assert delayed["portfolio_npv_m"] == pytest.approx(-2.8)
    assert delayed["annual_plan"][0]["capex_m"] == pytest.approx(2.8)
    assert delayed["constraint_audit"]["passed"]


def test_profitable_tail_is_not_rewarded_as_negative_cvar():
    assets = [asset("A", [action("Hold", 10)])]
    result = two(assets)
    assert result["portfolio_loss_cvar_m"] == 0
    assert result["risk_adjusted_objective_m"] == result["portfolio_expected_npv_m"] == 10


def test_joint_tail_risk_recognises_diversification():
    assets = [asset("A", [action("Hold", 0, risk=10, scenario_npvs_m=[-10, 10])]),
              asset("B", [action("Hold", 0, risk=10, scenario_npvs_m=[10, -10]),
                          action("Retrofit", 5, risk=10, scenario_npvs_m=[-10, 20])])]
    result = optimise_multi_period(assets, cvar_penalty=1, max_development_share=1)
    assert all(row["action"] == "Hold" for row in result["selections"])
    assert result["portfolio_loss_cvar_m"] == 0
    assert result["sum_of_marginal_cvar_95_m"] == 20
    marginal_assets = copy.deepcopy(assets)
    for a in marginal_assets:
        for row in a["actions"]:
            row.pop("scenario_npvs_m")
    marginal = optimise_multi_period(marginal_assets, cvar_penalty=1, max_development_share=1)
    assert next(row for row in marginal["selections"] if row["asset_id"] == "B")["action"] == "Retrofit"
    assert marginal["portfolio_loss_cvar_m"] is None


def test_weighted_cvar_splits_mass_at_tail_boundary():
    assert weighted_loss_cvar([-100, -10, 20], [.02, .04, .94], .95) == pytest.approx(46)


def test_independent_audit_detects_a_corrupted_schedule():
    assets = [asset("A", [action("Retrofit", 10, 10)])]
    selected = build_options(assets, 2, .1)[:1]
    selected[0]["capex_schedule_m"][0] = 100
    audit, _ = audit_plan(selected, assets, 2, 20, 0, [20, 20], 0, 0)
    assert not audit["passed"]
    assert audit["max_violation"] == 80
    assert audit["violation_count"] >= 3


def test_dependencies_apply_to_later_starts_and_actual_completion():
    assets = [asset("A", [action("Hold"), action("Retrofit", -1, 1)]),
              asset("B", [action("Hold"), action("Redevelop", 100, 1)])]
    dependencies = [{"asset_id": "B", "action": "Redevelop", "requires_asset_id": "A", "requires_action": "Retrofit"}]
    result = two(assets, dependencies=dependencies, horizon_years=2)
    chosen = {row["asset_id"]: row for row in result["recourse"][0]["executed"]}
    assert chosen["A"]["action"] == "Retrofit" and chosen["A"]["start_year"] == 1
    assert chosen["B"]["start_year"] == 2
    assert result["constraint_audit"]["passed"]


def test_scenario_probability_validation_and_signed_downside():
    assets = [asset("A", [action("Hold", -10)])]
    with pytest.raises(ValueError, match="sum to one"):
        two(assets, scenarios=[{**BASE[0], "probability": .9}])
    result = two(assets, scenarios=[{**BASE[0], "npv_multiplier": .55}])
    assert result["portfolio_expected_npv_m"] == pytest.approx(-14.5)


def test_stability_separates_risk_objective_and_expected_npv():
    assets = [asset("A", [action("Hold", -10, risk=10)])]
    result = analyse_stability(assets, runs=3, cvar_penalty=1)
    assert result["successful_runs"] == 3 and result["failed_runs"] == 0
    assert result["objective_mean_m"] == result["risk_adjusted_objective_mean_m"]
    assert result["objective_mean_m"] < result["portfolio_expected_npv_mean_m"]
    assert result["assets"][0]["modal_action"] == "Hold"


def test_all_infeasible_perturbations_do_not_generate_nan(monkeypatch):
    import packages.optimisation.stability as module
    monkeypatch.setattr(module, "optimise_multi_period", lambda *a, **k: {"feasible": False, "selections": [], "status": "fixture infeasible"})
    result = module.analyse_stability([asset("A", [action("Hold")])], runs=2)
    assert result["successful_runs"] == 0 and result["failed_runs"] == 2
    assert result["objective_mean_m"] is None
    assert result["assets"][0]["stability_score"] is None

def test_malformed_sale_is_rejected_and_settlement_discounts_npv():
    with pytest.raises(ValueError, match='Sell capex'):
        optimise_multi_period([asset('A', [action('Sell', 10, 5)])])
    result = optimise_multi_period([asset('A', [action('Sell', 121, -100, sale_delay_years=2)])],
                                  horizon_years=3, discount_rate=.1, minimum_noi_ratio=0)
    assert result['selections'][0]['expected_npv_m'] == pytest.approx(100)


def test_stressed_sale_receipt_reduces_funding_and_npv():
    assets = [asset('A', [action('Sell', 10, -100)])]
    result = two(assets, scenarios=[{**BASE[0], 'sale_receipt_multiplier': .9}])
    scenario = result['recourse'][0]
    assert scenario['portfolio_npv_m'] == pytest.approx(0)
    assert scenario['annual_plan'][0]['capital_released_m'] == pytest.approx(90)
