"""Build reproducible fictional fixtures, never represented as trained-model evidence."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.orchestration.engine import run_portfolio
from packages.legacy.comparison import compare
from packages.optimisation.engine import optimise_portfolio


def forecast_diagnostics(predictions: list[dict]) -> dict:
    """Reconcile summary metrics to exactly the displayed synthetic row sample."""
    count = len(predictions)
    errors = [row["point"] - row["actual_noi_m"] for row in predictions]
    covered = sum(row["p10"] <= row["actual_noi_m"] <= row["p90"] for row in predictions)
    return {
        "status": "synthetic_formula_reconciliation_not_backtest",
        "mae_m": sum(abs(error) for error in errors) / count if count else None,
        "rmse_m": math.sqrt(sum(error**2 for error in errors) / count) if count else None,
        "bias_m": sum(errors) / count if count else None,
        "p10_p90_coverage": covered / count if count else None,
        "observations": count, "covered_observations": covered, "nominal_interval_coverage": 0.8,
        "source": "row-level fictional formula examples; no learned model or historical holdout",
    }


def _without_scenario_arrays(value):
    if isinstance(value, dict):
        return {key: _without_scenario_arrays(item) for key, item in value.items()
                if key not in {"scenario_samples_m", "scenario_npvs_m"}}
    if isinstance(value, list):
        return [_without_scenario_arrays(item) for item in value]
    return value


def build_demo_assets() -> list[dict]:
    types = ["Mixed use", "Office", "Retail", "Logistics", "Residential", "Hospitality", "Office", "Retail", "Residential", "Industrial"]
    zones = [("COMMERCIAL & RESIDENTIAL", 4.2), ("COMMERCIAL", 5.6), ("COMMERCIAL", 3.5), ("BUSINESS 2", 2.5), ("RESIDENTIAL", 2.8), ("HOTEL", 3.5), ("COMMERCIAL", 4.2), ("COMMERCIAL", 3.0), ("RESIDENTIAL", 2.1), ("BUSINESS 1", 2.5)]
    assets = []
    for index, (kind, (land_use, gpr)) in enumerate(zip(types, zones), 1):
        assets.append({
            "asset_id": f"DEMO-{index:03d}", "name": f"Demo {kind} Asset {index}",
            "country": "Singapore", "jurisdiction": "Singapore URA (fictional fixture)",
            "segments": [kind], "address": f"Illustrative Singapore Location {index}",
            "source_records": 1, "source_rows": [{"sheet": "Public Demo", "row": index + 1}],
            "latitude": 1.25 + index * .018, "longitude": 103.70 + index * .025,
            "synthetic": True, "synthetic_financials": True,
            "context_source": "fictional public demonstration portfolio", "context_verified": False,
            "tenure_hint": {"type": "Freehold" if index % 3 == 0 else "99-year leasehold", "remaining_years": None if index % 3 == 0 else 68 - index, "source": "synthetic demo"},
            "ura_zoning": {
                "matches": [{"objectid": 900000 + index, "lu_desc": land_use, "gpr": gpr,
                             "gpr_text": str(gpr), "planning_area": "DEMO PLANNING AREA",
                             "subzone": f"DEMO SUBZONE {index}", "source_vintage": "Fictional zoning fixture; not a statutory match",
                             "legal_status": "fictional_not_statutory"}],
                "match_method": "demo_fixture", "spatial_review_required": True,
                "current_statutory_plan": "Fictional MP2025-style fixture; unverified",
                "legal_status": "fictional_not_statutory",
            },
            "catalogue_details": ["Fictional public demonstration asset"],
        })
    return assets


def _core_zone(land_use: str) -> str:
    if "RESIDENTIAL" in land_use and "COMMERCIAL" in land_use:
        return "Mixed Use"
    return "Residential" if "RESIDENTIAL" in land_use else "Commercial" if "COMMERCIAL" in land_use else "Industrial" if "BUSINESS" in land_use else "Hotel" if land_use == "HOTEL" else "Other"


def zoning_fixtures(assets: list[dict]) -> tuple[list[dict], dict]:
    rows = []
    core_entropy = round(-sum(probability * math.log(probability) for probability in (.86, .09, .05)) / math.log(3), 5)
    for asset in assets:
        zone = asset["ura_zoning"]["matches"][0]
        core = _core_zone(zone["lu_desc"])
        rows.append({
            "asset_id": asset["asset_id"], "name": asset["name"],
            "latitude": asset["latitude"], "longitude": asset["longitude"],
            "status": "synthetic_fixture_not_model", "legal_status": "fictional_not_statutory",
            "confidence_status": "illustrative_uncalibrated", "decision_ready": False,
            "legal_land_use": zone["lu_desc"], "legal_gpr": zone["gpr"],
            "planning_area": zone["planning_area"], "subzone": zone["subzone"],
            "prediction": {
                "core": {"prediction": core, "confidence": .86, "entropy": core_entropy,
                         "top3": [{"label": core, "probability": .86}, {"label": "Illustrative alternative", "probability": .09}, {"label": "Other", "probability": .05}], "abstain": True},
                "subtype": {"prediction": zone["lu_desc"], "confidence": .8, "entropy": .35, "top3": [], "abstain": True},
                "gpr_band": {"prediction": "Demo band", "confidence": .72, "entropy": .42, "top3": [], "abstain": True},
                "synthetic_training": False, "trained": False, "status": "hand_authored_display_fixture",
            },
            "discrepancy": {
                "legal_land_use": zone["lu_desc"], "legal_core": core, "legal_gpr": zone["gpr"],
                "predicted_core": core, "predicted_subtype": zone["lu_desc"], "predicted_gpr_band": "Demo band",
                "observed_lulc": "unknown", "severity": 0, "status": "unverified_fixture",
                "reasons": ["Labels and confidence are fictional display fixtures; agreement is not independent validation or legal evidence."],
                "prediction_confidence": .86, "prediction_entropy": core_entropy,
            },
            "future_change": {"change_probability": .18, "signal": "Illustrative only", "synthetic_training": False,
                              "status": "not_estimated", "calibrated": False},
        })
    geojson = {
        "type": "FeatureCollection", "status": "synthetic_fixture_not_model",
        "source": "fictional public demonstration portfolio", "legal_status": "fictional_not_statutory",
        "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]},
                      "properties": {"asset_id": row["asset_id"], "name": row["name"], "severity": 0,
                                     "status": "unverified_fixture", "legal_land_use": row["legal_land_use"],
                                     "legal_core": row["discrepancy"]["legal_core"], "legal_gpr": row["legal_gpr"],
                                     "legal_status": "fictional_not_statutory",
                                     "predicted_core": row["discrepancy"]["predicted_core"],
                                     "confidence": .86, "entropy": core_entropy, "change_probability": .18,
                                     "confidence_status": "illustrative_uncalibrated", "abstain": True}}
                     for row in rows],
    }
    return rows, geojson


def main() -> None:
    assets = build_demo_assets()
    results = run_portfolio(assets)
    legacy = [{"asset_id": asset["asset_id"], "asset_name": asset["name"], "financial": 55 + index * 3,
               "operational": 60 + index * 2, "market": 65 + index, "sustainability": 50 + index * 2,
               "published_current": None, "published_future": None, "source": "synthetic public demo", "synthetic_extension": True}
              for index, asset in enumerate(assets)]
    comparison = compare(legacy, results, [])
    actions = [{"asset_id": row["asset_id"], "name": row["name"], "base_noi_m": row["economics"]["current_noi_m"], "actions": row["actions"]} for row in results]
    optimisation = optimise_portfolio(actions, 300, 8, .5, .3, 30)
    predictions = [{"asset_id": row["asset_id"], "actual_noi_m": round(row["economics"]["current_noi_m"] * 1.02, 3),
                    "point": round(row["economics"]["current_noi_m"] * 1.018, 3), "p10": round(row["economics"]["current_noi_m"] * .98, 3),
                    "p50": round(row["economics"]["current_noi_m"] * 1.018, 3), "p90": round(row["economics"]["current_noi_m"] * 1.06, 3),
                    "status": "synthetic_formula_example"} for row in results]
    backtest = {"status": "public_synthetic_demo", "validation_status": "not_a_historical_backtest",
                "warning": "Row reconciliation for fictional formula examples; no learned model or out-of-sample investment evidence.",
                "noi_forecast": forecast_diagnostics(predictions),
                "decision_policy": {"status": "not_evaluated", "economic_action_hit_rate": None,
                                    "legacy_management_label_hit_rate": None, "observations": 0,
                                    "reason": "Independent action outcomes and management labels are unavailable"},
                "predictions": predictions}
    registry = {"name": "portfolio-formula-demo", "version": "0.2.0-demo", "status": "illustrative_formula_not_trained",
                "synthetic_training": False, "trained": False, "data_source": "fictional public demo",
                "metrics": {"noi": backtest["noi_forecast"]}, "artifacts": []}
    zoning, geojson = zoning_fixtures(assets)
    reference_path = ROOT / "data/reference/singapore_market_snapshot.json"
    market = json.loads(reference_path.read_text(encoding="utf-8")) if reference_path.exists() else {
        "status": "unavailable", "as_of": None, "market_indicators": {},
        "warning": "Official market reference is unavailable; no fictional market statistics substituted.",
    }
    files = {"demo_portfolio.json": assets, "demo_full_model_results.json": results, "demo_legacy_comparison.json": comparison,
             "demo_market_snapshot.json": market, "demo_pilot_model_v2.json": {"status": "public_synthetic_demo", "warning": "Fictional assets and synthetic financials", "assets": results, "optimisation": optimisation},
             "demo_backtest_report.json": backtest, "demo_model_registry.json": registry,
             "demo_zoning_predictions.json": zoning, "demo_zoning_discrepancy_map.geojson": geojson,
             "demo_full_portfolio_v2.json": {"governance": {"synthetic_model_allowed": True, "observed_assets": 0, "proxy_assets": len(assets), "decision_ready": False}, "assets": results}}
    output = ROOT / "data/examples"
    output.mkdir(parents=True, exist_ok=True)
    for filename, payload in files.items():
        if filename in {"demo_pilot_model_v2.json", "demo_full_portfolio_v2.json"}:
            payload = _without_scenario_arrays(payload)
        (output / filename).write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(json.dumps({"demo_assets": len(assets), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
