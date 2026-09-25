from datetime import date
import math
import pytest
from packages.market.official import parse_dataset, build_snapshot, quarter_id
from packages.market.public_data import context_for_asset
from packages.selection.engine import evaluate_selection, underwriting_readiness
from packages.data.underwriting_import import number


def test_official_quarters_exclude_future_and_do_not_bridge_missing_quarters():
    spec = {'id':'test','agency':'test','rows':{'Index':('office','price')}}
    payload = {'success':True,'result':{'total':1,'records':[{'DataSeries':'Index','20252Q':100,'20261Q':105,'20262Q':110,'20264Q':200}]}}
    series = parse_dataset(payload,spec,date(2026,9,25))
    result = build_snapshot(series,date(2026,9,25),{})['market_indicators']['office']
    assert result['price_period']=='2026-Q2'
    assert result['price_qoq']==pytest.approx(110/105-1)
    assert result['price_yoy']==pytest.approx(.1)
    earlier=build_snapshot(series,date(2026,3,31),{})['market_indicators']['office']
    assert earlier['price_qoq'] is None
    assert quarter_id('2026 2Q')==quarter_id('2026-Q2')


def test_partial_api_response_is_rejected():
    with pytest.raises(ValueError,match='Incomplete'):
        parse_dataset({'success':True,'result':{'total':10,'records':[{}]}},{'rows':{}},date.today())


def test_unknown_or_mixed_segment_does_not_inherit_residential():
    snapshot={'market_indicators':{'private_residential':{'price_qoq':.1}}}
    assert context_for_asset({'segments':['Mixed use']},snapshot)['indicators']=={}
    assert context_for_asset({'segments':['Logistics']},snapshot)['market_segment']=='industrial'


def test_nonfinite_underwriting_values_are_missing():
    assert number('nan') is None
    assert number(float('inf')) is None


def test_context_options_cannot_manufacture_alpha_or_change_rank():
    actions=[{'action':'Hold','expected_npv_m':0,'cvar_95_m':0}, {'action':'Retrofit','expected_npv_m':8,'cvar_95_m':20}, {'action':'Sell','expected_npv_m':4,'cvar_95_m':1}]
    asset={'segments':['Residential'],'latitude':1.3,'longitude':103.8,'tenure_hint':{'type':'Freehold'}}
    capacity={'statutory_gfa_sqm':30000,'unused_economic_gfa_sqm':12000,'residual_value_m':1000}
    result=evaluate_selection(asset,capacity,actions,None,{'indicators':{'price_qoq':.8}},100,5)
    assert result['preferred_action']=='Sell'
    assert result['risk_adjusted_score_m']==pytest.approx(3.7)
    assert result['annual_expected_alpha'] is None
    assert result['view_risk']['probability'] is None
    assert not result['enbloc']['included_in_selection']
    assert result['signal']=='Data Required / Monitor'
    assert result['opportunity']['break_even_additional_pv_cost_m']==4


def test_stale_or_missing_evidence_cannot_become_observed_by_flag():
    result=underwriting_readiness({'synthetic_financials':False},date(2026,9,25))
    assert not result['ready'] and 'verified_financial_evidence' in result['missing']


@pytest.mark.parametrize('value,horizon,risk', [(float('nan'),5,0),(100,.5,0),(100,5,float('nan'))])
def test_nonfinite_valuation_or_risk_and_fractional_horizon_are_rejected(value,horizon,risk):
    with pytest.raises(ValueError):
        evaluate_selection({}, {}, [{'action':'Hold','expected_npv_m':0,'cvar_95_m':risk}],
                           None, {}, value, 5, holding_years=horizon)
