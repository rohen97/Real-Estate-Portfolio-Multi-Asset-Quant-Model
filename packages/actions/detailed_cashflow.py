"""Monthly development cashflows with explicit ownership and financing ledgers."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
import math

import numpy as np
from scipy.optimize import brentq

from packages.economics.singapore_costs import buyer_stamp_duty, seller_stamp_duty, land_betterment_charge


@dataclass
class DetailedActionInputs:
    action: str
    current_value_m: float
    current_noi_m: float
    site_area_sqm: float
    current_gfa_sqm: float
    approved_gfa_sqm: float
    nla_efficiency: float
    market_value_per_nla_sqm: float
    construction_cost_per_gfa_sqm: float
    professional_fee_rate: float = .12
    contingency_rate: float = .08
    interest_rate: float = .045
    loan_to_cost: float = .6
    construction_months: int = 36
    predevelopment_months: int = 9
    lease_up_months: int = 18
    tenant_relocation_m: float = 0
    demolition_m: float = 0
    marketing_rate: float = .02
    sale_cost_rate: float = .025
    approval_probability: float = .65
    lbc_rate_per_sqm: float | None = None
    residential_share: float = 1
    acquisition_date: date = date(2020, 1, 1)
    start_date: date = date(2026, 9, 24)
    noi_growth: float = .025
    hold_value_growth: float = .025
    stabilised_noi_yield: float = .045
    assessed_lbc_m: float | None = None
    inputs_verified: bool = False
    equity_discount_rate: float | None = None


def s_curve(months):
    if months < 1 or int(months) != months:
        raise ValueError('construction months must be a positive integer')
    x = np.arange(1, months + 1)
    weights = np.sin(np.pi * x / (months + 1)) ** 1.7
    return weights / weights.sum()


def irr(cashflows):
    """Return a conventional cashflow IRR only; ambiguous roots are not ranked."""
    significant = [float(v) for v in cashflows if abs(v) > 1e-12]
    changes = sum(a * b < 0 for a, b in zip(significant, significant[1:]))
    if changes != 1 or not significant or significant[0] >= 0:
        return None
    def f(rate):
        return sum(v / (1 + rate) ** i for i, v in enumerate(cashflows))
    try:
        # Monthly lower bound avoids overflow on long cashflow series.
        return brentq(f, -.5, 10)
    except (ValueError, OverflowError):
        return None


def _add_months(value, months):
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    return date(year, month0 + 1, min(value.day, monthrange(year, month0 + 1)[1]))


def evaluate_detailed_action(x: DetailedActionInputs, discount_rate=.078):
    if x.action not in ('Acquire', 'Redevelop'):
        raise ValueError('the detailed full-rebuild engine supports Acquire or Redevelop only')
    for name in ('current_value_m', 'current_noi_m', 'site_area_sqm', 'current_gfa_sqm',
                 'approved_gfa_sqm', 'market_value_per_nla_sqm', 'construction_cost_per_gfa_sqm',
                 'professional_fee_rate', 'contingency_rate', 'interest_rate',
                 'tenant_relocation_m', 'demolition_m', 'stabilised_noi_yield'):
        value = getattr(x, name)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    for name in ('loan_to_cost', 'approval_probability', 'residential_share', 'nla_efficiency'):
        if not 0 <= getattr(x, name) <= 1:
            raise ValueError(f'{name} must be between zero and one')
    if not 0 <= x.marketing_rate + x.sale_cost_rate < 1 or min(x.marketing_rate, x.sale_cost_rate) < 0:
        raise ValueError('combined sale costs must be between zero and one')
    if min(discount_rate, x.noi_growth, x.hold_value_growth) <= -1:
        raise ValueError('discount and growth rates must exceed -1')
    for name in ('predevelopment_months', 'lease_up_months'):
        if getattr(x, name) < 0 or int(getattr(x, name)) != getattr(x, name):
            raise ValueError(f'{name} must be a nonnegative integer')
    weights = s_curve(x.construction_months)
    additional = max(0., x.approved_gfa_sqm - x.current_gfa_sqm)
    # A demolition/rebuild replaces all floor area, including the existing floors.
    construction_gfa = x.approved_gfa_sqm
    construction = construction_gfa * x.construction_cost_per_gfa_sqm / 1e6
    fees = construction * x.professional_fee_rate
    contingency = construction * x.contingency_rate
    if x.assessed_lbc_m is not None:
        if not math.isfinite(x.assessed_lbc_m) or x.assessed_lbc_m < 0:
            raise ValueError('assessed LBC must be finite and nonnegative')
        lbc = {'status': 'assessed_input', 'total_sgd': x.assessed_lbc_m * 1e6,
               'source': 'user-supplied assessed LBC; verify assessment date and scope'}
    else:
        lbc = land_betterment_charge(additional, x.lbc_rate_per_sqm)
    lbc_known = lbc.get('total_sgd') is not None
    lbc_m = lbc['total_sgd'] / 1e6 if lbc_known else 0.
    development = construction + fees + contingency + x.tenant_relocation_m + x.demolition_m + lbc_m
    months = x.predevelopment_months + x.construction_months + x.lease_up_months + 12
    operation_start = x.predevelopment_months + x.construction_months
    disposal_date = _add_months(x.start_date, months)
    acquisition_date = x.start_date if x.action == 'Acquire' else x.acquisition_date
    bsd = buyer_stamp_duty(x.current_value_m * 1e6, x.residential_share)['total_sgd'] / 1e6 if x.action == 'Acquire' else 0.
    opportunity = x.current_value_m
    hold = np.zeros(months + 1)
    hold[0] = -opportunity - bsd
    for month in range(1, months + 1):
        hold[month] = x.current_noi_m / 12 * (1 + x.noi_growth) ** (month / 12)
    hold_gross_sale = x.current_value_m * (1 + x.hold_value_growth) ** (months / 12)
    hold_ssd = seller_stamp_duty(hold_gross_sale * 1e6, acquisition_date, disposal_date, x.residential_share)['total_sgd'] / 1e6
    hold[-1] += hold_gross_sale * (1 - x.sale_cost_rate) - hold_ssd

    success = np.zeros(months + 1)
    success[0] = -opportunity - bsd
    predevelopment = np.zeros(months + 1)
    if x.predevelopment_months:
        predevelopment[1:x.predevelopment_months + 1] = fees / x.predevelopment_months
        success[1:x.predevelopment_months + 1] = hold[1:x.predevelopment_months + 1]
    else:
        predevelopment[0] = fees
    success -= predevelopment
    construction_spend = np.zeros(months + 1)
    start = x.predevelopment_months + 1
    construction_spend[start:start + x.construction_months] = (construction + contingency) * weights
    construction_spend[start] += x.tenant_relocation_m + x.demolition_m + lbc_m
    success -= construction_spend
    gross_value = x.approved_gfa_sqm * x.nla_efficiency * x.market_value_per_nla_sqm / 1e6
    stabilised_noi = gross_value * x.stabilised_noi_yield
    for month in range(operation_start + 1, months + 1):
        progress = min(1., (month - operation_start) / max(1, x.lease_up_months))
        success[month] += stabilised_noi / 12 * progress
    net_sale = gross_value * (1 - x.marketing_rate - x.sale_cost_rate)
    # Existing statutory helper receives gross consideration, not proceeds net of fees.
    ssd = seller_stamp_duty(gross_value * 1e6, acquisition_date, disposal_date, x.residential_share)['total_sgd'] / 1e6
    success[-1] += net_sale - ssd
    failure = hold - predevelopment
    probability = x.approval_probability
    expected_project = probability * success + (1 - probability) * failure
    comparison = np.zeros_like(hold) if x.action == 'Acquire' else hold
    incremental = expected_project - comparison

    # Development-only borrowing: no predevelopment/acquisition finance assumed.
    debt_draws = construction_spend * x.loan_to_cost
    balance = np.cumsum(debt_draws)
    interest = balance * x.interest_rate / 12
    interest[0] = 0.
    repayments = np.zeros(months + 1)
    repayments[-1] = balance[-1]
    equity_success = success + debt_draws - interest - repayments
    expected_equity = probability * equity_success + (1 - probability) * failure
    closing_debt = balance - np.cumsum(repayments)
    monthly_rate = (1 + discount_rate) ** (1 / 12) - 1
    discounts = (1 + monthly_rate) ** np.arange(months + 1)
    pv = lambda values: float(np.sum(values / discounts))
    monthly_irr = irr(expected_equity.tolist())
    blockers = []
    if not lbc_known:
        blockers.append('LBC is missing; reported numeric values exclude an unknown charge and are not decision-ready')
    elif x.assessed_lbc_m is None:
        blockers.append('LBC uses a simplified additional-area rate screen; verify pre/post use, sector, tenure and chargeable value or supply assessed_lbc_m')
    if not x.inputs_verified:
        blockers.append('Asset values, planning, dates, taxes, costs and approval assumptions are not verified')
    round_vector = lambda values: np.round(values, 8).tolist()
    equity_pv = None
    if x.equity_discount_rate is not None:
        if not math.isfinite(x.equity_discount_rate) or x.equity_discount_rate <= -1:
            raise ValueError('equity discount rate must be finite and above -1')
        equity_pv = float(np.sum(expected_equity / (1 + x.equity_discount_rate) ** (np.arange(months + 1) / 12)))
    return {
        'action': x.action, 'monthly_cashflows_m': round_vector(incremental),
        'npv_m': round(pv(incremental), 6), 'incremental_npv_m': round(pv(incremental), 6),
        'npv_basis': 'expected unlevered incremental cashflows versus Hold' if x.action != 'Acquire' else 'expected unlevered acquisition investment versus no investment',
        'project_npv_m': round(pv(expected_project), 6), 'hold_npv_m': round(pv(hold), 6),
        'success_project_npv_m': round(pv(success), 6), 'failure_project_npv_m': round(pv(failure), 6),
        'equity_npv_m': round(equity_pv, 6) if equity_pv is not None else None,
        'equity_discount_rate': x.equity_discount_rate,
        'irr_annual': (1 + monthly_irr) ** 12 - 1 if monthly_irr is not None else None,
        'irr_basis': 'probability-weighted equity investment, including current-asset opportunity cost; not incremental IRR',
        'irr_status': 'conventional_root' if monthly_irr is not None else 'unavailable_or_nonconventional_cashflows',
        'monthly_project_cashflows_m': round_vector(expected_project),
        'monthly_hold_cashflows_m': round_vector(hold),
        'monthly_equity_cashflows_m': round_vector(expected_equity),
        'success_unlevered_cashflows_m': round_vector(success),
        'success_equity_cashflows_m': round_vector(equity_success),
        'failure_unlevered_cashflows_m': round_vector(failure),
        'monthly_debt_draws_m': round_vector(debt_draws),
        'monthly_interest_m': round_vector(interest),
        'monthly_debt_repayments_m': round_vector(repayments),
        'monthly_closing_debt_m': round_vector(closing_debt),
        'financing_basis': 'success-conditional development debt; draws added to equity, interest paid monthly, principal repaid on sale; excluded from unlevered NPV',
        'current_asset_opportunity_cost_m': opportunity, 'additional_gfa_sqm': additional,
        'construction_gfa_sqm': construction_gfa, 'construction_m': round(construction, 6),
        'professional_fees_m': round(fees, 6), 'contingency_m': round(contingency, 6),
        'total_development_m': round(development, 6), 'lbc': lbc,
        'buyer_stamp_duty_m': round(bsd, 6), 'seller_stamp_duty_m': round(ssd, 6),
        'financing_interest_m': round(float(interest.sum()), 6),
        'tenant_relocation_m': x.tenant_relocation_m, 'demolition_m': x.demolition_m,
        'gross_terminal_value_m': round(gross_value, 6), 'net_sale_proceeds_m': round(net_sale, 6),
        'debt_repayment_m': round(float(repayments.sum()), 6),
        'total_debt_draws_m': round(float(debt_draws.sum()), 6),
        'approval_probability': probability, 'failure_cost_m': round(fees * (1 - probability), 6),
        'months': months, 'disposal_date': disposal_date.isoformat(),
        'valuation_status': 'incomplete_inputs' if blockers else 'calculated_with_verified_inputs',
        'decision_ready': not blockers, 'verification_required': bool(blockers),
        'excluded_costs': ['unassessed LBC'] if not lbc_known else [],
        'decision_blockers': blockers,
        'assumptions': ['predevelopment fees are sunk before approval; failed approval retains Hold cashflows',
                        'NOI yield, lease-up, financing, growth and approval are supplied assumptions, not calibrated forecasts',
                        'existing debt, corporate income tax, ABSD, tenure top-up and other unprovided levies are excluded; verify applicability'],
    }
