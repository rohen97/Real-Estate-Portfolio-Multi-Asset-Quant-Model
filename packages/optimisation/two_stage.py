from __future__ import annotations
import math
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
DEVELOPMENT={'Retrofit','Repurpose','Redevelop'}
RESOURCE_UNITS={'Hold':0,'Retrofit':1,'Repurpose':2,'Redevelop':3,'Sell':0}
def default_scenarios():return [{'name':'Base','probability':.5,'npv_multiplier':1,'capex_multiplier':1,'delay_years':0},{'name':'Downside','probability':.25,'npv_multiplier':.55,'capex_multiplier':1.18,'delay_years':1},{'name':'Upside','probability':.25,'npv_multiplier':1.35,'capex_multiplier':.95,'delay_years':0}]
def optimise_two_stage(asset_actions:list[dict],scenarios=None,horizon_years=5,total_capital_budget_m=500,annual_capital_budgets=None,minimum_liquidity_m=50,max_concurrent_projects=8,contractor_capacity=None,minimum_noi_ratio=.7,cvar_alpha=.95,cvar_penalty=.25,max_leverage=.65,dependencies=None,concentration_limits=None):
 scenarios=scenarios or default_scenarios();annual_capital_budgets=annual_capital_budgets or [total_capital_budget_m/horizon_years]*horizon_years;contractor_capacity=contractor_capacity or [12]*horizon_years;dependencies=dependencies or [];concentration_limits=concentration_limits or {};options=[]
 for asset in asset_actions:
  for action in asset['actions']:
   duration=max(1,int(math.ceil(action.get('execution_years',1))));starts=[0] if action['action'] in ('Hold','Sell') else range(max(1,horizon_years-duration+1))
   for start in starts:
    capex=[0.]*horizon_years;receipts=[0.]*horizon_years;noi_loss=[0.]*horizon_years;resource=[0.]*horizon_years
    if action['action']=='Sell':receipts[min(horizon_years-1,start+int(action.get('sale_delay_years',0)))]=max(0,-float(action.get('capex_m',0)));noi_loss[start:]=[asset.get('base_noi_m',0)]*(horizon_years-start)
    else:
     annual=max(0,float(action.get('capex_m',0)))/duration
     for y in range(start,min(horizon_years,start+duration)):capex[y]=annual;resource[y]=RESOURCE_UNITS.get(action['action'],1);noi_loss[y]=asset.get('base_noi_m',0)*{'Hold':0,'Retrofit':.12,'Repurpose':.35,'Redevelop':.8}.get(action['action'],0)
    options.append({'asset_id':asset['asset_id'],'asset_name':asset['name'],'segment':asset.get('segment','Unknown'),'planning_area':asset.get('planning_area','Unknown'),'action':action['action'],'start_year':start+1,'duration_years':duration,'base_npv_m':float(action.get('expected_npv_m',0)),'capex':capex,'receipts':receipts,'noi_loss':noi_loss,'resource':resource,'commitment_m':sum(capex)*.1,'cancel_cost_m':sum(capex)*.08})
 n=len(options);s_count=len(scenarios);x_start=0;e_start=n;eta_index=n+n*s_count;z_start=eta_index+1;total_vars=z_start+s_count;c=np.zeros(total_vars);integrality=np.zeros(total_vars);integrality[:eta_index]=1;lower=np.zeros(total_vars);upper=np.ones(total_vars);lower[eta_index]=-np.inf;upper[eta_index]=np.inf;upper[z_start:]=np.inf
 for j,o in enumerate(options):c[j]+=sum(sc['probability']*o['cancel_cost_m'] for sc in scenarios)
 for s,scenario in enumerate(scenarios):
  for j,o in enumerate(options):c[e_start+s*n+j]+=-scenario['probability']*(o['base_npv_m']*scenario['npv_multiplier']+o['cancel_cost_m'])
 c[eta_index]=cvar_penalty;c[z_start:]=[cvar_penalty*sc['probability']/(1-cvar_alpha) for sc in scenarios];constraints=[];asset_ids=sorted({o['asset_id'] for o in options})
 for aid in asset_ids:constraints.append(LinearConstraint(np.array([1 if i<n and options[i]['asset_id']==aid else 0 for i in range(total_vars)]),1,1))
 for s,scenario in enumerate(scenarios):
  for j,o in enumerate(options):
   row=np.zeros(total_vars);row[e_start+s*n+j]=1;row[j]=-1;constraints.append(LinearConstraint(row,-np.inf,0))
   if o['action'] in ('Hold','Sell'):constraints.append(LinearConstraint(row,0,0))
  for y in range(horizon_years):
   cap=np.zeros(total_vars);resource=np.zeros(total_vars);noi=np.zeros(total_vars)
   for j,o in enumerate(options):cap[e_start+s*n+j]=(o['capex'][y]*scenario['capex_multiplier']-o['receipts'][y]);resource[e_start+s*n+j]=o['resource'][y];noi[e_start+s*n+j]=o['noi_loss'][y]
   constraints.append(LinearConstraint(cap,-np.inf,annual_capital_budgets[y]));constraints.append(LinearConstraint(resource,-np.inf,contractor_capacity[y]));total_noi=sum(a.get('base_noi_m',0) for a in asset_actions);constraints.append(LinearConstraint(noi,-np.inf,total_noi*(1-minimum_noi_ratio)))
  cumulative=np.zeros(total_vars)
  for y in range(horizon_years):
   for j,o in enumerate(options):cumulative[e_start+s*n+j]+=o['capex'][y]*scenario['capex_multiplier']-o['receipts'][y]
  constraints.append(LinearConstraint(cumulative,-np.inf,total_capital_budget_m-minimum_liquidity_m))
  loss=np.zeros(total_vars)
  for j,o in enumerate(options):loss[e_start+s*n+j]=-o['base_npv_m']*scenario['npv_multiplier'];loss[j]+=o['cancel_cost_m'];loss[e_start+s*n+j]-=o['cancel_cost_m']
  loss[eta_index]-=1;loss[z_start+s]-=1;constraints.append(LinearConstraint(loss,-np.inf,0))
 total_value=sum(float(a.get('current_value_m',0)) for a in asset_actions);debt=np.zeros(total_vars)
 for j,o in enumerate(options):debt[j]=sum(o['capex'])*.6
 constraints.append(LinearConstraint(debt,-np.inf,total_value*max_leverage if total_value else total_capital_budget_m*max_leverage))
 for field,limits in concentration_limits.items():
  for value,limit in limits.items():constraints.append(LinearConstraint(np.array([1 if i<n and options[i].get(field)==value and options[i]['action'] in DEVELOPMENT else 0 for i in range(total_vars)]),-np.inf,limit))
 option_lookup={(o['asset_id'],o['action']):i for i,o in enumerate(options) if o['start_year']==1}
 for dependency in dependencies:
  child=option_lookup.get((dependency['asset_id'],dependency['action']));parent=option_lookup.get((dependency['requires_asset_id'],dependency['requires_action']))
  if child is not None and parent is not None:
   row=np.zeros(total_vars);row[child]=1;row[parent]=-1;constraints.append(LinearConstraint(row,-np.inf,0))
 result=milp(c,integrality=integrality,bounds=Bounds(lower,upper),constraints=constraints,options={'time_limit':90,'mip_rel_gap':.01})
 if not result.success:return {'feasible':False,'status':result.message,'selections':[]}
 selected=[o for j,o in enumerate(options) if result.x[j]>.5];recourse=[]
 for s,scenario in enumerate(scenarios):recourse.append({'scenario':scenario['name'],'probability':scenario['probability'],'executed':[{'asset_id':o['asset_id'],'action':o['action'],'start_year':o['start_year']} for j,o in enumerate(options) if result.x[e_start+s*n+j]>.5],'cancelled':[{'asset_id':o['asset_id'],'action':o['action']} for j,o in enumerate(options) if result.x[j]>.5 and result.x[e_start+s*n+j]<.5]})
 return {'feasible':True,'status':result.message,'method':'Two-stage stochastic MILP with scenario recourse and CVaR','first_stage':selected,'recourse':recourse,'cvar_eta':float(result.x[eta_index]),'objective':float(-result.fun),'constraints':{'horizon_years':horizon_years,'annual_capital_budgets':annual_capital_budgets,'contractor_capacity':contractor_capacity,'minimum_noi_ratio':minimum_noi_ratio,'cvar_alpha':cvar_alpha,'max_leverage':max_leverage}}
