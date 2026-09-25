from datetime import date
import pytest
from packages.valuation.lease_cashflow import lease_cashflow
from packages.zoning.approval import approval_path


def lease(expiry='2026-12-31',collection=1):
    return {'Area sqm':1000,'Passing Rent SGD pa':1200000,'Market Rent SGD pa':1200000,
            'Lease Expiry':expiry,'Collection %':collection}


def test_vacancy_occurs_once_after_expiry_not_every_future_year():
    result=lease_cashflow([lease()],as_of=date(2027,1,1),horizon_years=3,rent_growth=0,
                          opex_ratio=0,renewal_probability=0,downtime_months=4)
    assert result['gross_rent_m']==pytest.approx([.8,1.2,1.2])
    assert result['occupancy']==pytest.approx([2/3,1,1],abs=1e-6)


def test_expiry_does_not_remove_rent_earned_earlier_in_the_same_year():
    result=lease_cashflow([lease('2027-06-30')],as_of=date(2027,1,1),horizon_years=2,
                          rent_growth=0,opex_ratio=0,renewal_probability=0,downtime_months=4)
    assert result['gross_rent_m']==pytest.approx([.8,1.2])
    assert result['monthly_gross_rent_m'][:6]==pytest.approx([.1]*6)


def test_zero_collection_is_not_replaced_with_credit_proxy():
    result=lease_cashflow([lease(collection=0)],as_of=date(2026,1,1))
    assert result['present_value_m']==0


def test_monthly_pv_reconciles_to_exported_schedule():
    result=lease_cashflow([lease('2030-12-31')],as_of=date(2026,1,1),horizon_years=2)
    expected=sum(value/(1.078)**((i+1)/12) for i,value in enumerate(result['monthly_cashflows_m']))
    assert result['present_value_m']==pytest.approx(expected,abs=1e-6)


def test_approval_success_duration_and_probabilities_are_explicit():
    with pytest.raises(ValueError):approval_path({'Pre-application':1.5})
    result=approval_path({'Pre-application':0})
    assert result['overall_probability']==0
    assert result['p50_success_months'] is None
    assert result['redesign_probability_status'].startswith('legacy alias')
