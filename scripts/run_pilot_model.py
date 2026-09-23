import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.domain.twin import build_twins
from packages.orchestration.v2 import run_twin
from packages.optimisation.multiperiod import optimise_multi_period
portfolio=json.loads((ROOT/'data/processed/portfolio.json').read_text());pilot=ROOT/'data/pilot';twins=build_twins(portfolio,pilot);legacy={x['asset_id']:x for x in json.loads((pilot/'legacy_inputs.json').read_text())};model_dir=ROOT/'models/synthetic-pilot/0.1.0';results=[]
for i,twin in enumerate([x for x in twins if x['financials']]):results.append(run_twin(twin,model_dir,legacy.get(twin['asset']['asset_id']),20260923+i))
asset_actions=[{'asset_id':x['asset_id'],'name':x['asset_name'],'base_noi_m':x['lease_cashflow']['noi_m'][0] if x['lease_cashflow'] else 0,'actions':x['actions']} for x in results];optimised=optimise_multi_period(asset_actions,horizon_years=5,total_capital_budget_m=300,annual_capital_budgets=[70,70,65,55,40],minimum_liquidity_m=30,max_concurrent_projects=4,max_development_share=.5,minimum_noi_ratio=.65,cvar_penalty=.3);output={'status':'synthetic_pilot_only','warning':'Asset identities come from the company workbook; financial, lease, planning, capex and outcome histories are synthetic until verified company data is imported.','assets':results,'optimisation':optimised};target=ROOT/'data/processed/pilot_model_v2.json';target.write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps({'assets':len(results),'optimiser_feasible':optimised.get('feasible'),'portfolio_expected_npv_m':optimised.get('portfolio_expected_npv_m'),'annual_plan':optimised.get('annual_plan')},indent=2))
