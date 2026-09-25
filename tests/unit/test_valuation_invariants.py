"""Analytical cashflow identities that do not encode preferred recommendations."""
from dataclasses import replace
from datetime import date
import numpy as np
import pytest

from packages.actions.detailed_cashflow import DetailedActionInputs, evaluate_detailed_action, irr
from packages.actions.enbloc import EnBlocInputs, evaluate_enbloc
from packages.actions.real_options import evaluate_actions, npv, real_options
from packages.valuation.engine import AssetEconomics, dcf, value_actions


def detailed(**kwargs):
    defaults = dict(action='Redevelop', current_value_m=120, current_noi_m=5.8,
                    site_area_sqm=8000, current_gfa_sqm=16000, approved_gfa_sqm=24000,
                    nla_efficiency=.78, market_value_per_nla_sqm=12000,
                    construction_cost_per_gfa_sqm=4200, assessed_lbc_m=12,
                    inputs_verified=True)
    return DetailedActionInputs(**{**defaults, **kwargs})


def enbloc(**kwargs):
    defaults = dict(current_strata_value_m=200, site_area_sqm=10000, existing_gfa_sqm=18000,
                    legal_gpr=2.8, nla_efficiency=.78, sale_price_per_nla_sqm=14000,
                    construction_cost_per_gfa_sqm=4200, lbc_rate_per_sqm=None,
                    tenure_remaining_years=70, owners_count=120, assessed_lbc_m=12)
    return EnBlocInputs(**{**defaults, **kwargs})


def test_first_year_noi_and_terminal_are_discounted_one_period():
    # Flat NOI of 5; net terminal value 97.5, both paid at end of year one.
    expected = (5 + 5 / .05 * .975) / 1.1
    action = evaluate_actions(100, 5, 0, discount_rate=.1, horizon=1,
                              terminal_cap_rate=.05, rent_growth=0)[0]
    assert action['pv_without_m'] == pytest.approx(expected, abs=1e-6)
    core = dcf(AssetEconomics(100, 5, market_rent_growth=0, holding_years=1,
                              cap_rate=.05, discount_rate=.1))
    assert core['value_m'] == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize('cap_rate', [.035, .05, .09])
def test_hold_is_exact_zero_under_every_baseline(cap_rate):
    hold = evaluate_actions(100, 5, 999, terminal_cap_rate=cap_rate)[0]
    assert hold['incremental_npv_m'] == hold['capex_m'] == 0
    assert all(v == 0 for v in hold['incremental_cashflows_m'])
    assert value_actions(AssetEconomics(100, 5, cap_rate=cap_rate), {})[0]['incremental_npv_m'] == 0


def test_cashflow_branch_probability_reconciliation():
    for action in evaluate_actions(100, 5, 20):
        p = action['success_probability']
        expected = p * action['success_incremental_npv_m'] + (1 - p) * action['failure_incremental_npv_m']
        assert action['incremental_npv_m'] == pytest.approx(expected, abs=2e-6)
        assert npv(.078, action['incremental_cashflows_m']) == pytest.approx(action['incremental_npv_m'], abs=3e-6)


def test_sale_is_immediate_proceeds_less_the_same_hold_pv():
    sale = evaluate_actions(100, 5, 0, sale_price_multiplier=.8)[-1]
    assert sale['capex_m'] == -78
    assert sale['incremental_npv_m'] == pytest.approx(78 - sale['pv_without_m'], abs=1e-6)
    assert all(v == 0 for v in sale['annual_cashflows_m'])


def test_capex_stress_does_not_create_value_or_change_hold():
    base = evaluate_actions(100, 5, 0)
    stressed = evaluate_actions(100, 5, 0, capex_multiplier=1.3)
    for before, after in zip(base, stressed):
        assert after['incremental_npv_m'] <= before['incremental_npv_m']
    assert base[0]['incremental_npv_m'] == stressed[0]['incremental_npv_m'] == 0


def test_capacity_and_real_options_do_not_double_count_unpriced_upside():
    low = evaluate_actions(100, 5, 0)
    high = evaluate_actions(100, 5, 1000)
    assert [a['incremental_npv_m'] for a in low] == [a['incremental_npv_m'] for a in high]
    options = real_options(high, 5)
    assert options['status'] == 'not_valued'
    assert all(options[k] == 0 for k in ('Wait', 'Phase', 'Abandon', 'Expand'))


def test_rebuild_costs_all_floors_even_without_capacity_increase():
    inputs = detailed(approved_gfa_sqm=16000)
    result = evaluate_detailed_action(inputs)
    assert result['additional_gfa_sqm'] == 0
    assert result['construction_m'] == pytest.approx(16000 * 4200 / 1e6)


def test_debt_draw_interest_repayment_and_equity_reconcile_every_month():
    result = evaluate_detailed_action(detailed())
    project = np.array(result['success_unlevered_cashflows_m'])
    equity = np.array(result['success_equity_cashflows_m'])
    draws = np.array(result['monthly_debt_draws_m'])
    repayments = np.array(result['monthly_debt_repayments_m'])
    interest = np.array(result['monthly_interest_m'])
    assert equity == pytest.approx(project + draws - interest - repayments, abs=3e-8)
    assert draws.sum() == pytest.approx(repayments.sum(), abs=1e-6)
    assert result['monthly_closing_debt_m'][-1] == 0
    assert min(result['monthly_closing_debt_m']) >= 0


