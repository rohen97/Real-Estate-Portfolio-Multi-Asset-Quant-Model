import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from packages.orchestration.engine import run_portfolio
base=ROOT/'data/processed/portfolio.json'
enriched=ROOT/'data/observed/portfolio_enriched.json'
assets=json.loads(base.read_text())
if enriched.exists():
 candidate=json.loads(enriched.read_text())
 if any(x.get('observed_inputs') for x in candidate):
  assets=candidate
results=run_portfolio(assets)
target=ROOT/'data/processed/full_model_results.json'
target.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({'assets':len(results),'proxy_modelled':sum(x.get('model_status')=='provisional_proxy_run' for x in results),'observed_modelled':sum(x.get('model_status')=='observed_run' for x in results),'outside_scope':sum(x.get('model_status')=='outside_singapore_scope' for x in results)},indent=2))
