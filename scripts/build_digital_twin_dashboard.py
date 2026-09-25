import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.synthetic.dashboard import build_dashboard
from packages.synthetic.semisynthetic import generate_portfolio_twins

portfolio_path = ROOT / "data/processed/portfolio.json"
if not portfolio_path.exists():
    portfolio_path = ROOT / "data/examples/demo_portfolio.json"
portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
twins = generate_portfolio_twins(portfolio)

synthetic_path = ROOT / "data/synthetic/semisynthetic_twins.json"
synthetic_path.parent.mkdir(parents=True, exist_ok=True)
synthetic_path.write_text(json.dumps(twins, indent=2), encoding="utf-8", newline="\n")

dashboard = build_dashboard(twins)
dashboard["portfolio_source"] = str(portfolio_path.relative_to(ROOT)).replace("\\", "/")
dashboard["source_status"] = "fictional_public_fixture" if all(asset.get("synthetic") for asset in portfolio) else "supplied_context_with_synthetic_underwriting"
dashboard["decision_ready"] = False
dashboard_path = ROOT / "data/processed/digital_twin_dashboard.json"
dashboard_path.parent.mkdir(parents=True, exist_ok=True)
dashboard_path.write_text(json.dumps(dashboard, indent=2, allow_nan=False), encoding="utf-8", newline="\n")

print(
    json.dumps(
        {
            "status": dashboard["status"],
            "portfolio_source": str(portfolio_path.relative_to(ROOT)),
            "twins": len(twins),
            "environments": len(dashboard["environments"]),
            "fragile_assets": dashboard["portfolio_summary"]["fragile_assets"],
            "twin_output": str(synthetic_path),
            "dashboard_output": str(dashboard_path),
        },
        indent=2,
    )
)
