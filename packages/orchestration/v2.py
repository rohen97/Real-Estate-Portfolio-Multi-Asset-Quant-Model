from __future__ import annotations
from pathlib import Path
import joblib
from packages.forecasting.ensemble import predict
from packages.valuation.lease_cashflow import lease_cashflow
from packages.actions.real_options import evaluate_actions,real_options
from packages.scenarios.engine import simulate_actions
from packages.orchestration.engine import inputs_for_asset
from packages.zoning.engine import calculate_capacity
from packages.legacy.scorecard import score as legacy_score
from packages.zoning.ura import surrounding_development_context
from packages.selection.engine import evaluate_selection,load_transformation_zones
from packages.market.public_data import load_snapshot,context_for_asset
ROOT=Path(__file__).resolve().parents[2]
STAGES=['Pre-application','Planning submission','Technical clearances','Committee/public review','Conditions discharge','Building permission']
def run_twin(twin:dict,model_dir:Path,legacy_input:dict|None=None,seed=20260923):
 asset=twin['asset'];financials=sorted(twin.get('financials',[]),key=lambda x:int(x['Fiscal Year']));latest=financials[-1] if financials else None;leases=twin.get('leases',[]);zoning_assumptions,_,_,_,_=inputs_for_asset(asset);capacity=calculate_capacity(zoning_assumptions,seed).__dict__
 if latest:
  features={'prior_noi':float(latest['NOI SGD m']),'occupancy':float(latest['Occupancy %']),'cap_rate':float(latest['Cap Rate %']),'maintenance_capex':float(latest.get('Maintenance Capex SGD m') or 0),'prior_valuation':float(latest['Valuation SGD m']),'year_index':int(latest['Fiscal Year'])+1-2020};noi_forecast=predict(model_dir/'noi_ensemble.joblib',features);current_value=float(latest['Valuation SGD m']);current_noi=float(latest['NOI SGD m'])
 else:noi_forecast=None;current_value=65;current_noi=3
 lease_model=lease_cashflow(leases) if leases else None
 if lease_model:current_noi=lease_model['noi_m'][0]
 action_values=evaluate_actions(current_value,current_noi,capacity.get('residual_value_m',0));risk=simulate_actions(action_values,draws=5000,seed=seed);options=real_options(risk,current_noi);preferred=max(risk,key=lambda x:x['expected_npv_m']-.3*max(0,x['cvar_95_m']));zone=(asset.get('ura_zoning',{}).get('matches') or [{}])[0];surroundings=surrounding_development_context(ROOT/'data/processed/ura_mp2025.sqlite',asset['latitude'],asset['longitude'],500,zone.get('objectid')) if asset.get('latitude') is not None else {'status':'unavailable'};market=context_for_asset(asset,load_snapshot(ROOT));selection=evaluate_selection({**asset,'synthetic_financials':False},capacity,risk,surroundings,market,current_value,current_noi,.078,5,load_transformation_zones(ROOT));preferred=next((x for x in risk if x['action']==selection['preferred_action']),preferred)
 approval_model_path=model_dir/'approval_survival.joblib';approval=[]
 if approval_model_path.exists():
  model=joblib.load(approval_model_path)
  for stage in STAGES:approval.append({'stage':stage,'probability':round(model.predict_stage(stage),4),'duration':model.durations.get(stage)})
 legacy=legacy_score(legacy_input['financial'],legacy_input['operational'],legacy_input['market'],legacy_input['sustainability']) if legacy_input else None
 return {'asset_id':asset['asset_id'],'asset_name':asset['name'],'portfolio_source':asset.get('source_rows'),'synthetic_history':twin.get('synthetic_history',False),'noi_forecast':noi_forecast,'lease_cashflow':lease_model,'capacity':capacity,'approval_forecast':approval,'actions':risk,'real_options':options,'surrounding_context':surroundings,'market_context':market,'selection':selection,'recommendation':preferred,'legacy':legacy,'legacy_agreement':legacy['quadrant']=={'Hold':'Retain','Retrofit':'Retrofit','Repurpose':'Repurpose','Redevelop':'Repurpose','Sell':'Release'}[preferred['action']] if legacy else None,'model_version':'economic-model-v2-0.1'}
