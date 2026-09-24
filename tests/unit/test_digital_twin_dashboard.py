from packages.synthetic.semisynthetic import generate_twin, generate_portfolio_twins
from packages.synthetic.dashboard import build_dashboard, evaluate_twin


def sample_asset(asset_id="A1"):
    return {
        "asset_id": asset_id,
        "name": "Sample Asset",
        "address": "1 Sample Road",
        "country": "Singapore",
        "segments": ["Mall"],
        "latitude": 1.3,
        "longitude": 103.8,
        "size_from_sqft": 250000,
        "asking_rent_monthly_sgd": None,
        "ura_zoning": {
            "matches": [
                {
                    "planning_area": "ORCHARD",
                    "subzone": "ORCHARD",
                    "lu_desc": "COMMERCIAL",
                    "gpr": 4.2,
                    "height_max": 120,
                }
            ]
        },
        "zoning_exception": None,
    }


def test_semisynthetic_twin_preserves_real_context_and_labels_underwriting():
    twin = generate_twin(sample_asset())
    assert twin["real_context"]["address"] == "1 Sample Road"
    assert twin["real_context"]["planning_area"] == "ORCHARD"
    assert twin["completeness"]["verified_underwriting_pct"] == 0
    assert twin["field_provenance"]["valuation_m"]["status"] == "synthetic"
    assert len(twin["histories"]["financials"]) == 12
    assert twin["histories"]["leases"]


def test_semisynthetic_generation_is_deterministic():
    first = generate_twin(sample_asset())
    second = generate_twin(sample_asset())
    assert first["underwriting"] == second["underwriting"]
    assert first["latent_simulation_truth"] == second["latent_simulation_truth"]


def test_new_model_evaluates_three_environments():
    twin = generate_twin(sample_asset())
    results = [evaluate_twin(twin, environment) for environment in ("base", "stress", "structural_change")]
    assert all(result["recommended_action"] in {"Hold", "Retrofit", "Repurpose", "Redevelop", "Sell"} for result in results)
    assert all(len(result["actions"]) == 5 for result in results)
    assert all(result["recommendation_p10_m"] <= result["recommendation_p90_m"] for result in results)


def test_dashboard_contains_new_model_portfolio_outputs():
    twins = generate_portfolio_twins([sample_asset("A1"), sample_asset("A2"), sample_asset("A3")])
    dashboard = build_dashboard(twins)
    assert dashboard["portfolio_summary"]["assets"] == 3
    assert len(dashboard["environments"]) == 3
    assert all(environment["portfolio"]["feasible"] for environment in dashboard["environments"])
    assert dashboard["assets"][0]["environments"]["base"]["actions"]
