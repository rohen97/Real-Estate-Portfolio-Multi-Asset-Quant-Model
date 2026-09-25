"""NOI forecasting with chronological evaluation and explicit provenance."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import math
import joblib
import numpy as np
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

FEATURES = ['prior_noi', 'occupancy', 'cap_rate', 'maintenance_capex', 'prior_valuation', 'year_index']
SOURCE_FIELDS = ['NOI SGD m', 'Occupancy %', 'Cap Rate %', 'Maintenance Capex SGD m', 'Valuation SGD m']


def contains_synthetic_history(financials):
    return any(str(row.get('Synthetic', '')).strip().lower() in ('true', 'yes', '1')
               or 'synthetic' in str(row.get('Source', '')).lower() for row in financials)


def _prepare_samples(financials):
    diagnostics = Counter(input_rows=len(financials))
    by_key = {}
    for row in financials:
        try:
            aid = str(row['Asset ID']).strip()
            year_value = float(row['Fiscal Year'])
            if not aid or row['Asset ID'] is None or not math.isfinite(year_value) or not year_value.is_integer():
                raise ValueError('invalid asset/year')
            key = (aid, int(year_value))
        except (KeyError, ValueError, TypeError, OverflowError):
            diagnostics['invalid_identifier_rows'] += 1
            continue
        by_key.setdefault(key, []).append(row)
    by_asset = {}
    for (aid, year), rows in by_key.items():
        if len(rows) != 1:
            # Reject ambiguous asset-years, including exact repeats: do not create
            # an arbitrary survivor or multiple labels for the same observation.
            diagnostics['duplicate_asset_year_rows'] += len(rows)
            continue
        by_asset.setdefault(aid, {})[year] = rows[0]
    x, y, years, asset_ids = [], [], [], []
    for aid, annual in sorted(by_asset.items()):
        for target_year in sorted(annual):
            if target_year - 1 not in annual:
                diagnostics['rows_without_adjacent_prior_year'] += 1
                continue
            prev, cur = annual[target_year - 1], annual[target_year]
            try:
                features = [float(prev[k]) for k in SOURCE_FIELDS] + [target_year - 2020]
                target = float(cur['NOI SGD m'])
                if not all(math.isfinite(v) for v in features + [target]):
                    raise ValueError('non-finite feature or target')
            except (KeyError, ValueError, TypeError, OverflowError):
                diagnostics['invalid_numeric_pairs'] += 1
                continue
            # Append atomically only after the whole row and target are valid.
            x.append(features)
            y.append(target)
            years.append(target_year)
            asset_ids.append(aid)
    diagnostics['accepted_pairs'] = len(y)
    return (np.asarray(x, float).reshape(-1, len(FEATURES)), np.asarray(y, float),
            np.asarray(years, int), asset_ids, dict(diagnostics))


def samples(financials: list[dict]):
    """Return aligned prior-year features, next-year NOI, years and asset IDs."""
    return _prepare_samples(financials)[:4]


def _raw_predictions(model, x):
    point = (model['ridge'].predict(x) + model['gbm'].predict(x)) / 2
    quantiles = np.sort(np.column_stack([model['quantiles'][q].predict(x) for q in (.1, .5, .9)]), axis=1)
    return point, quantiles


def train_ensemble(financials: list[dict], output_dir: Path, synthetic=False):
    synthetic = bool(synthetic) or contains_synthetic_history(financials)
    x, y, years, asset_ids, diagnostics = _prepare_samples(financials)
    unique_years = np.unique(years)
    if len(y) < 30 or len(unique_years) < 3:
        return {'status': 'blocked', 'observations': len(y), 'sample_diagnostics': diagnostics,
                'reason': 'At least 30 valid adjacent-year observations across three target years are required'}
    holdout_year, calibration_year = int(unique_years[-1]), int(unique_years[-2])
    holdout, calibration = years == holdout_year, years == calibration_year
    train = years < calibration_year
    if train.sum() < 20 or calibration.sum() < 5 or holdout.sum() < 5:
        return {'status': 'blocked', 'observations': len(y), 'sample_diagnostics': diagnostics,
                'reason': 'Chronological split requires at least 20 training, 5 calibration and 5 holdout rows',
                'train_rows': int(train.sum()), 'calibration_rows': int(calibration.sum()), 'test_rows': int(holdout.sum())}
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=1)).fit(x[train], y[train])
    parameters = dict(n_estimators=180, learning_rate=.035, max_depth=3, num_leaves=15,
                      min_child_samples=8, reg_lambda=2, verbosity=-1, random_state=20260923,
                      n_jobs=1)
    gbm = LGBMRegressor(**parameters).fit(x[train], y[train])
    quantiles = {q: LGBMRegressor(objective='quantile', alpha=q, **parameters).fit(x[train], y[train])
                 for q in (.1, .5, .9)}
    model = {'ridge': ridge, 'gbm': gbm, 'quantiles': quantiles, 'features': FEATURES}
    _, calibration_quantiles = _raw_predictions(model, x[calibration])
    scores = np.maximum(calibration_quantiles[:, 0] - y[calibration], y[calibration] - calibration_quantiles[:, 2])
    rank = min(len(scores), math.ceil((len(scores) + 1) * .8))
    adjustment = max(0., float(np.sort(scores)[rank - 1]))
    pred, raw_quantiles = _raw_predictions(model, x[holdout])
    lower, upper = raw_quantiles[:, 0] - adjustment, raw_quantiles[:, 2] + adjustment
    baseline = x[holdout, 0]  # No-change forecast is known at the prediction origin.
    mae = float(mean_absolute_error(y[holdout], pred))
    baseline_mae = float(mean_absolute_error(y[holdout], baseline))
    nominal_alpha = .2
    interval_score = upper - lower + (2 / nominal_alpha) * (
        np.maximum(lower - y[holdout], 0) + np.maximum(y[holdout] - upper, 0))
    metrics = {
        'mae': mae, 'rmse': float(mean_squared_error(y[holdout], pred) ** .5),
        'holdout_year': holdout_year, 'calibration_year': calibration_year,
        'training_cutoff_year': int(years[train].max()),
        'train_rows': int(train.sum()), 'calibration_rows': int(calibration.sum()), 'test_rows': int(holdout.sum()),
        'naive_no_change_mae': baseline_mae,
        'mae_improvement_vs_naive': baseline_mae - mae,
        'mae_skill_vs_naive': 1 - mae / baseline_mae if baseline_mae > 0 else None,
        'p10_p90_coverage': float(np.mean((lower <= y[holdout]) & (y[holdout] <= upper))),
        'mean_interval_width': float(np.mean(upper - lower)),
        'mean_interval_score_80': float(np.mean(interval_score)),
        'nominal_interval_coverage': .8,
    }
    provenance = {
        'evaluation': 'latest fiscal year held out; prior fiscal year calibration; earlier years training',
        'training_cutoff_year': metrics['training_cutoff_year'], 'calibration_year': calibration_year,
        'holdout_year': holdout_year, 'feature_timing': 'prior fiscal year financials only',
        'publication_lag_verified': False,
        'publication_lag_warning': 'Fiscal-year ordering is enforced; actual report-release dates must be supplied to verify investable information timing',
        'synthetic_training': bool(synthetic), 'sample_diagnostics': diagnostics,
        'independent_market_alpha_verified': False,
        'interval_method': 'chronological split quantile-residual calibration; no finite-sample coverage guarantee under time dependence or regime change',
        'performance_scope': 'synthetic software validation' if synthetic else 'single future fiscal-year forecast test; no causal investment-return claim',
    }
    model.update(metrics=metrics, synthetic_training=bool(synthetic), provenance=provenance,
                 interval_adjustment_m=adjustment, schema_version=2)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / 'noi_ensemble.joblib'
    joblib.dump(model, artifact)
    return {'status': 'trained', 'metrics': metrics, 'features': FEATURES, 'synthetic_training': bool(synthetic),
            'artifact': str(artifact), 'provenance': provenance, 'sample_diagnostics': diagnostics,
            'interval_adjustment_m': adjustment}


def predict(model_path: Path, features: dict):
    model = joblib.load(model_path)
    x = np.array([[float(features[k]) for k in model['features']]])
    if not np.all(np.isfinite(x)):
        raise ValueError('prediction features must be finite')
    point, raw_quantiles = _raw_predictions(model, x)
    adjustment = float(model.get('interval_adjustment_m', 0.))
    lower, median, upper = raw_quantiles[0]
    provenance = model.get('provenance', {'evaluation': 'legacy artifact without verified chronological calibration metadata'})
    target_year = int(features['year_index']) + 2020
    cutoff = provenance.get('calibration_year', model['metrics'].get('training_cutoff_year'))
    out_of_time = cutoff is not None and target_year > cutoff
    return {'point': float(point[0]), 'p10': float(lower - adjustment), 'p50': float(median),
            'p90': float(upper + adjustment), 'model_metrics': model['metrics'],
            'synthetic_training': model['synthetic_training'], 'provenance': provenance,
            'target_fiscal_year': target_year, 'out_of_time': out_of_time,
            'interval_adjustment_m': adjustment,
            'interval_semantics': 'p10/p90 fields are calibrated nominal 80% interval bounds, not guaranteed conditional quantiles',
            'independent_market_alpha_verified': False}
