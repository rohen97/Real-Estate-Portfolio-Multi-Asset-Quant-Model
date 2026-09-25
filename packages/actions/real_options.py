"""Unlevered action screening on a common, end-of-period Hold baseline."""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class ActionDefinition:
    action: str
    capex_rate: float
    noi_uplift: float
    disruption_rate: float
    duration_years: int
    success_probability: float
    terminal_uplift: float


ACTIONS = [
    ActionDefinition('Hold', 0, 0, 0, 0, 1, 0),
    ActionDefinition('Retrofit', .08, .10, .12, 2, .9, 0),
    ActionDefinition('Repurpose', .22, .24, .35, 3, .75, 0),
    ActionDefinition('Redevelop', .45, .48, .8, 5, .62, 0),
    ActionDefinition('Sell', 0, 0, 0, 0, 1, 0),
]


def npv(rate, cashflows, start_period=0):
    """Discount explicit periods; a vector including time zero uses the default."""
    if not math.isfinite(rate) or rate <= -1:
        raise ValueError('discount rate must be finite and greater than -1')
    return sum(v / (1 + rate) ** (i + start_period) for i, v in enumerate(cashflows))


def evaluate_specifications(current_value_m, base_noi_m, capacity_option_m, specifications,
                            discount_rate=.078, horizon=10, terminal_cap_rate=.05,
                            rent_growth=.025, selling_cost_rate=.025,
                            capex_multiplier=1.0, approval_multiplier=1.0,
                            sale_price_multiplier=1.0):
    """Value success and failed-execution branches without mixing debt with asset PV.

    Failure retains Hold cashflows and loses 55% of planned capex. This is an
    explicit screening assumption, not an empirically calibrated failure model.
    Specification capex is an absolute amount, unlike ActionDefinition's rate.
    """
    if horizon < 1 or int(horizon) != horizon:
        raise ValueError('horizon must be a positive integer')
    numbers = (current_value_m, base_noi_m, capacity_option_m, terminal_cap_rate,
               rent_growth, selling_cost_rate, capex_multiplier, approval_multiplier,
               sale_price_multiplier)
    if not all(math.isfinite(v) for v in numbers):
        raise ValueError('valuation inputs must be finite')
    if current_value_m < 0 or terminal_cap_rate <= 0 or rent_growth <= -1:
        raise ValueError('value must be nonnegative, cap rate positive and growth above -1')
    if not 0 <= selling_cost_rate < 1 or min(capex_multiplier, approval_multiplier, sale_price_multiplier) < 0:
        raise ValueError('invalid selling cost or scenario multiplier')
    horizon = int(horizon)
    base_noi = [base_noi_m * (1 + rent_growth) ** y for y in range(1, horizon + 1)]
    base = base_noi.copy()
    base[-1] += base_noi[-1] * (1 + rent_growth) / terminal_cap_rate * (1 - selling_cost_rate)
    baseline_pv = npv(discount_rate, base, start_period=1)
    results = []
    for spec in specifications:
        action = spec['action']
        duration = float(spec['duration_years'])
        capex = float(spec['capex_m']) * capex_multiplier
        probability = min(1., max(0., spec['success_probability'] * approval_multiplier))
        if action == 'Hold':
            expected = [0.] + base.copy()
            success = expected.copy()
            failure = expected.copy()
            probability, capex, duration, sunk_cost = 1., 0., 0., 0.
        elif action == 'Sell':
            proceeds = current_value_m * sale_price_multiplier * (1 - selling_cost_rate)
            expected = [proceeds] + [0.] * horizon
            success = expected.copy()
            failure = expected.copy()
            probability, capex, duration, sunk_cost = 1., -proceeds, 0., 0.
        else:
            success = [-capex]
            for year, noi in enumerate(base_noi, start=1):
                construction_share = min(1., max(0., duration - year + 1))
                operational_share = 1 - construction_share
                success.append(noi * (1 + spec['noi_uplift'] * operational_share)
                               * (1 - spec['disruption_rate'] * construction_share))
            completed = duration <= horizon
            terminal_noi = base_noi[-1] * (1 + rent_growth) * (1 + spec['noi_uplift'] if completed else 1)
            terminal_premium = 1 + spec.get('terminal_uplift', 0.) if completed else 1
            success[-1] += terminal_noi / terminal_cap_rate * (1 - selling_cost_rate) * terminal_premium
            sunk_cost = capex * .55
            failure = [-sunk_cost] + base.copy()
            expected = [probability * good + (1 - probability) * bad
                        for good, bad in zip(success, failure)]
        expected_pv = npv(discount_rate, expected)
        incremental = [expected[0]] + [a - b for a, b in zip(expected[1:], base)]
        operating_pv = npv(discount_rate, expected[1:], start_period=1)
        if action == 'Sell':
            operating_pv = expected[0]
        results.append({
            'action': action, 'incremental_npv_m': round(expected_pv - baseline_pv, 6),
            'success_incremental_npv_m': round(npv(discount_rate, success) - baseline_pv, 6),
            'failure_incremental_npv_m': round(npv(discount_rate, failure) - baseline_pv, 6),
            'pv_after_m': round(operating_pv, 6), 'pv_without_m': round(baseline_pv, 6),
            'expected_project_pv_m': round(expected_pv, 6), 'capex_m': round(capex, 6),
            'expected_capex_m': round(-min(0., expected[0]), 6),
            'financing_cost_m': 0., 'failure_cost_m': round((1 - probability) * sunk_cost, 6),
            'success_probability': probability, 'execution_years': duration,
            'annual_cashflows_m': [round(v, 6) for v in expected[1:]],
            'time_zero_cashflow_m': round(expected[0], 6),
            'incremental_cashflows_m': [round(v, 6) for v in incremental],
            'success_cashflows_m': [round(v, 6) for v in success],
            'failure_cashflows_m': [round(v, 6) for v in failure],
            'cashflow_basis': 'unlevered; time zero plus year-end cashflows; incremental to Hold',
            'cashflow_start_year': 1,
            'current_value_m': current_value_m, 'base_noi_m': base_noi_m,
            'reference_cap_rate': terminal_cap_rate, 'reference_rent_growth': rent_growth,
            'capacity_option_unpriced_m': round(max(0., capacity_option_m), 6),
            'capacity_option_treatment': 'screening only; excluded to avoid overlap with capitalised NOI uplift',
            'assumption_status': 'illustrative action uplifts, probabilities and failure sunk-cost fraction',
            'decision_ready': False,
        })
    return results


