from pathlib import Path
import json,pytest
from packages.legacy.scorecard import score
from packages.valuation.lease_cashflow import lease_cashflow
from packages.actions.real_options import evaluate_actions,real_options
from packages.optimisation.multiperiod import optimise_multi_period
from packages.governance.gates import require_production_model,GovernanceError
ROOT=Path(__file__).resolve().parents[2]
def test_frozen_legacy_scorecard_corrects_deck_values():
 r=score(85,80,90,75);assert r['current_performance']==82.9167;assert r['future_potential']==84.375;assert r['quadrant']=='Retain'
def test_lease_level_cashflow():
 leases=[{'Area sqm':1000,'Passing Rent SGD pa':600000,'Market Rent SGD pa':660000,'Lease Expiry':'2028-12-31','Tenant Credit Grade':'A','Collection %':.99}];r=lease_cashflow(leases);assert len(r['noi_m'])==10;assert r['present_value_m']>0;assert all(0<=x<=1 for x in r['occupancy'])
def test_action_and_real_options():
 actions=evaluate_actions(120,5.8,14);low_cap_actions=evaluate_actions(120,5.8,14,terminal_cap_rate=.035);opts=real_options(actions,5.8);assert len(actions)==5;assert set(opts)>={'Wait','Phase','Abandon','Expand'};assert low_cap_actions[0]['incremental_npv_m']>actions[0]['incremental_npv_m']
def test_multiperiod_optimizer():
 actions=evaluate_actions(100,5,10)
 risk=[{**x,'expected_npv_m':x['incremental_npv_m'],'cvar_95_m':max(0,-x['incremental_npv_m']),'probability_of_loss':.2} for x in actions]
 assets=[{'asset_id':f'A{i}','name':f'Asset {i}','base_noi_m':5,'actions':risk} for i in range(4)];r=optimise_multi_period(assets,horizon_years=5,total_capital_budget_m=200,minimum_liquidity_m=20,max_concurrent_projects=2);assert r['feasible'];assert len(r['selections'])==4;assert len(r['annual_plan'])==5
def test_synthetic_model_governance_gate():
 with pytest.raises(GovernanceError):require_production_model({'synthetic_training':True,'artifacts':[1]},False)
 assert require_production_model({'synthetic_training':True,'artifacts':[1]},True)
def test_v2_outputs_exist():
 pilot_path=ROOT/'data/processed/pilot_model_v2.json';pilot_path=pilot_path if pilot_path.exists() else ROOT/'data/examples/demo_pilot_model_v2.json';back_path=ROOT/'data/processed/backtest_report.json';back_path=back_path if back_path.exists() else ROOT/'data/examples/demo_backtest_report.json';reg_path=ROOT/'models/registry/portfolio-forecasting-latest.json';reg_path=reg_path if reg_path.exists() else ROOT/'data/examples/demo_model_registry.json';pilot=json.loads(pilot_path.read_text());backtest=json.loads(back_path.read_text());registry=json.loads(reg_path.read_text());assert len(pilot['assets'])==10;assert backtest['status'] in ('synthetic_pilot_backtest','public_synthetic_demo');assert registry['synthetic_training'] is True
