import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.governance.gates import load_manifest,require_production_model
from packages.orchestration.engine import run_portfolio
p=argparse.ArgumentParser();p.add_argument('--allow-synthetic-model',action='store_true');p.add_argument('--output',default='data/processed/full_portfolio_v2.json');a=p.parse_args();manifest=load_manifest(ROOT/'models/registry/portfolio-forecasting-latest.json');require_production_model(manifest,a.allow_synthetic_model);base=json.loads((ROOT/'data/processed/portfolio.json').read_text());enriched=ROOT/'data/observed/portfolio_enriched.json'
if enriched.exists():
 candidate=json.loads(enriched.read_text());base=candidate if any(x.get('observed_inputs') for x in candidate) else base
results=run_portfolio(base);payload={'governance':{'model_manifest':manifest,'synthetic_model_allowed':a.allow_synthetic_model,'observed_assets':sum(x.get('model_status')=='observed_run' for x in results),'proxy_assets':sum(x.get('model_status')=='provisional_proxy_run' for x in results)},'assets':results};target=ROOT/a.output;target.write_text(json.dumps(payload,indent=2),encoding='utf-8');print(json.dumps({'assets':len(results),**payload['governance']},indent=2))
