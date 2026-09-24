import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.synthetic.dashboard import build_dashboard
from packages.synthetic.semisynthetic import generate_portfolio_twins

portfolio = json.loads((ROOT / "data/examples/demo_portfolio.json").read_text(encoding="utf-8"))
twins = generate_portfolio_twins(portfolio)
dashboard = build_dashboard(twins)
dashboard["status"] = "public_synthetic_demo"
dashboard["warning"] = "Public fictional assets and synthetic financials. Software demonstration only; no private Far East portfolio data are included."
target = ROOT / "public/data/digital_twin_dashboard.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(dashboard, indent=2), encoding="utf-8")
print(json.dumps({"assets": len(twins), "output": str(target), "status": dashboard["status"]}, indent=2))
