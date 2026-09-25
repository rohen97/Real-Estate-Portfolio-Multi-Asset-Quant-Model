# Simulation and diagnostic integrity revision

Version: `semi-synthetic-twin-0.4.0` / `digital-twin-dashboard-0.4.0`.

## Evidence boundary

The ten public assets, addresses, zoning labels, valuations, leases and financial histories are fictional. Public market indices are separately sourced official aggregate context; they do not verify an asset's income, title, capex, value or achievable investment return. This revision improves internal logic and reproducibility, not demonstrated real-world alpha.

Context has an explicit source/status: `synthetic_fixture`, `supplied_unverified` or an explicitly supplied `verified_source`. Fictional fields cannot become real portfolio anchors merely because they are populated. Context completeness uses the actual number of eligible context fields as its denominator. The legacy `real_context_pct` key remains a compatibility alias for completeness; `verified_context_pct` is the distinct verification measure. Financial underwriting remains synthetic and 0% verified.

Office maps to Commercial; Logistics, Warehouse, Business park and Industrial map to Industrial; Hospitality maps to Hotel; Mixed use has a separate Mixed Use profile. Unknown labels map to Other. Profile numbers remain visible generator assumptions rather than calibrated sector benchmarks.

## Digital-twin prediction and evaluation

Prediction uses generated observable underwriting and explicit scenario assumptions. It does not read `latent_simulation_truth`. Small, bounded screening adjustments use operating/sustainability scores, occupancy or building age. The maximum absolute valuation-based adjustments are 1.5% for Retrofit and 2% for Repurpose/Redevelop; they apply only to successful implementation. They are unvalidated assumptions, not learned effects or investment alpha. Residual capacity is displayed as unpriced optionality and is not added again to capitalised NOI uplift.

Hold defines the common incremental baseline: incremental expected NPV, quantiles, loss probability, capital and simulated outcome are all exactly zero. Baseline retained-asset PV remains available separately; zero incremental Hold does not imply zero asset value or zero absolute market risk.

The action valuation engine now supplies explicit success and failure incremental NPVs, net of correctly timed cashflows. Each predictive draw samples the approval branch using the displayed probability. The failed-execution branch retains Hold income and loses the model's assumed sunk capex. Failure-state uncertainty is restricted to sunk costs; it does not create development rent/terminal-value exposure after approval has failed. Added tail shocks represent residual market and execution model risk.

There are 2,048 predictive draws per action. All assets/actions share economic and construction factors and retain independent asset/action shocks. Factors use variance-standardised Student-t(6) draws. Economic loading is 0.65; development cost loading is -0.35; remaining variance is idiosyncratic. Predictive means, quantiles, loss probability and loss CVaR are computed from the same sample. Scenario assumptions and tail distributions are not empirically calibrated. Student-t outcomes are unbounded incremental-NPV stresses, not legal liability bounds.

Evaluation uses a disjoint random seed, a separate approval draw and hidden simulation effects. Changing hidden truth cannot change predicted means, intervals or recommendations. A single held-out synthetic outcome per action/environment supports only a software simulation comparison. Oracle agreement, regret and interval coverage are not historical accuracy. Coverage explicitly reports its denominator (50 asset/action outcomes for ten assets); agreement reports ten recommendations. Reusing common scenario indexes across environments reduces random comparison noise; environments are still conditional cases without probability weights.

## Environment and funding consistency

Rent changes and segment demand first adjust the current NOI level used by both action and Hold cashflows. Annual growth is `clip(2.5% + 0.1 × total rent-level change, -3%, 8%)`; this deliberately separates a level stress from persistent annual growth. Terminal cap rate is clipped to 2–15%. Construction multipliers adjust committed capex as well as NPV. Approval multipliers change branch probabilities once. Sale-price multiplier is `clip((1 + rent-level change) × current cap / stressed cap, 0.35, 1.75)`, so sale proceeds and available portfolio cash fall under the same stressed assumptions.

No additional external financing or approval penalty is added after the branch valuation. Funding uses full committed construction costs as a conservative budget measure, even where failure-state expected cash expenditure is smaller. One cannot fund a successful project using probability-weighted expected capex alone.

The portfolio optimiser receives 128 evenly spaced, aligned predictive draws for joint tail-risk optimisation. Individual risk cards retain all 2,048 observations. The smaller optimisation risk sample can differ from card-level CVaR. Marginal-versus-joint CVaR comparisons in the optimiser use the same 128 draws. Both standalone recommendations and constrained selections are retained. Model and hindsight selections use the same funding constraints; evaluation totals are discounted using each selected start year. NOI-retention constraints use the environment-adjusted baseline NOI. Hindsight regret is explicitly a synthetic comparison. Constraint violations come from the optimiser's numerical post-solve audit rather than a hardcoded zero.

## Core scenario engine

The separate core model stores all 5,000 predictive observations as `scenario_samples_m`; charts return those exact observations instead of a fresh 600-draw distribution. `scenario_npvs_m` holds an aligned 128-observation optimisation subset. Stable SHA-256 asset/action seeds make action reordering and process restarts reproducible. Portfolio assets use a common factor seed and separate idiosyncratic seeds.

Fixed currency shock coefficients are replaced by exposures proportional to asset value, capex, NOI and execution duration. Selling reverses exposure to the retained income stream: stronger future rent growth reduces sale-versus-Hold incremental value. Development adds capex-linked cost sensitivity and NOI-linked delay exposure. A direct financing-rate penalty is excluded from unlevered NPV; the interest factor remains available for market/financing diagnostics but has no direct coefficient here. Approval outcomes sample the valuation engine's success/failure branches. These are still heuristic local sensitivity models, not a calibrated structural price process.

The correlated Gaussian/heavy-tail mixture is variance-normalised before factor bounds. The displayed correlation matrix is measured from 5,000 bounded model draws; `input_correlation` separately retains the source matrix. Calibrated factors, if supplied, do not validate action sensitivity coefficients. Displayed VaR and CVaR use positive-part loss `max(0,-NPV)` with exact finite 5% tail weights; they do not offset rare losses with profits inside the tail. Signed loss-tail statistics remain separately available. Hold's incremental distribution remains exactly zero.

## Demonstration diagnostics

NOI example MAE, RMSE, bias and coverage are recomputed from the precise displayed rows. The examples are formula-generated fictional values, not an out-of-time model backtest. Economic-action and legacy-label hit rates are null with status `not_evaluated` because independent outcome/label observations do not exist. The demo registry explicitly states that no model was trained.

Zoning display fixtures include legal-label fields needed for label-agreement charts, but also `legal_status=fictional_not_statutory`, `status=unverified_fixture` and an abstention. Display confidence values are illustrative, uncalibrated scores; there is no trained classifier or estimated future zoning-change probability. Identical fixture labels do not establish classifier performance or statutory agreement.

## Verification

Focused tests cover sector aliases, provenance bounds, hidden-truth independence, shared-versus-held-out draw separation, reproducibility, empirical metric reconciliation, zero Hold, stressed capex/sale receipts, schedule-discounted comparison and zoning fixture status. Core scenario tests cover exact chart/card agreement, linear economic-size scaling, action-order invariance, common asset factor exposure and factor bounds. Existing calibrated covariance and regime-artifact tests also pass.

Before underwriting use, obtain independently verified asset cashflows and development costs, point-in-time outcome histories, planning evidence and a genuine held-out evaluation. None of the simulation gains substitutes for those missing inputs.
