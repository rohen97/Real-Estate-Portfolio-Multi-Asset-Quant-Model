import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.calibration.engine import run_calibration
p=argparse.ArgumentParser();p.add_argument('--data-dir',default='data/observed');p.add_argument('--output',default='data/calibration/calibration_report.json');a=p.parse_args();print(json.dumps(run_calibration(ROOT/a.data_dir,ROOT/a.output),indent=2))
