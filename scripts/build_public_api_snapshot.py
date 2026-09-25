"""Capture an allowlisted, fictional-only API snapshot for all public dashboard tabs."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GLOBAL_ROUTES = [
    "/health", "/model/revision", "/data/status", "/underwriting/status", "/calibration/status",
    "/visualisations/scenario-matrix", "/visualisations/model-diagnostics", "/models/market-scenarios",
    "/digital-twins/dashboard", "/models/registry", "/models/backtest", "/pilot/v2", "/portfolio/v2",
    "/legacy/spec", "/legacy/comparison", "/market/public", "/zoning/discrepancy-map",
    "/zoning/exceptions", "/zoning/source-status",
]
OPTIMISATION_ROUTES = {
    "/snapshots/optimise": ("/optimise", {"capital_budget_m": 500, "max_projects": 20, "max_development_share": .45, "cvar_penalty": .3, "minimum_liquidity_m": 50}),
    "/snapshots/two-stage": ("/optimise/two-stage", {"capital_budget_m": 500, "minimum_liquidity_m": 50, "max_concurrent_projects": 8, "minimum_noi_ratio": .7, "cvar_penalty": .25}),
    "/snapshots/stability": ("/optimise/stability", {"capital_budget_m": 500, "max_projects": 20, "max_development_share": .45, "cvar_penalty": .3, "minimum_liquidity_m": 50}),
}


def compact_payload(value):
    """Keep full chart observations only in the scenario-samples route."""
    omitted = {"scenario_samples_m", "scenario_npvs_m", "latent_simulation_truth"}
    if isinstance(value, dict):
        return {key: compact_payload(item) for key, item in value.items() if key not in omitted}
    if isinstance(value, list):
        return [compact_payload(item) for item in value]
    return value


def assert_public_assets(value):
    if isinstance(value, dict):
        if isinstance(value.get("asset_id"), (str, int, float)) and not str(value["asset_id"]).startswith("DEMO-"):
            raise RuntimeError("Public snapshot encountered a non-demo asset identifier")
        for item in value.values():
            assert_public_assets(item)
    elif isinstance(value, list):
        for item in value:
            assert_public_assets(item)


def main():
    private_sources = ["data/processed/portfolio.json", "data/processed/ura_mp2025.sqlite",
                       "data/calibration/market_scenarios.json", "data/calibration/calibration_report.json",
                       "data/observed/underwriting_validation_report.json", "models/registry/portfolio-forecasting-latest.json"]
    if any((ROOT / source).exists() for source in private_sources):
        raise RuntimeError("Build public snapshots in a clean demo checkout without private portfolio, calibration, registry or spatial-index inputs")
    fixtures = json.loads((ROOT / "data/examples/demo_portfolio.json").read_text(encoding="utf-8"))
    if len(fixtures) != 10 or not all(asset.get("synthetic") and asset["asset_id"].startswith("DEMO-") for asset in fixtures):
        raise RuntimeError("Public snapshot requires exactly ten explicitly fictional DEMO assets")
    os.environ["PUBLIC_DEMO_MODE"] = "1"
    from fastapi.testclient import TestClient
    from apps.api import main as api
    if not api.DEMO_MODE:
        raise RuntimeError("API was imported before public demo mode was enabled")

    routes = {}
    with TestClient(api.app) as client:
        def capture(path):
            response = client.get(path)
            response.raise_for_status()
            payload = response.json()
            assert_public_assets(payload)
            routes[path] = compact_payload(payload)
            return payload

        portfolio = capture("/portfolio")
        if {asset["asset_id"] for asset in portfolio["assets"]} != {asset["asset_id"] for asset in fixtures}:
            raise RuntimeError("API portfolio does not match the explicitly fictional fixture set")
        for route in GLOBAL_ROUTES:
            capture(route)
        print(f"Captured {len(routes)} portfolio and diagnostic routes", flush=True)
        for asset in fixtures:
            asset_id = asset["asset_id"]
            for route in (f"/assets/{asset_id}", f"/assets/{asset_id}/scenario-samples", f"/assets/{asset_id}/advanced-analysis",
                          f"/digital-twins/assets/{asset_id}", f"/zoning/prediction/{asset_id}", f"/selection/{asset_id}"):
                capture(route)
            for radius in (250, 500, 750, 1000, 2000):
                capture(f"/zoning/map/{asset_id}?radius_m={radius}")
            routes[f"/zoning/map/{asset_id}"] = routes[f"/zoning/map/{asset_id}?radius_m=750"]
            print(f"Captured {asset_id} analysis and map views", flush=True)
        for target, (source, request) in OPTIMISATION_ROUTES.items():
            response = client.post(source, json=request)
            response.raise_for_status()
            payload = response.json()
            assert_public_assets(payload)
            routes[target] = {**compact_payload(payload), "snapshot_status": "saved_calculation",
                              "snapshot_request": request, "snapshot_source_route": source,
                              "snapshot_warning": "Previously calculated fictional portfolio; this static site cannot rerun the model."}
            print(f"Captured saved calculation {target}", flush=True)

    snapshot = {"metadata": {"status": "public_synthetic_snapshot", "schema_version": "1.0",
                              "generated_at": datetime.now(timezone.utc).isoformat(), "assets": len(fixtures),
                              "routes": len(routes), "decision_ready": False,
                              "warning": "Fictional assets and model results; official aggregate market context is separately attributed. Saved calculations are not live API executions.",
                              "model_revision": routes.get("/model/revision")}, "routes": routes}
    target = ROOT / "public/data/api_snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(json.dumps({"output": str(target), "routes": len(routes), "bytes": target.stat().st_size}, indent=2))


if __name__ == "__main__":
    main()
