import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.optimisation.stability import analyse_stability
from packages.optimisation.two_stage import optimise_two_stage
from packages.orchestration.advanced import analyse_asset


def load_json(primary: Path, fallback: Path):
    path = primary if primary.exists() else fallback
    return json.loads(path.read_text(encoding="utf-8"))


def load_modelled_assets():
    full_portfolio = ROOT / "data/processed/full_portfolio_v2.json"
    if full_portfolio.exists():
        payload = json.loads(full_portfolio.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("assets"), list):
            return payload["assets"], "data/processed/full_portfolio_v2.json"
    results = load_json(
        ROOT / "data/processed/full_model_results.json",
        ROOT / "data/examples/demo_full_model_results.json",
    )
    return results, "data/processed/full_model_results.json" if (ROOT / "data/processed/full_model_results.json").exists() else "data/examples/demo_full_model_results.json"


portfolio = load_json(ROOT / "data/processed/portfolio.json", ROOT / "data/examples/demo_portfolio.json")
results, results_source = load_modelled_assets()
singapore = [asset for asset in portfolio if asset.get("country") == "Singapore" and asset.get("latitude") is not None][:10]
advanced = []
for asset in singapore:
    try:
        advanced.append(analyse_asset(asset))
    except Exception as exc:
        advanced.append({"asset_id": asset["asset_id"], "error": str(exc)})

selected_ids = {asset["asset_id"] for asset in singapore}
modelled = [asset for asset in results if asset.get("asset_id") in selected_ids and asset.get("actions")]
actions = [
    {
        "asset_id": asset["asset_id"],
        "name": asset["name"],
        "segment": (asset.get("segments") or ["Unknown"])[0],
        "planning_area": (asset.get("ura_zoning", {}).get("matches") or [{}])[0].get("planning_area", "Unknown"),
        "base_noi_m": asset.get("economics", {}).get("current_noi_m", 0),
        "current_value_m": asset.get("economics", {}).get("current_value_m", 0),
        "actions": asset["actions"],
    }
    for asset in modelled
]
two_stage = optimise_two_stage(
    actions,
    total_capital_budget_m=300,
    annual_capital_budgets=[70, 70, 65, 55, 40],
    minimum_liquidity_m=30,
    max_concurrent_projects=4,
    contractor_capacity=[8, 8, 7, 6, 5],
    minimum_noi_ratio=0.65,
    cvar_penalty=0.25,
)
stability = analyse_stability(
    actions,
    runs=20,
    total_capital_budget_m=300,
    annual_capital_budgets=[70, 70, 65, 55, 40],
    minimum_liquidity_m=30,
    max_concurrent_projects=4,
    max_development_share=0.5,
    cvar_penalty=0.3,
)
payload = {
    "status": "screening_only",
    "warning": "Requires verified underwriting, LBC rates, title geometry and professional review",
    "modelled_results_source": results_source,
    "advanced_assets": advanced,
    "two_stage_optimisation": two_stage,
    "stability": stability,
}
target = ROOT / "data/processed/advanced_model_results.json"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(
    json.dumps(
        {
            "assets": len(advanced),
            "advanced_errors": sum("error" in asset for asset in advanced),
            "two_stage_feasible": two_stage.get("feasible"),
            "fragile_assets": stability.get("fragile_assets"),
            "modelled_results_source": results_source,
            "output": str(target),
        },
        indent=2,
    )
)