def evaluate_actions(current_value_m, base_noi_m, capacity_option_m, discount_rate=.078,
                     horizon=10, terminal_cap_rate=.05, *, rent_growth=.025,
                     selling_cost_rate=.025, capex_multiplier=1.0, approval_multiplier=1.0,
                     sale_price_multiplier=1.0):
    specifications = [{**vars(spec), 'capex_m': current_value_m * spec.capex_rate} for spec in ACTIONS]
    return evaluate_specifications(current_value_m, base_noi_m, capacity_option_m, specifications,
                                   discount_rate, horizon, terminal_cap_rate, rent_growth,
                                   selling_cost_rate, capex_multiplier, approval_multiplier,
                                   sale_price_multiplier)


def real_options(actions: list[dict], base_noi_m, discount_rate=.078):
    """Do not invent option alpha from income already included in the Hold DCF."""
    upside = max([0.] + [a['incremental_npv_m'] for a in actions
                        if a['action'] in ('Repurpose', 'Redevelop')])
    return {'Wait': 0., 'Phase': 0., 'Abandon': 0., 'Expand': 0.,
            'status': 'not_valued', 'decision_ready': False,
            'immediate_exercise_screen_m': round(upside, 6),
            'method': 'No option premium credited: calibrated transition and exercise-cost inputs are absent; zero is not an estimate of option market value.'}
