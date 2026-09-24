import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.scenarios.covariance import calibrate_covariance
from packages.scenarios.regimes import fit_regimes

parser = argparse.ArgumentParser()
parser.add_argument("--dataset", default="data/observed/market_history.json")
parser.add_argument("--allow-synthetic-demo", action="store_true")
parser.add_argument("--version", default="0.1.0")
args = parser.parse_args()

path = ROOT / args.dataset
synthetic = False
if not path.exists():
    if not args.allow_synthetic_demo:
        raise SystemExit("No verified market history. Use --allow-synthetic-demo for software validation.")
    path = ROOT / "data/examples/demo_market_history.json"
    synthetic = True

rows = json.loads(path.read_text(encoding="utf-8"))
columns = ["rent_growth", "vacancy", "cap_rate", "interest_rate", "cost_inflation", "approval_delay"]
covariance = calibrate_covariance(rows, columns)
artifact_path = ROOT / "models/market-regimes" / args.version / "regimes.joblib"
regimes = fit_regimes(rows, columns, artifact_path, 3)
if regimes.get("artifact"):
    regimes["artifact"] = artifact_path.relative_to(ROOT).as_posix()

output = {
    "version": args.version,
    "generated_on": date.today().isoformat(),
    "synthetic_training": synthetic,
    "source_dataset": path.relative_to(ROOT).as_posix(),
    "covariance": covariance,
    "regimes": regimes,
}
target = ROOT / "data/calibration/market_scenarios.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(output, indent=2), encoding="utf-8")
print(json.dumps(output, indent=2))
