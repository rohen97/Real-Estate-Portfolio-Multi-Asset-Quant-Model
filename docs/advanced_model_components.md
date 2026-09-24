# Advanced model components

Implemented on 24 September 2026.

## Detailed Singapore cash flows

Monthly construction S-curves, lease-up, tenant relocation, demolition, financing drawdowns, Buyer and Seller Stamp Duty, transaction costs, developer margin, sale timing and Land Betterment Charge inputs.

## 3D development envelopes

Title-boundary geometry is converted into a local metric plane. Candidate tower layouts apply setbacks, site coverage, height, tower spacing, core/access efficiency, parking area and daylight depth. Outputs include footprints, 3D boxes, GFA, NLA, parking and binding constraints.

## En-bloc model

Residual land value includes GDV, construction, professional, finance, marketing, LBC, demolition, tenant costs, BSD and developer margin. Owner-consent probability considers premium, tenure, owner fragmentation and failed attempts.

## Viewshed

A 360-degree angular horizon estimates blocked azimuth, severe obstruction and potential view-premium loss. Surveyed building geometry should replace assumed MP2025 envelopes for decision use.

## Market calibration

Ledoit-Wolf covariance, exponentially weighted covariance diagnostics, Gaussian-mixture market regimes, transition probabilities, spatial market forecasting and conformal interval support. The scenario engine resolves the exact versioned regime artifact recorded by the calibration manifest and falls back to calibrated covariance before using explicit assumptions.

## Two-stage stochastic optimisation

First-stage action/start decisions are followed by scenario-specific execute or cancel recourse. Constraints include annual capital, cumulative liquidity, contractor resources, portfolio NOI, leverage, concentration and project dependencies. CVaR is included in the objective.

## Decision stability

Recommendations are rerun under NPV, CVaR and capex perturbations. The output reports action frequencies, stability scores, robust actions and fragile assets.

## Independent review

Valuation, planning/legal, tax/finance and investment-committee approvals are stored separately. Implementation remains blocked until all required roles approve.

All advanced outputs remain screening-level until verified company data and professional inputs are provided.
