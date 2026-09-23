from __future__ import annotations
from dataclasses import dataclass,asdict

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
 cash=[];noi=e.current_noi_m
 for year in range(1,e.holding_years+1):
  noi*=1+e.market_rent_growth;cash.append(noi)
 terminal=noi*(1+e.market_rent_growth)/e.cap_rate*(1-e.selling_cost_rate);cash[-1]+=terminal
 pv=sum(v/(1+e.discount_rate)**(i+1) for i,v in enumerate(cash));return {'value_m':round(pv,2),'cashflows_m':[round(x,2) for x in cash],'terminal_value_m':round(terminal,2)}

def action_plans(e:AssetEconomics,capacity:dict)->list[ActionPlan]:
 option=max(0,float(capacity.get('residual_value_m',0)))
 return [ActionPlan('Hold',1.5,.1,.01,0,.0,.98,.25),ActionPlan('Retrofit',max(5,e.current_value_m*.08),.6,.1,.05,.04,.9,1.5),ActionPlan('Repurpose',max(12,e.current_value_m*.2),1.2,.22,.12,.12,.72,2.5),ActionPlan('Redevelop',max(25,e.current_value_m*.42),2.2,.45,.18,.25,.62,4),ActionPlan('Sell',0,0,0,0,0,.97,.75,e.current_value_m*(1-e.selling_cost_rate))]

def value_actions(e:AssetEconomics,capacity:dict)->list[dict]:
 baseline=dcf(e)['value_m'];out=[]
 for plan in action_plans(e,capacity):
  if plan.action=='Sell': after=plan.sale_proceeds_m;failure_cost=0;capital=-plan.sale_proceeds_m
  else:
   changed=AssetEconomics(**asdict(e));changed.current_noi_m=e.current_noi_m*(1+plan.noi_uplift);changed.occupancy=min(.99,e.occupancy+plan.occupancy_uplift);changed.current_value_m=e.current_value_m*(1+plan.terminal_value_uplift);after=dcf(changed)['value_m']+float(capacity.get('residual_value_m',0))*(.15 if plan.action=='Repurpose' else .45 if plan.action=='Redevelop' else 0);failure_cost=plan.capex_m*(1-plan.success_probability)*.55;capital=plan.capex_m
  financing=plan.capex_m*.045*plan.execution_years/2;disruption=e.current_noi_m*plan.disruption_years*.7;npv=after-baseline-plan.capex_m-financing-disruption-failure_cost
  out.append({'action':plan.action,'incremental_npv_m':round(npv,2),'pv_after_m':round(after,2),'pv_without_m':round(baseline,2),'capex_m':round(capital,2),'financing_cost_m':round(financing,2),'disruption_cost_m':round(disruption,2),'failure_cost_m':round(failure_cost,2),'success_probability':plan.success_probability,'execution_years':plan.execution_years,'source_quality':e.source_quality})
 return out

def proxy_economics(asset:dict)->AssetEconomics:
 segments=' '.join(asset.get('segments',[])).lower();rent=asset.get('asking_rent_monthly_sgd');size=asset.get('size_from_sqft')
 if rent and size: annual=rent*12/1e6/.9;value=annual/(.052 if 'industrial' in segments else .047)
 else:
  base=42 if 'residential' in segments else 85 if 'hotel' in segments else 65 if 'commercial' in segments or 'mall' in segments else 35;value=base
 noi=value*(.052 if 'industrial' in segments else .045)
 return AssetEconomics(round(value,2),round(noi,2),source_quality='illustrative proxy - replace with observed company financials')
