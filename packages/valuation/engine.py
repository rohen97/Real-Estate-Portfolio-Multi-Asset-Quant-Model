from __future__ import annotations
from dataclasses import dataclass
import math
from packages.actions.real_options import evaluate_specifications, npv

@dataclass
class AssetEconomics:
 current_value_m:float
 current_noi_m:float
 occupancy:float=.9
 market_rent_growth:float=.025
 vacancy_target:float=.07
 cap_rate:float=.0475
 discount_rate:float=.078
 selling_cost_rate:float=.025
 holding_years:int=10
 source_quality:str='proxy_from_asset_class'

@dataclass
class ActionPlan:
 action:str
 capex_m:float
 disruption_years:float
 noi_uplift:float
 occupancy_uplift:float
 terminal_value_uplift:float
 success_probability:float
 execution_years:float
 sale_proceeds_m:float=0

def dcf(e:AssetEconomics)->dict:
 if not all(math.isfinite(value) for value in (e.current_noi_m,e.current_value_m,e.market_rent_growth,e.cap_rate,e.discount_rate,e.selling_cost_rate)):
  raise ValueError('DCF inputs must be finite')
 if e.holding_years < 1 or int(e.holding_years) != e.holding_years or e.cap_rate <= 0 or e.market_rent_growth <= -1 or not 0 <= e.selling_cost_rate < 1:
  raise ValueError('invalid DCF horizon, cap rate, growth or selling cost')
 cash=[];noi=e.current_noi_m
 for year in range(1,e.holding_years+1):
  noi*=1+e.market_rent_growth;cash.append(noi)
 terminal=noi*(1+e.market_rent_growth)/e.cap_rate*(1-e.selling_cost_rate);cash[-1]+=terminal
 pv=npv(e.discount_rate,cash,start_period=1);return {'value_m':round(pv,6),'cashflows_m':[round(x,6) for x in cash],'terminal_value_m':round(terminal,6),'cashflow_start_year':1,'cashflow_basis':'unlevered year-end NOI and forward-NOI terminal value net of selling costs'}

def action_plans(e:AssetEconomics,capacity:dict)->list[ActionPlan]:
 return [ActionPlan('Hold',0,0,0,0,0,1,0),ActionPlan('Retrofit',max(5,e.current_value_m*.08),.6,.1,.05,0,.9,1.5),ActionPlan('Repurpose',max(12,e.current_value_m*.2),1.2,.22,.12,0,.72,2.5),ActionPlan('Redevelop',max(25,e.current_value_m*.42),2.2,.45,.18,0,.62,4),ActionPlan('Sell',0,0,0,0,0,1,0,e.current_value_m*(1-e.selling_cost_rate))]

def value_actions(e:AssetEconomics,capacity:dict)->list[dict]:
 specifications=[]
 for plan in action_plans(e,capacity):
  specifications.append({'action':plan.action,'capex_m':plan.capex_m,'noi_uplift':plan.noi_uplift,'disruption_rate':min(1.,plan.disruption_years*.7/max(plan.execution_years,1e-9)),'duration_years':plan.execution_years,'success_probability':plan.success_probability,'terminal_uplift':plan.terminal_value_uplift})
 out=evaluate_specifications(e.current_value_m,e.current_noi_m,float(capacity.get('residual_value_m',0)),specifications,e.discount_rate,e.holding_years,e.cap_rate,e.market_rent_growth,e.selling_cost_rate)
 for result,plan in zip(out,action_plans(e,capacity)):
  result['source_quality']=e.source_quality
  result.update({'current_value_m':e.current_value_m,'base_noi_m':e.current_noi_m,'reference_cap_rate':e.cap_rate,'reference_rent_growth':e.market_rent_growth,'baseline_vacancy':e.vacancy_target})
  result['disruption_cost_m']=round(e.current_noi_m*plan.disruption_years*.7,6)
  result['disruption_cost_basis']='undiscounted screening diagnostic; already included in cashflows'
  result['occupancy_uplift_treatment']='included in total NOI uplift; not added a second time'
 return out

def proxy_economics(asset:dict)->AssetEconomics:
 segments=' '.join(asset.get('segments',[])).lower();rent=asset.get('asking_rent_monthly_sgd');size=asset.get('size_from_sqft')
 industrial=any(term in segments for term in ('industrial','warehouse','logistics','storage','factory'))
 hospitality=any(term in segments for term in ('hotel','hospitality','serviced residence'))
 commercial=any(term in segments for term in ('commercial','mall','retail','office','mixed use','mixed-use','business park'))
 if rent and size: annual=rent*12/1e6/.9;value=annual/(.052 if industrial else .047)
 else:
  base=85 if hospitality else 65 if commercial else 35 if industrial else 42 if 'residential' in segments else 35;value=base
 noi=value*(.052 if industrial else .045)
 return AssetEconomics(round(value,2),round(noi,2),source_quality='illustrative proxy - replace with observed company financials')
