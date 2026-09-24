from __future__ import annotations
from dataclasses import dataclass
import numpy as np
@dataclass
class ActionDefinition:
 action:str;capex_rate:float;noi_uplift:float;disruption_rate:float;duration_years:int;success_probability:float;terminal_uplift:float
ACTIONS=[ActionDefinition('Hold',.01,.01,.01,1,.99,0),ActionDefinition('Retrofit',.08,.10,.12,2,.9,.04),ActionDefinition('Repurpose',.22,.24,.35,3,.75,.14),ActionDefinition('Redevelop',.45,.48,.8,5,.62,.28),ActionDefinition('Sell',0,0,0,1,.98,0)]
def npv(rate,cashflows):return sum(v/(1+rate)**i for i,v in enumerate(cashflows))
def evaluate_actions(current_value_m,base_noi_m,capacity_option_m,discount_rate=.078,horizon=10,terminal_cap_rate=.05):
 results=[]
 terminal_cap_rate=max(.02,float(terminal_cap_rate));base=[base_noi_m*(1.02)**y for y in range(1,horizon+1)];base[-1]+=base_noi_m*(1.02)**horizon/terminal_cap_rate;base_pv=npv(discount_rate,base)
 for spec in ACTIONS:
  if spec.action=='Sell':after=current_value_m*.975;capex=-after;failure=0;cash=[after]
  else:
   capex=current_value_m*spec.capex_rate;cash=[]
   for y in range(1,horizon+1):
    disruption=spec.disruption_rate if y<=spec.duration_years else 0;noi=base_noi_m*(1+spec.noi_uplift)*(1.025)**y*(1-disruption);cash.append(noi)
   cash[-1]+=base_noi_m*(1+spec.noi_uplift)*(1.025)**horizon/terminal_cap_rate*(1+spec.terminal_uplift)+capacity_option_m*(.2 if spec.action=='Repurpose' else .55 if spec.action=='Redevelop' else 0);after=npv(discount_rate,cash);failure=capex*(1-spec.success_probability)*.55
  financing=max(0,capex)*.045*spec.duration_years/2;incremental=after-base_pv-max(0,capex)-financing-failure;results.append({'action':spec.action,'incremental_npv_m':round(incremental,3),'pv_after_m':round(after,3),'pv_without_m':round(base_pv,3),'capex_m':round(capex,3),'financing_cost_m':round(financing,3),'failure_cost_m':round(failure,3),'success_probability':spec.success_probability,'execution_years':spec.duration_years,'annual_cashflows_m':[round(x,3) for x in cash]})
 return results
def real_options(actions:list[dict],base_noi_m,discount_rate=.078):
 by={x['action']:x for x in actions};redevelop=by['Redevelop'];repurpose=by['Repurpose'];hold=by['Hold'];upside=max(redevelop['incremental_npv_m'],repurpose['incremental_npv_m']);wait_value=base_noi_m/(1+discount_rate)+max(0,upside)/(1+discount_rate)-max(0,upside)*.12;phase_value=max(0,redevelop['incremental_npv_m'])*.65+max(0,repurpose['incremental_npv_m'])*.25;abandon_value=max(0,-redevelop['p10_npv_m']) if 'p10_npv_m' in redevelop else max(0,-redevelop['incremental_npv_m'])*.2;return {'Wait':round(wait_value,3),'Phase':round(phase_value,3),'Abandon':round(abandon_value,3),'Expand':round(max(0,upside)*.18,3),'method':'Decision-tree real-option approximations; calibrate with observed project transitions'}
