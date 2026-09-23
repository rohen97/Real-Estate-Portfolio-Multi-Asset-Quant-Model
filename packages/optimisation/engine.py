from __future__ import annotations
from packages.optimisation.multiperiod import optimise_multi_period
def optimise_portfolio(asset_actions:list[dict],capital_budget_m=500,max_projects=20,max_development_share=.45,cvar_penalty=.3,minimum_liquidity_m=50):
 result=optimise_multi_period(asset_actions,horizon_years=5,total_capital_budget_m=capital_budget_m,minimum_liquidity_m=minimum_liquidity_m,max_concurrent_projects=min(max_projects,10),max_development_share=max_development_share,cvar_penalty=cvar_penalty)
 if result.get('feasible'):
  result['capital_required_m']=round(sum(sum(x['capex_schedule_m']) for x in result['selections']),2);result['capital_released_m']=round(sum(sum(x['receipt_schedule_m']) for x in result['selections']),2)
 return result
