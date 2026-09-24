import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.forecasting.spatial_market import train_spatial_market
p=argparse.ArgumentParser();p.add_argument('--dataset',default='data/observed/spatial_market_training.json');p.add_argument('--allow-synthetic-demo',action='store_true');p.add_argument('--version',default='0.1.0');a=p.parse_args();path=ROOT/a.dataset;synthetic=False
if not path.exists():
 if not a.allow_synthetic_demo:raise SystemExit('No verified spatial market history. Use --allow-synthetic-demo for software validation.')
 path=ROOT/'data/examples/demo_spatial_market_training.json';synthetic=True
result=train_spatial_market(json.loads(path.read_text()),ROOT/'models/spatial-market'/a.version/'rent_growth.joblib');result['synthetic_training']=synthetic;print(json.dumps(result,indent=2))
