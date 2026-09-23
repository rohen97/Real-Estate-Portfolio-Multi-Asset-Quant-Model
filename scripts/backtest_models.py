import sys,json
from pathlib import Path
import numpy as np,joblib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.forecasting.ensemble import predict
pilot=ROOT/'data/pilot';model_dir=ROOT/'models/synthetic-pilot/0.1.0';financials=json.loads((pilot/'financials.json').read_text());outcomes={x['asset_id']:x for x in json.loads((pilot/'outcomes.json').read_text())};v2=json.loads((ROOT/'data/processed/pilot_model_v2.json').read_text());legacy={x['asset_id']:x for x in json.loads((ROOT/'data/processed/legacy_comparison.json').read_text())};by_asset={}
for r in financials:by_asset.setdefault(r['Asset ID'],[]).append(r)
errors=[];covered=0;predictions=[]
for aid,rows in by_asset.items():
 rows=sorted(rows,key=lambda x:int(x['Fiscal Year']));prev,target=rows[-2],rows[-1];features={'prior_noi':float(prev['NOI SGD m']),'occupancy':float(prev['Occupancy %']),'cap_rate':float(prev['Cap Rate %']),'maintenance_capex':float(prev['Maintenance Capex SGD m']),'prior_valuation':float(prev['Valuation SGD m']),'year_index':int(target['Fiscal Year'])-2020};p=predict(model_dir/'noi_ensemble.joblib',features);actual=float(target['NOI SGD m']);errors.append(abs(p['point']-actual));covered+=int(p['p10']<=actual<=p['p90']);predictions.append({'asset_id':aid,'actual_noi_m':actual,**p})
new_actions={x['asset_id']:x['recommendation']['action'] for x in v2['assets']};legacy_labels={aid:x['corrected_quadrant'] for aid,x in legacy.items()};action_to_label={'Hold':'Retain','Retrofit':'Retrofit','Repurpose':'Repurpose','Redevelop':'Repurpose','Sell':'Release'};new_hits=[];legacy_hits=[];matched_npvs=[]
for aid,outcome in outcomes.items():
 actual=outcome['action'];new=new_actions.get(aid);legacy_action=legacy_labels.get(aid);new_hits.append(int(new==actual));legacy_hits.append(int(legacy_action==action_to_label.get(actual,actual)))
 if new==actual:matched_npvs.append(outcome['realised_npv_m'])
report={'status':'synthetic_pilot_backtest','warning':'Software validation only. Replace with verified historical decisions and outcomes.','noi_forecast':{'mae_m':round(float(np.mean(errors)),4),'p10_p90_coverage':round(covered/len(errors),4),'observations':len(errors)},'decision_policy':{'economic_action_hit_rate':round(float(np.mean(new_hits)),4),'legacy_management_label_hit_rate':round(float(np.mean(legacy_hits)),4),'matched_decision_realised_npv_m':round(float(sum(matched_npvs)),3),'observations':len(new_hits)},'predictions':predictions};target=ROOT/'data/processed/backtest_report.json';target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
