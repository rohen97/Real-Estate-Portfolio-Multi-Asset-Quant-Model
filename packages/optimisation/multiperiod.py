from __future__ import annotations
import math
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
DEVELOPMENT={'Retrofit','Repurpose','Redevelop'}
DISRUPTION={'Hold':0,'Retrofit':.12,'Repurpose':.35,'Redevelop':.8,'Sell':1}
def optimise_multi_period(asset_actions:list[dict],horizon_years=5,total_capital_budget_m=500,annual_capital_budgets=None,minimum_liquidity_m=50,max_concurrent_projects=8,max_development_share=.45,minimum_noi_ratio=.7,cvar_penalty=.3):
 annual_capital_budgets=annual_capital_budgets or [total_capital_budget_m/horizon_years]*horizon_years;options=[]
 for asset in asset_actions:
  base_noi=float(asset.get('base_noi_m') or 0)
  for action in asset['actions']:
   name=action['action'];duration=max(1,int(math.ceil(action.get('execution_years',1))));starts=[0] if name in ('Hold','Sell') else list(range(max(1,horizon_years-duration+1)))
   for start in starts:
    capex=[0.]*horizon_years;receipts=[0.]*horizon_years;lost_noi=[0.]*horizon_years
    if name=='Sell':receipts[start]=max(0,-float(action.get('capex_m',0)));lost_noi[start:]=[base_noi]*(horizon_years-start)
    else:
     annual=max(0,float(action.get('capex_m',0)))/duration
     for y in range(start,min(horizon_years,start+duration)):capex[y]=annual;lost_noi[y]=base_noi*DISRUPTION.get(name,0)
    options.append({'asset_id':asset['asset_id'],'asset_name':asset['name'],'base_noi_m':base_noi,'action':name,'start_year':start+1,'duration_years':duration,'expected_npv_m':float(action['expected_npv_m']),'cvar_95_m':float(action.get('cvar_95_m',0)),'probability_of_loss':float(action.get('probability_of_loss',0)),'capex_schedule_m':capex,'receipt_schedule_m':receipts,'capex_m':sum(capex)-sum(receipts),'lost_noi_m':lost_noi})
 n=len(options);c=-np.array([o['expected_npv_m']-cvar_penalty*max(0,o['cvar_95_m']) for o in options]);constraints=[]
 asset_ids=sorted({o['asset_id'] for o in options})
 for aid in asset_ids:constraints.append(LinearConstraint(np.array([1 if o['asset_id']==aid else 0 for o in options]),1,1))
 for y in range(horizon_years):constraints.append(LinearConstraint(np.array([o['capex_schedule_m'][y]-o['receipt_schedule_m'][y] for o in options]),-np.inf,annual_capital_budgets[y]))
 cumulative=np.zeros(n)
 for y in range(horizon_years):
  cumulative+=np.array([o['capex_schedule_m'][y]-o['receipt_schedule_m'][y] for o in options]);constraints.append(LinearConstraint(cumulative.copy(),-np.inf,total_capital_budget_m-minimum_liquidity_m))
  active=np.array([1 if o['action'] in DEVELOPMENT and o['start_year']-1<=y<o['start_year']-1+o['duration_years'] else 0 for o in options]);constraints.append(LinearConstraint(active,-np.inf,max_concurrent_projects))
 total_base=sum(max((o['base_noi_m'] for o in options if o['asset_id']==aid),default=0) for aid in asset_ids)
 for y in range(horizon_years):constraints.append(LinearConstraint(np.array([o['lost_noi_m'][y] for o in options]),-np.inf,total_base*(1-minimum_noi_ratio)))
 developments=np.array([1 if o['action'] in DEVELOPMENT else 0 for o in options]);constraints.append(LinearConstraint(developments,-np.inf,max(1,int(len(asset_ids)*max_development_share))))
 result=milp(c,integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=constraints,options={'time_limit':60,'mip_rel_gap':.005})
 if not result.success:return {'feasible':False,'status':result.message,'selections':[],'horizon_years':horizon_years}
 selected=[o for x,o in zip(result.x,options) if x>.5];annual=[{'year':y+1,'capex_m':round(sum(o['capex_schedule_m'][y] for o in selected),2),'capital_released_m':round(sum(o['receipt_schedule_m'][y] for o in selected),2),'noi_disruption_m':round(sum(o['lost_noi_m'][y] for o in selected),2),'active_projects':sum(1 for o in selected if o['action'] in DEVELOPMENT and o['start_year']-1<=y<o['start_year']-1+o['duration_years'])} for y in range(horizon_years)]
 return {'feasible':True,'status':result.message,'method':'Multi-period stochastic-risk MILP','horizon_years':horizon_years,'portfolio_expected_npv_m':round(sum(o['expected_npv_m'] for o in selected),2),'risk_adjusted_objective_m':round(sum(o['expected_npv_m']-cvar_penalty*max(0,o['cvar_95_m']) for o in selected),2),'selections':selected,'annual_plan':annual,'constraints':{'total_capital_budget_m':total_capital_budget_m,'annual_capital_budgets':annual_capital_budgets,'minimum_liquidity_m':minimum_liquidity_m,'max_concurrent_projects':max_concurrent_projects,'max_development_share':max_development_share,'minimum_noi_ratio':minimum_noi_ratio,'cvar_penalty':cvar_penalty}}