def test_borrowing_does_not_change_unlevered_decision_npv():
    low = evaluate_detailed_action(detailed(loan_to_cost=0))
    high = evaluate_detailed_action(detailed(loan_to_cost=.8))
    assert low['npv_m'] == high['npv_m']
    assert low['financing_interest_m'] == 0 < high['financing_interest_m']
    assert high['equity_npv_m'] is None  # Cost of equity has not been supplied.


def test_monthly_incremental_npv_uses_same_horizon_hold_opportunity_cost():
    result = evaluate_detailed_action(detailed())
    project = np.array(result['monthly_project_cashflows_m'])
    hold = np.array(result['monthly_hold_cashflows_m'])
    incremental = np.array(result['monthly_cashflows_m'])
    assert project[0] == hold[0] == -120
    assert incremental == pytest.approx(project - hold, abs=2e-8)
    calculated = npv((1.078 ** (1 / 12)) - 1, incremental)
    assert result['npv_m'] == pytest.approx(calculated, abs=1e-6)
    assert result['project_npv_m'] - result['hold_npv_m'] == pytest.approx(result['npv_m'], abs=2e-6)


def test_failed_approval_spends_predevelopment_only_and_retains_hold():
    result = evaluate_detailed_action(detailed(approval_probability=0))
    cash = np.array(result['monthly_cashflows_m'])
    assert np.all(cash <= 0)
    assert cash.sum() == pytest.approx(-result['professional_fees_m'], abs=1e-6)
    assert np.all(cash[10:] == 0)


def test_missing_lbc_keeps_explicit_nondecision_ready_status():
    unknown = evaluate_detailed_action(detailed(assessed_lbc_m=None))
    assert unknown['lbc']['total_sgd'] is None
    assert unknown['decision_ready'] is False and unknown['verification_required'] is True
    assert 'unassessed LBC' in unknown['excluded_costs']
    known = evaluate_detailed_action(detailed(assessed_lbc_m=0))
    assert known['decision_ready'] is True
    screening_rate = evaluate_detailed_action(detailed(assessed_lbc_m=None, lbc_rate_per_sqm=1800))
    assert screening_rate['lbc']['status'] == 'calculated'
    assert screening_rate['decision_ready'] is False


def test_assessed_lbc_monotonically_reduces_value():
    low = evaluate_detailed_action(detailed(assessed_lbc_m=0))
    high = evaluate_detailed_action(detailed(assessed_lbc_m=20))
    assert high['npv_m'] < low['npv_m']


def test_exact_month_disposal_date_and_nonconventional_irr():
    result = evaluate_detailed_action(detailed(start_date=date(2026, 1, 31),
        predevelopment_months=0, construction_months=1, lease_up_months=0))
    assert result['disposal_date'] == '2027-02-28'
    assert irr([-100, 230, -132]) is None
    assert irr([-100, 110]) == pytest.approx(.1)


def test_enbloc_land_offer_plus_its_duty_reconciles_residual():
    result = evaluate_enbloc(enbloc(sale_price_per_nla_sqm=20000))
    assert result['maximum_land_value_m'] > 0
    assert result['maximum_land_value_m'] + result['buyer_stamp_duty_m'] == pytest.approx(
        result['residual_before_buyer_duty_m'], abs=2e-6)
    assert abs(result['residual_reconciliation_error_m']) <= 1e-6


def test_enbloc_consent_threshold_and_failure_fallback():
    low = evaluate_enbloc(enbloc(required_consent=.8))
    high = evaluate_enbloc(enbloc(required_consent=.9))
    assert high['owner_consent_probability'] <= low['owner_consent_probability']
    failed = evaluate_enbloc(enbloc(observed_consent_share=.7))
    assert failed['success_probability'] == 0
    assert failed['expected_discounted_enbloc_value_m'] == 0
    assert failed['expected_retained_asset_value_m'] > 0
    assert failed['incremental_npv_vs_hold_m'] == 0


def test_enbloc_unknown_lbc_cannot_be_used_for_decisions():
    result = evaluate_enbloc(enbloc(assessed_lbc_m=None))
    assert not result['decision_ready']
    assert result['lbc']['total_sgd'] is None


@pytest.mark.parametrize('kwargs', [{'horizon': 0}, {'terminal_cap_rate': 0}, {'capex_multiplier': -1}])
def test_invalid_annual_inputs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        evaluate_actions(100, 5, 0, **kwargs)


def test_advanced_no_feasible_envelope_does_not_value_existing_area_as_approved(monkeypatch):
    import json
    from pathlib import Path
    import packages.orchestration.advanced as advanced
    monkeypatch.setattr(advanced, 'generate_envelopes', lambda inputs: {
        'preferred': None, 'options': [], 'status': 'no_feasible_envelope'})
    asset = json.loads((Path(__file__).resolve().parents[2] / 'data/examples/demo_portfolio.json').read_text())[0]
    result = advanced.analyse_asset(asset)['redevelopment_cashflow']
    assert result['npv_m'] is None
    assert result['monthly_cashflows_m'] == []
    assert result['decision_ready'] is False
    assert result['feasible_envelope'] is False
    assert result['valuation_status'] == 'not_evaluated_no_feasible_envelope'
