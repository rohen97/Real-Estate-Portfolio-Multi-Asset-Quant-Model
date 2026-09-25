from copy import deepcopy
import json
import joblib
import numpy as np
import pytest

from packages.forecasting.ensemble import FEATURES, samples, train_ensemble, predict
from scripts.backtest_models import build_backtest_report


def row(aid='A', year=2020, noi=5., **kwargs):
    return {'Asset ID': aid, 'Fiscal Year': year, 'NOI SGD m': noi,
            'Occupancy %': .9, 'Cap Rate %': .05, 'Maintenance Capex SGD m': .4,
            'Valuation SGD m': 100., **kwargs}


def history():
    return [row(f'A{aid}', year, noi=(3 + aid / 3) * 1.025 ** (year - 2018), Synthetic=True)
            for aid in range(8) for year in range(2018, 2027)]


def test_samples_skip_nonconsecutive_years_and_keep_aligned_arrays():
    data = [row(year=2020), row(year=2022), row(year=2023), row(year=2024, noi='broken')]
    x, y, years, ids = samples(data)
    assert x.shape == (1, len(FEATURES))
    assert len(x) == len(y) == len(years) == len(ids)
    assert years.tolist() == [2023]


def test_duplicate_asset_years_do_not_create_ambiguous_training_labels():
    x, y, years, ids = samples([row(year=2020), row(year=2021), row(year=2021, noi=99), row(year=2022)])
    assert x.shape == (0, len(FEATURES))
    assert not len(y) and not len(years) and not ids


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), None, ''])
def test_nonfinite_or_missing_targets_are_rejected_atomically(bad):
    x, y, years, ids = samples([row(year=2020), row(year=2021, noi=bad)])
    assert x.shape == (0, len(FEATURES))
    assert len(x) == len(y) == len(years) == len(ids) == 0


def test_insufficient_temporal_depth_is_blocked_even_with_many_rows(tmp_path):
    data = [row(str(i), year) for i in range(40) for year in (2025, 2026)]
    result = train_ensemble(data, tmp_path / 'blocked')
    assert result['status'] == 'blocked'
    assert not (tmp_path / 'blocked/noi_ensemble.joblib').exists()


@pytest.fixture(scope='module')
def trained(tmp_path_factory):
    destination = tmp_path_factory.mktemp('forecast_model')
    result = train_ensemble(history(), destination)
    return result, destination / 'noi_ensemble.joblib'


def test_training_calibration_and_test_are_disjoint_chronological_years(trained):
    result, model_path = trained
    assert result['status'] == 'trained'
    metrics = result['metrics']
    assert metrics['training_cutoff_year'] < metrics['calibration_year'] < metrics['holdout_year']
    assert (metrics['train_rows'], metrics['calibration_rows'], metrics['test_rows']) == (48, 8, 8)
    assert result['synthetic_training'] is True  # Source markers override a missing caller flag.
    model = joblib.load(model_path)
    assert model['ridge'].named_steps['standardscaler'].n_samples_seen_ == 48
    assert metrics['mae_improvement_vs_naive'] == pytest.approx(metrics['naive_no_change_mae'] - metrics['mae'])
    assert metrics['mean_interval_score_80'] >= 0
    assert result['provenance']['independent_market_alpha_verified'] is False


def test_modifying_final_holdout_cannot_change_fit_or_interval_calibration(trained, tmp_path):
    _, model_path = trained
    changed = deepcopy(history())
    for item in changed:
        if item['Fiscal Year'] == 2026:
            item['NOI SGD m'] += 100
    trained_changed = train_ensemble(changed, tmp_path / 'changed')
    x, _, years, _ = samples(history())
    features = dict(zip(FEATURES, x[np.flatnonzero(years == 2026)[0]]))
    before = predict(model_path, features)
    after = predict(tmp_path / 'changed/noi_ensemble.joblib', features)
    for key in ('point', 'p10', 'p50', 'p90', 'interval_adjustment_m'):
        assert before[key] == pytest.approx(after[key], abs=1e-12)
    assert trained_changed['metrics']['mae'] > before['model_metrics']['mae'] + 90


def test_predictions_identify_cutoff_and_reject_nan(trained):
    _, model_path = trained
    features = dict(zip(FEATURES, [5, .9, .05, .4, 100, 6]))
    result = predict(model_path, features)
    assert result['target_fiscal_year'] == 2026 and result['out_of_time']
    assert result['p10'] <= result['p50'] <= result['p90']
    assert predict(model_path, {**features, 'year_index': 5})['out_of_time'] is False
    with pytest.raises(ValueError):
        predict(model_path, {**features, 'prior_noi': float('nan')})


def test_backtest_metrics_reconcile_rows_and_do_not_infer_policy_alpha(trained):
    _, model_path = trained
    report = build_backtest_report(history(), model_path,
        outcomes=[{'asset_id': 'A0', 'action': 'Hold', 'realised_npv_m': 999}],
        decisions=[{'asset_id': 'A0', 'recommendation': {'action': 'Hold'}}])
    predictions = report['predictions']
    mae = np.mean([abs(r['point'] - r['actual_noi_m']) for r in predictions])
    coverage = np.mean([r['p10'] <= r['actual_noi_m'] <= r['p90'] for r in predictions])
    assert report['noi_forecast']['mae_m'] == pytest.approx(mae, abs=1e-6)
    assert report['noi_forecast']['p10_p90_coverage'] == pytest.approx(coverage, abs=1e-6)
    assert report['decision_policy']['descriptive_action_agreement'] == 1
    assert report['decision_policy']['economic_action_hit_rate'] is None
    assert report['decision_policy']['matched_decision_realised_npv_m'] is None
    assert report['independent_market_alpha_verified'] is False
    json.dumps(report, allow_nan=False)


def test_backtest_blocks_legacy_artifact_without_cutoff(trained, tmp_path):
    _, model_path = trained
    model = joblib.load(model_path)
    model.pop('provenance')
    legacy_path = tmp_path / 'legacy.joblib'
    joblib.dump(model, legacy_path)
    report = build_backtest_report(history(), legacy_path)
    assert report['status'] == 'blocked'
