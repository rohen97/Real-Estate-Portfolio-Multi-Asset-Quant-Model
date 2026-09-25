"""En-bloc residual screening with self-consistent acquisition duty and fallback."""
from __future__ import annotations

from dataclasses import dataclass
import math
from scipy.stats import binom

from packages.economics.singapore_costs import buyer_stamp_duty, land_betterment_charge


@dataclass
class EnBlocInputs:
    current_strata_value_m: float
    site_area_sqm: float
    existing_gfa_sqm: float
    legal_gpr: float
    nla_efficiency: float
    sale_price_per_nla_sqm: float
    construction_cost_per_gfa_sqm: float
    lbc_rate_per_sqm: float | None
    tenure_remaining_years: float | None
    owners_count: int
    required_consent: float = .8
    professional_rate: float = .12
    finance_rate: float = .08
    marketing_rate: float = .025
    demolition_m: float = 2
    tenant_cost_m: float = 0
    developer_margin_rate: float = .2
    failed_attempts: int = 0
    timeline_years: float = 3
    residential_share: float = 1
    discount_rate: float = .078
    hold_value_growth: float = .025
    attempt_cost_m: float = 0
    assessed_lbc_m: float | None = None
    inputs_verified: bool = False
    observed_consent_share: float | None = None


def evaluate_enbloc(x: EnBlocInputs):
    for name in ('current_strata_value_m', 'site_area_sqm', 'existing_gfa_sqm', 'legal_gpr',
                 'sale_price_per_nla_sqm', 'construction_cost_per_gfa_sqm', 'professional_rate',
                 'finance_rate', 'marketing_rate', 'demolition_m', 'tenant_cost_m',
                 'developer_margin_rate', 'timeline_years', 'attempt_cost_m'):
        if not math.isfinite(getattr(x, name)) or getattr(x, name) < 0:
            raise ValueError(f'{name} must be finite and nonnegative')
    if x.owners_count < 1 or int(x.owners_count) != x.owners_count:
        raise ValueError('owners_count must be a positive integer')
    if not 0 < x.required_consent <= 1 or not 0 <= x.residential_share <= 1 or not 0 <= x.nla_efficiency <= 1:
        raise ValueError('invalid consent, residential share or NLA efficiency')
    if min(x.discount_rate, x.hold_value_growth) <= -1:
        raise ValueError('discount and growth rates must exceed -1')
    allowable = x.site_area_sqm * x.legal_gpr
    additional = max(0., allowable - x.existing_gfa_sqm)
    gdv = allowable * x.nla_efficiency * x.sale_price_per_nla_sqm / 1e6
    construction = allowable * x.construction_cost_per_gfa_sqm / 1e6
    professional = construction * x.professional_rate
    finance = (construction + professional) * x.finance_rate
    marketing = gdv * x.marketing_rate
    if x.assessed_lbc_m is not None:
        if not math.isfinite(x.assessed_lbc_m) or x.assessed_lbc_m < 0:
            raise ValueError('assessed LBC must be finite and nonnegative')
        lbc = {'status': 'assessed_input', 'total_sgd': x.assessed_lbc_m * 1e6,
               'source': 'user-supplied assessed LBC; verify assessment date and scope'}
    else:
        lbc = land_betterment_charge(additional, x.lbc_rate_per_sqm)
    lbc_known = lbc.get('total_sgd') is not None
    lbc_m = lbc['total_sgd'] / 1e6 if lbc_known else 0.
    developer_margin = gdv * x.developer_margin_rate
    residual_before_duty = (gdv - construction - professional - finance - marketing - lbc_m
                            - developer_margin - x.demolition_m - x.tenant_cost_m)
    # Duty depends on the offered land consideration; solving against current
    # strata value makes the previous residual fail its own cost reconciliation.
    if residual_before_duty > 0:
        lo, hi = 0., residual_before_duty
        for _ in range(70):
            mid = (lo + hi) / 2
            duty = buyer_stamp_duty(mid * 1e6, x.residential_share)['total_sgd'] / 1e6
            if mid + duty > residual_before_duty:
                hi = mid
            else:
                lo = mid
        max_land = lo
    else:
        max_land = residual_before_duty
    bsd = buyer_stamp_duty(max(0., max_land) * 1e6, x.residential_share)['total_sgd'] / 1e6
    premium = max_land / x.current_strata_value_m - 1 if x.current_strata_value_m else 0.
    tenure_factor = 1 if x.tenure_remaining_years is None else min(1., max(.25, x.tenure_remaining_years / 99))
    fragmentation = max(0., math.log(x.owners_count) / math.log(500))
    logit = -1.7 + 5 * max(0., premium) + 1.2 * tenure_factor - 1.1 * fragmentation - .65 * x.failed_attempts
    support = 1 / (1 + math.exp(-max(-700., min(700., logit))))
    required_owners = math.ceil(x.required_consent * x.owners_count)
    if x.observed_consent_share is not None:
        if not 0 <= x.observed_consent_share <= 1:
            raise ValueError('observed consent share must be between zero and one')
        consent = float(x.observed_consent_share >= x.required_consent)
        consent_method = 'supplied consent share compared with supplied threshold; legal voting basis requires verification'
    else:
        consent = float(binom.sf(required_owners - 1, x.owners_count, support))
        consent_method = 'uncalibrated independent equal-weight owner-support screen; not a legal vote or observed approval probability'
    success = consent if max_land > 0 else 0.
    discount = (1 + x.discount_rate) ** x.timeline_years
    hold_terminal = x.current_strata_value_m * (1 + x.hold_value_growth) ** x.timeline_years
    conditional_sale = max(0., max_land) / discount
    discounted_sale = success * conditional_sale
    fallback = (1 - success) * hold_terminal / discount
    incremental = success * (max(0., max_land) - hold_terminal) / discount - x.attempt_cost_m
    blockers = []
    if not lbc_known:
        blockers.append('LBC is missing; residual and indicative values exclude an unknown charge')
    elif x.assessed_lbc_m is None:
        blockers.append('LBC is a simplified additional-area rate screen; supply a verified assessed charge')
    if not x.inputs_verified:
        blockers.append('Site, market, costs, taxes and ownership/voting assumptions are unverified')
    if x.observed_consent_share is None:
        blockers.append('Consent uses an uncalibrated equal-owner proxy; actual legal voting shares are unavailable')
    rounded = lambda value: round(float(value), 6)
    return {
        'allowable_gfa_sqm': rounded(allowable), 'additional_gfa_sqm': rounded(additional),
        'gross_development_value_m': rounded(gdv), 'construction_m': rounded(construction),
        'professional_m': rounded(professional), 'finance_m': rounded(finance),
        'marketing_m': rounded(marketing), 'lbc': lbc,
        'developer_margin_m': rounded(developer_margin), 'buyer_stamp_duty_m': rounded(bsd),
        'demolition_m': x.demolition_m, 'tenant_cost_m': x.tenant_cost_m,
        'residual_before_buyer_duty_m': rounded(residual_before_duty),
        'maximum_land_value_m': rounded(max_land), 'premium_over_current_value': rounded(premium),
        'residual_reconciliation_error_m': rounded(residual_before_duty - max_land - bsd),
        'individual_owner_support_probability': rounded(support),
        'owner_consent_probability': rounded(consent), 'success_probability': rounded(success),
        'required_consent': x.required_consent, 'required_owner_count_screen': required_owners,
        'consent_method': consent_method,
        'expected_discounted_enbloc_value_m': rounded(discounted_sale),
        'conditional_discounted_sale_value_m': rounded(conditional_sale),
        'expected_retained_asset_value_m': rounded(fallback),
        'expected_total_terminal_value_m': rounded(discounted_sale + fallback - x.attempt_cost_m),
        'incremental_npv_vs_hold_m': rounded(incremental),
        'hold_terminal_value_m': rounded(hold_terminal), 'attempt_cost_m': x.attempt_cost_m,
        'timeline_years': x.timeline_years, 'discount_rate': x.discount_rate,
        'value_basis': 'legacy expected value is success-weighted sale component only; incremental value includes retained-asset fallback versus same-date Hold',
        'finance_basis': 'supplied effective development financing allowance on construction and professional costs; acquisition finance and tenure top-up are excluded',
        'decision_ready': not blockers, 'verification_required': bool(blockers),
        'valuation_status': 'incomplete_inputs' if blockers else 'calculated_with_verified_inputs',
        'excluded_costs': ['unassessed LBC'] if not lbc_known else [], 'decision_blockers': blockers,
    }
