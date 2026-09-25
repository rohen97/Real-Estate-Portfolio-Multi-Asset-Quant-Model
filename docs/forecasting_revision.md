# Forecasting and backtest revision — 25 September 2026

The NOI forecasting code now tests a future fiscal year against a no-change NOI forecast and keeps interval calibration separate from that final test. This improves measurement discipline; it does not establish investment alpha or validate the fictional public portfolio against real outcomes.

## Data construction

`packages/forecasting/ensemble.py::samples` preserves its four-result API. Every accepted sample contains prior-year NOI, occupancy, cap rate, maintenance capex and valuation plus the target-year index; its label is next-year NOI for the same asset. Asset IDs and fiscal years must be valid, all numeric features and labels must be finite, and the two fiscal years must be consecutive. All rows for a duplicated asset/year are excluded rather than choosing an arbitrary survivor. Missing covariates are not silently replaced with zero. A feature row and target are appended together only after both have been validated, fixing the earlier possibility of misaligned feature and label arrays. The returned empty feature array retains its six-column shape. Training emits rejection counts in `sample_diagnostics`.

## Fitting, calibration and evaluation

The latest target fiscal year is reserved for final testing; the penultimate year is calibration only; earlier years train the standardised Ridge, gradient-boosted point model and quantile models. The scaler and all models are fitted only on the training slice. At least 20 training rows, five calibration rows and five holdout rows are required. The fitted model is not subsequently refitted on the held-out outcomes, so the saved artifact retains an auditable cutoff.

The point forecast remains the equal-weight Ridge/gradient-boosting mean. A sorted quantile interval is expanded using the finite-sample residual order statistic computed on the calibration year only. The legacy `p10` and `p90` response names remain, but metadata explains they are nominal 80% calibrated interval bounds; they are not guaranteed conditional quantiles. Temporal dependence, small samples and regime change mean that the independent-observation conformal coverage guarantee cannot be claimed for this panel.

The held-out report includes MAE and RMSE, the MAE of the no-change prior-NOI forecast, absolute improvement and relative MAE skill, empirical interval coverage, interval width and the 80% interval score. Negative skill means the ensemble underperformed the simple baseline on that held-out sample. Forecast skill is not an investment return and is not market alpha.

Training, calibration and test cutoffs are stored with the artifact. Prediction includes the target fiscal year, `out_of_time`, provenance and `independent_market_alpha_verified=false`. Legacy artifacts remain loadable for prediction, but a historical backtest will not certify their timing without the new cutoff metadata. Synthetic source markers override a missing caller flag, preventing synthetic training data from being accidentally labelled observed.

Fiscal-year ordering alone cannot establish that the prior annual accounts had been publicly released at the proposed trading date. Actual disclosure timestamps and revision vintages are absent; `publication_lag_verified=false` records that limitation. This is a future fiscal-year forecast split, not a fully point-in-time investable backtest.

## Backtest and policy interpretation

`scripts/backtest_models.py` is now import-safe, with a `main()` entry point and optional CLI paths for financials, model directory, outcomes, decisions, legacy comparison and output. It evaluates only the saved held-out year, uses the same validated sample builder and recomputes the headline metrics from its prediction rows. Missing required history/artifact produces a clear failure instead of fabricated validation data. Missing optional decision/outcome files do not prevent a valid NOI forecast evaluation.

An action recorded in an outcomes file is not necessarily the optimal action. Only summing realised NPVs where the model happened to match that action conditions on a selected subset and leaves alternative outcomes unobserved. Therefore the old `economic_action_hit_rate`, `legacy_management_label_hit_rate` and `matched_decision_realised_npv_m` fields are retained as null rather than interpreted as investment performance. New descriptive agreement fields are explicitly label agreement only. Causal policy performance remains unidentified until timestamped decisions, the complete eligible opportunity set and an appropriate counterfactual evaluation design are available.

## Verification

`tests/unit/test_forecasting_invariants.py`: **12 passed**. Tests cover adjacent-year requirements, duplicate rejection, atomic handling of invalid targets, minimum temporal depth, disjoint fitting/calibration/test years, scaler training-row count, synthetic provenance, no-change baseline reconciliation, invalid prediction inputs, out-of-time flags, exact report-to-prediction metric reconciliation and blocking a legacy artifact without cutoffs. An explicit leakage test adds SGD100m to every final-year target and verifies that fitted point predictions and calibrated interval bounds remain unchanged while reported holdout error rises.

The final combined check passed **51 tests** across forecasting invariants, valuation invariants, existing detailed components and v2 model tests. The valuation file includes a regression ensuring that an infeasible redevelopment envelope does not reuse existing floor area to manufacture a redevelopment valuation. Final repository-wide suite results are recorded separately because other model modules are being revised concurrently.

## References

- scikit-learn, [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html): chronological evaluation avoids fitting future samples to evaluate earlier observations.
- Romano, Patterson and Candès, [Conformalized Quantile Regression, NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/5103c3584b063c431bd1268e9b5e76fb-Abstract.html): separate model fitting and residual calibration. This implementation documents why time dependence prevents simply importing an independent-data coverage guarantee.
