# Research-based model upgrade recommendations

## Executive conclusion

The existing proof of concept reduces zoning to legal plot ratio, expected attainable plot ratio and a linear option-value calculation. The research supports replacing this with a layered development-capacity engine that separates statutory permission, physical feasibility, approval probability, market absorption, delivery timing and economic viability.

## 1. Zoning component redesign

### 1.1 Replace the single plot-ratio constraint with a constraint graph

Represent every planning and development rule as a typed constraint with source, effective date, geometry, units and precedence. At minimum include:

- permitted and conditional uses;
- plot ratio/FAR by use;
- site coverage and building coverage ratio;
- maximum/minimum height, storeys and height planes;
- front, side and rear setbacks;
- minimum parcel width/depth and lot area;
- open-space, landscaping and public-realm requirements;
- parking, loading, servicing and access requirements;
- daylight, ventilation, fire access and core-efficiency allowances;
- heritage, conservation, easement and infrastructure reservations;
- affordable housing or community-benefit obligations;
- parcel amalgamation and subdivision rules.

The engine should return the binding constraint, not merely the maximum GFA.

### 1.2 Use geometry-aware development envelopes

Generate feasible three-dimensional development envelopes from parcel polygons rather than multiplying land area by plot ratio. Evaluate irregular sites, multiple towers/podiums, residual unusable geometry and circulation/core loss. Use quasi-Monte Carlo sampling or constrained search to generate candidate massing configurations.

Research indicates that parameters have unequal and nonlinear effects: parcel width can dominate housing density, while side setbacks can dominate building coverage. Therefore, the interface should show marginal capacity sensitivities by rule.

### 1.3 Separate four definitions of capacity

1. Statutory capacity: maximum capacity explicitly allowed by the written rules.
2. De facto capacity: capacity suggested by observed approvals and bunching near height/FAR limits.
3. Physically attainable capacity: capacity surviving geometry, access, engineering and efficiency constraints.
4. Economically viable capacity: capacity whose risk-adjusted residual value is positive after time, cost and absorption.

This avoids treating every legally permitted square metre as equally valuable or achievable.

### 1.4 Infer hidden or de facto restrictions

Observed buildings often bunch below apparent height/FAR limits. Compare distributions of realised height, floor area and site coverage against formal limits to estimate latent restrictions such as discretionary design review, infrastructure limitations or recurring approval practice.

Model this as a posterior distribution over effective constraints rather than silently reducing the plot ratio.

### 1.5 Introduce staged approval probabilities

Replace one approval probability with a multi-stage process:

- pre-application feasibility;
- planning submission acceptance;
- technical-agency clearance;
- public/committee review;
- conditions discharge;
- construction permit.

Each stage should have a transition probability and time-to-event distribution. Use survival/hazard modelling when real approval histories become available. The result should expose expected approval time, probability of approval by date, probability of redesign and expected carrying cost.

### 1.6 Make zoning dynamic

Development stock is durable and costly to adjust. A demand or policy shock does not instantaneously produce the long-run optimum. Add construction lead times, demolition/redevelopment frictions, lease break constraints, temporary income loss and supply-pipeline interaction.

The model should compare immediate redevelopment with waiting, phased development and preserving a real option to redevelop later.

### 1.7 Add spatial equilibrium and spillovers

A parcel-level upzoning can change rents, accessibility, congestion, amenities and competing supply around it. Add neighbourhood features and network accessibility rather than treating the asset as spatially independent.

Useful outputs include accessibility to jobs/transit/amenities, local development pipeline, competing capacity, agglomeration benefits, congestion exposure and displacement/community impacts.

### 1.8 Add spatially explicit sensitivity maps

Sensitivity should not only report a portfolio-wide coefficient. Map where conclusions change when thresholds, buffers, density definitions or accessibility assumptions change. This reveals whether a recommendation is robust or driven by an arbitrary spatial definition.

### 1.9 Integrate climate and public-realm constraints

Include flood, extreme heat, energy/carbon retrofit requirements, transport disruption and public-realm accessibility. Climate exposure should change attainable GFA, capex, approval conditions, operating performance and required return rather than appearing as a separate ESG score.

### 1.10 Improve zoning explainability

For every asset show:

- written legal limits and sources;
- effective limits inferred from evidence;
- binding constraints;
- feasible envelope range;
- P10/P50/P90 attainable GFA;
- unused but non-economic capacity;
- marginal value of relaxing each binding rule;
- approval pathway and delay risk;
- conditions that would change the recommendation.

## 2. Recommended zoning data model

Create versioned entities for Parcel, PlanningRule, RuleSource, GeometryConstraint, UsePermission, ApprovalStage, DevelopmentConcept and CapacityResult. Every calculated output should link back to source documents and effective dates.

