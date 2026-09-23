import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.zoning.change_model import train_change_model
p=argparse.ArgumentParser();p.add_argument('--dataset',default='data/observed/zoning_change_training.json');p.add_argument('--allow-synthetic-demo',action='store_true');p.add_argument('--version',default='0.1.0');a=p.parse_args();path=ROOT/a.dataset;synthetic=False
if not path.exists():
 if not a.allow_synthetic_demo:raise SystemExit('No historical zoning-change dataset. Use --allow-synthetic-demo for software validation.')
 path=ROOT/'data/examples/demo_zoning_change_training.json';synthetic=True
rows=json.loads(path.read_text());print(json.dumps(train_change_model(rows,ROOT/'models/zoning-change'/a.version,synthetic),indent=2))
