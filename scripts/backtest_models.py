"""Evaluate a saved chronological NOI holdout without claiming decision alpha."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.forecasting.ensemble import FEATURES, contains_synthetic_history, predict, samples


def build_backtest_report(financials, model_path, outcomes=None, decisions=None, legacy=None):
    model = joblib.load(model_path)
    provenance = model.get('provenance') or {}
    cutoff = provenance.get('calibration_year')
    target_year = provenance.get('holdout_year')
    if cutoff is None or target_year is None or target_year <= cutoff:
        return {'status': 'blocked', 'reason': 'Retrain with chronological training/calibration/holdout metadata before evaluating',
                'independent_market_alpha_verified': False}
    x, y, years, asset_ids = samples(financials)
    indexes = np.flatnonzero(years == target_year)
    if not len(indexes):
        return {'status': 'blocked', 'reason': 'No valid adjacent-year rows match the saved model holdout year',
                'holdout_year': target_year, 'independent_market_alpha_verified': False}
    predictions = []
    errors, baseline_errors, coverage, interval_scores = [], [], [], []
    for index in indexes:
        forecast = predict(model_path, dict(zip(FEATURES, x[index])))
        if not forecast['out_of_time']:
            raise ValueError('Refusing to score a target at or before model calibration cutoff')
        actual, baseline = float(y[index]), float(x[index, 0])
        errors.append(abs(forecast['point'] - actual))
        baseline_errors.append(abs(baseline - actual))
        coverage.append(forecast['p10'] <= actual <= forecast['p90'])
        interval_scores.append(forecast['p90'] - forecast['p10'] + 10 * (
            max(0., forecast['p10'] - actual) + max(0., actual - forecast['p90'])))
        predictions.append({'asset_id': asset_ids[index], 'target_year': int(years[index]),
                            'actual_noi_m': actual, 'naive_no_change_noi_m': baseline, **forecast})
    synthetic = bool(model.get('synthetic_training')) or contains_synthetic_history(financials)
    actions = {r['asset_id']: r.get('recommendation', {}).get('action') for r in (decisions or [])}
    labels = {r['asset_id']: r.get('corrected_quadrant') for r in (legacy or [])}
    label_map = {'Hold': 'Retain', 'Retrofit': 'Retrofit', 'Repurpose': 'Repurpose', 'Redevelop': 'Repurpose', 'Sell': 'Release'}
    agreements, legacy_agreements = [], []
    for outcome in outcomes or []:
        aid, actual_action = outcome.get('asset_id'), outcome.get('action')
        if actual_action is None:
            continue
        if actions.get(aid) is not None:
            agreements.append(actions[aid] == actual_action)
        if labels.get(aid) is not None:
            legacy_agreements.append(labels[aid] == label_map.get(actual_action, actual_action))
    mae, baseline_mae = float(np.mean(errors)), float(np.mean(baseline_errors))
    return {
        'status': 'synthetic_pilot_backtest' if synthetic else 'chronological_forecast_holdout',
        'warning': ('Synthetic software validation; no independent market alpha has been established.' if synthetic else
                    'Fiscal-year out-of-time forecast test; publication lags and causal investment returns remain unverified.'),
        'provenance': provenance, 'independent_market_alpha_verified': False,
        'noi_forecast': {
            'mae_m': round(mae, 6), 'naive_no_change_mae_m': round(baseline_mae, 6),
            'mae_improvement_vs_naive_m': round(baseline_mae - mae, 6),
            'mae_skill_vs_naive': round(1 - mae / baseline_mae, 6) if baseline_mae > 0 else None,
            'p10_p90_coverage': round(float(np.mean(coverage)), 6),
            'mean_interval_score_80_m': round(float(np.mean(interval_scores)), 6),
            'observations': len(predictions), 'holdout_year': int(target_year),
            'calibration_year': int(cutoff), 'nominal_interval_coverage': .8,
        },
        'decision_policy': {
            'status': 'causal_policy_performance_not_identified',
            'economic_action_hit_rate': None, 'legacy_management_label_hit_rate': None,
            'matched_decision_realised_npv_m': None, 'observations': len(agreements),
            'descriptive_action_agreement': float(np.mean(agreements)) if agreements else None,
            'descriptive_legacy_label_agreement': float(np.mean(legacy_agreements)) if legacy_agreements else None,
            'interpretation': 'Agreement with recorded actions is not evidence those actions were optimal. Selected matched outcomes exclude alternatives and cannot identify policy value or alpha. Timestamped decisions, complete eligible universe and counterfactual evaluation are required.',
        },
        'predictions': predictions,
    }


def _load_optional(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--financials', type=Path, default=ROOT / 'data/pilot/financials.json')
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'models/synthetic-pilot/0.1.0')
    parser.add_argument('--outcomes', type=Path, default=ROOT / 'data/pilot/outcomes.json')
    parser.add_argument('--decisions', type=Path, default=ROOT / 'data/processed/pilot_model_v2.json')
    parser.add_argument('--legacy', type=Path, default=ROOT / 'data/processed/legacy_comparison.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed/backtest_report.json')
    args = parser.parse_args()
    model_path = args.model_dir / 'noi_ensemble.joblib'
    if not args.financials.exists() or not model_path.exists():
        raise SystemExit('Financial history and trained NOI artifact are required; no fabricated backtest will be generated.')
    decisions = _load_optional(args.decisions)
    report = build_backtest_report(
        json.loads(args.financials.read_text(encoding='utf-8')), model_path,
        _load_optional(args.outcomes), decisions.get('assets', []) if isinstance(decisions, dict) else decisions,
        _load_optional(args.legacy))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
