import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.forecasting.ensemble import train_ensemble
from packages.forecasting.survival import ApprovalSurvivalModel
from packages.forecasting.hierarchical import HierarchicalGrowthModel
from packages.governance.registry import register
p=argparse.ArgumentParser();p.add_argument('--allow-synthetic-pilot',action='store_true');p.add_argument('--version',default='0.1.0');a=p.parse_args();observed=ROOT/'data/observed';pilot=ROOT/'data/pilot';financial_path=observed/'financials.json';planning_path=observed/'planning_history.json';capex_path=observed/'capex.json';synthetic=False
financials=json.loads(financial_path.read_text()) if financial_path.exists() else []
if sum(1 for r in financials if r.get('NOI SGD m') not in (None,''))<30:
 if not a.allow_synthetic_pilot:raise SystemExit('Insufficient verified history. Re-run with --allow-synthetic-pilot for software validation only.')
 financials=json.loads((pilot/'financials.json').read_text());planning_path=pilot/'planning_history.json';capex_path=pilot/'capex.json';synthetic=True
model_dir=ROOT/'models'/('synthetic-pilot' if synthetic else 'company-calibrated')/a.version
noi=train_ensemble(financials,model_dir,synthetic)
planning=json.loads(planning_path.read_text()) if planning_path.exists() else [];survival=ApprovalSurvivalModel();approval=survival.fit(planning)
if approval.get('status')=='trained':survival_path=model_dir/'approval_survival.joblib';survival.save(survival_path)
else:survival_path=model_dir/'approval_survival.joblib'
by_asset={}
for row in financials:by_asset.setdefault(row['Asset ID'],[]).append(row)
growth=[]
for aid,rows in by_asset.items():
 rows=sorted(rows,key=lambda x:int(x['Fiscal Year']))
 for x,y in zip(rows,rows[1:]):
  if float(x['NOI SGD m']):growth.append({'segment':'Pilot portfolio','growth':float(y['NOI SGD m'])/float(x['NOI SGD m'])-1})
hier=HierarchicalGrowthModel().fit(growth).summary();(model_dir/'hierarchical_growth.json').parent.mkdir(parents=True,exist_ok=True);(model_dir/'hierarchical_growth.json').write_text(json.dumps(hier,indent=2),encoding='utf-8')
metrics={'noi':noi,'approval':approval,'hierarchical':hier};artifacts=[model_dir/'noi_ensemble.joblib',survival_path,model_dir/'hierarchical_growth.json'];manifest=register(ROOT/'models/registry','portfolio-forecasting',a.version,artifacts,metrics,str(financial_path if not synthetic else pilot),synthetic);print(json.dumps(manifest,indent=2))
