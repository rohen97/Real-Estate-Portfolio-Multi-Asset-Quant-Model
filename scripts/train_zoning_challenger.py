import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.zoning.challenger import train
p=argparse.ArgumentParser();p.add_argument('--dataset',default='data/observed/zoning_training.json');p.add_argument('--allow-synthetic-demo',action='store_true');p.add_argument('--version',default='0.1.0');a=p.parse_args();path=ROOT/a.dataset;synthetic=False
if not path.exists():
 if not a.allow_synthetic_demo:raise SystemExit('No verified zoning training dataset. Use --allow-synthetic-demo for software validation.')
 path=ROOT/'data/examples/demo_zoning_training.json';synthetic=True
rows=json.loads(path.read_text());print(json.dumps(train(rows,ROOT/'models/zoning-challenger'/a.version,synthetic),indent=2))
