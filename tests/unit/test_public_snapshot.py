import pytest

from scripts.build_public_api_snapshot import assert_public_assets, compact_payload


def test_snapshot_rejects_nested_non_demo_asset_records():
    with pytest.raises(RuntimeError, match="non-demo"):
        assert_public_assets({"assets": [{"asset_id": "PRIVATE-001"}]})
    assert_public_assets({"asset_id": "DEMO-001", "field_provenance": {"asset_id": {"status": "synthetic_fixture"}}})


def test_snapshot_omits_duplicate_simulation_and_hidden_truth_but_keeps_chart_observations():
    payload = {"assets": [{"asset_id": "DEMO-001", "scenario_samples_m": [1, 2], "scenario_npvs_m": [1],
                           "latent_simulation_truth": {"execution_quality": .9}}],
               "samples": {"Hold": [0., 0.], "Sell": [1., 2.]}}
    compact = compact_payload(payload)
    assert compact["assets"] == [{"asset_id": "DEMO-001"}]
    assert compact["samples"] == payload["samples"]