A CapacityResult should include statutory_gfa, de_facto_gfa, physical_gfa, economic_gfa, binding_constraints, concept_geometry, efficiency_ratio, probability_distribution, approval_timeline, option_value and provenance_snapshot.

## 3. Valuation and action-engine upgrades

- Replace the featured asset's calibrated action values with fully calculated cash flows.
- Model construction drawdowns, lease disruption, financing, taxes, sale costs, absorption and stabilisation explicitly.
- Decompose capitalisation rates into risk-free rate, property risk, liquidity, growth and evidence uncertainty.
- Add probability of loss, downside semi-deviation, expected shortfall and median NPV alongside expected NPV.
- Preserve correlations between rents, costs, cap rates, approval time and absorption.
- Use real-options valuation for wait, phase, expand, abandon and switch-use decisions.

## 4. Market-evidence upgrades

- Keep observation date separate from publication date.
- Store definitions and units with each observation.
- Display ranges and dispersion when sources are not directly comparable.
- Segment transactions by stabilisation, lease structure, quality, tenure and development potential.
- Use small specialised extraction, validation and calculation components rather than one monolithic LLM workflow.
- Treat LLM output as proposed evidence requiring schema validation and provenance, never as an authoritative fact.

## 5. Scenario-engine upgrades

- Add market regimes and transition probabilities.
- Simulate spatially correlated rent, vacancy and cap-rate shocks.
- Link planning delay to cost inflation, interest carry and market-cycle exposure.
- Calibrate dependency structures and tails from data rather than fixing one correlation matrix.
- Add Bayesian posterior updating and calibration diagnostics.
- Separate parameter uncertainty, model uncertainty, evidence uncertainty and irreducible outcome risk.

## 6. Portfolio-optimisation upgrades

Replace the current greedy selector with a formal mixed-integer multi-period optimisation model. Include:

- one action per asset;
- annual capital and liquidity constraints;
- timing of sale receipts and capex drawdowns;
- maximum concurrent developments;
- contractor and management capacity;
- geographic, use and tenant concentration;
- minimum income/NOI preservation;
- CVaR or downside-budget constraints;
- action dependencies and mutually exclusive projects;
- optional robust or stochastic optimisation across scenarios.

Monte Carlo should continue to produce scenarios and risk inputs; the optimiser should select decisions.

## 7. Spatial and machine-learning upgrades

- Derive urban-form signatures from parcel, street, building-footprint and remote-sensing data.
- Use self-supervised imagery models to detect neighbourhood change, but validate against observed transactions and planning records.
- Add mobility and accessibility features using explicit spatial-temporal graphs.
- Use spatial and temporal holdouts to avoid leakage from neighbouring parcels or future observations.
- Monitor geographic transferability: a model trained in one urban form may not generalise to another.

## 8. Agent-based modelling guidance

ABMs are useful for policy and market-response experiments, not as a default valuation engine. Parameters should come from observed behaviour, controlled decision experiments or calibrated revealed preferences. Reinforcement learning can model adaptive agents, but its reward function and learned policy require governance and out-of-sample tests.

## 9. Validation and governance upgrades

- spatial cross-validation and leave-area-out tests;
- temporal and market-cycle holdouts;
- calibration curves for approval probabilities;
- sensitivity maps showing where decisions change;
- backtests of predicted versus realised approval time, cost and value;
- challenger models and documented disagreement thresholds;
- fairness/distributional review of zoning and accessibility assumptions;
- privacy controls for mobility and trajectory data;
- decision records that preserve data, rules, geometry, model and scenario versions.

## 10. Prioritised implementation roadmap

### Phase 1 - highest value

1. Constraint graph and versioned zoning-rule schema.
2. Statutory/de facto/physical/economic capacity separation.
3. Binding-constraint and sensitivity reporting.
4. Staged approval probability and time model.
5. Fully calculated action cash flows instead of calibrated outputs.
6. Formal multi-period portfolio optimiser.

### Phase 2

1. Parcel geometry and massing generation.
2. Spatial accessibility, competing supply and pipeline features.
3. Real-options timing model.
4. Spatial/temporal validation and uncertainty decomposition.
5. Climate and infrastructure constraints integrated into economics.

### Phase 3

1. Remote-sensing and street-image change detection.
2. Agent-based policy simulations.
3. Mobility/event demand models.
4. Participatory mapping and community-impact evidence.

## Immediate codebase implications

The current zoning function should be split into rule ingestion, rule resolution, geometry generation, feasibility, approval and economic-capacity services. The current action and optimiser functions should consume distributions from those services rather than a single unused-capacity number.
