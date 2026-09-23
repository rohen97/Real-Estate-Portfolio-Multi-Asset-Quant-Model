# Validation report

Validation date: 23 September 2026.

## Ten-step delivery status

1. Legacy scorecard frozen with exact 35/25/25/15 weights and corrected formulas.
2. Versioned domain contracts and SQLite evidence ledger implemented.
3. Ten company-register assets linked to a clearly labelled synthetic six-year pilot history.
4. Lease-level ten-year cash-flow modelling implemented.
5. Hold, Retrofit, Repurpose, Redevelop, Sell and real-option valuations implemented.
6. LightGBM/Ridge ensemble, quantile models, empirical-Bayes pooling and approval-survival model trained on the synthetic pilot; company calibration remains blocked pending history.
7. Five-year MILP implemented with annual budgets, cumulative liquidity, concurrent projects, development exposure and NOI preservation.
8. Published, corrected and economic recommendations compared for the same ten assets.
9. Temporal NOI and policy backtests implemented.
10. Governed expansion executed across all 260 registered assets, with synthetic-model use requiring an explicit flag.

## Data and zoning

- 260 deduplicated portfolio assets from the company workbook.
- 177 Singapore assets; all geocoded and matched to live URA SPACE MP2025.
- 113,418 MP2025 polygons in the local index.
- 15 controlled zoning exceptions requiring title-lot or use-permission verification.
- Title-boundary GeoJSON overlap resolver implemented.

## ML pilot metrics

- Training source: synthetic pilot linked to ten real portfolio asset IDs.
- NOI ensemble training rows: 40; chronological holdout rows: 10.
- Latest synthetic holdout MAE: approximately S$0.254m.
- P10-P90 backtest coverage: 70% across ten synthetic observations.
- Approval survival model observations: 60 stage outcomes.
- Hierarchical growth observations: 50 transitions.
- All model artifacts have SHA-256 hashes in the registry.

These statistics validate software execution only and are not claims about investment performance.

## Selection logic validation

- All 177 catalogue-only Singapore assets return Data Required / Monitor, preventing unsupported transaction instructions.
- A separate underlying portfolio signal and acquisition signal are calculated but suppressed until verified underwriting replaces proxies.
- Action-specific adjustments include zoning/en-bloc value, transformation value, view risk, supply pressure and lease decay.
- Surrounding development context uses MP2025 polygons within 500 metres.
- Synthetic-pilot selection results are labelled software validation only.

## Visualization layer

Interactive charts cover portfolio allocation, MP2025 location/GPR, capacity waterfalls, zoning sensitivity, surrounding development, DCF cash flows, action risks, covariance/correlation, selection bridges, optimisation timelines, legacy quadrants, model diagnostics, evidence provenance and audit gates. Plotly is lazy-loaded to preserve initial application performance.

## Zoning challenger validation

- Synthetic training observations: 1,200 across nine detailed land-use classes.
- Stratified planning-area cross-validation mean macro F1: approximately 0.864.
- Mean balanced accuracy: approximately 0.936.
- Real portfolio inference: 177 assets, 19 model abstentions and 57 discrepancy reviews.
- Probability calibration uses held-out planning areas and temperature scaling.
- Future-change synthetic model performance is weak and remains software validation only.

## Automated validation

- Backend unit and integration tests: 35 passed.
- Frontend tests: 1 passed.
- TypeScript type checking: passed.
- Production frontend build: passed.
- End-to-end pipeline script: passed.
- Underwriting workbook formula-error scan: zero matches.
- Workbook visual QA completed across 13 sheets.

## Production blockers

- Zero assets currently have complete verified underwriting inputs.
- Company financial, lease, planning, capex and realised decision history must replace the synthetic pilot.
- The 15 zoning exceptions require title-lot or written-permission evidence.
- Professional valuation and investment governance remain mandatory.
