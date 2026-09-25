# Model integrity revision 0.9

This release changes the economic and statistical meaning of several outputs. Earlier demonstration results are superseded; changes in simulated portfolio value are not investment performance.

## Selection and potential value creation

Selection now uses the same transparent expected incremental NPV less nonnegative loss-CVaR score as its standalone action comparison. Hold is required as the explicit counterfactual. Unverified en-bloc, transformation, view, supply and lease-decay screens remain visible as research hypotheses and are not mechanically added to cash-flow NPV. This avoids counting the same capitalised benefit twice.

`opportunity` reports the modelled incremental value, margin over Hold and runner-up, and break-even additional discounted cost. The annual-equivalent incremental NPV yield divides the NPV by the horizon annuity factor and the current value; it is not a total return and must not be added to NOI yield or market index growth. Expected alpha and total-return fields remain null without an out-of-sample, cost-adjusted risk benchmark. Changing `synthetic_financials` to false cannot bypass verification: title/planning, values, NOI, evidence source, owner, current evidence dates and action costs/cashflows must be supported.

## Lease cashflows and approval timing

Lease cashflows now use monthly forward periods from an explicit valuation date, prorate the original lease around expiry, and apply non-renewal downtime once at the supplied expiry. The old method penalised every later year for the same vacancy and discarded rent earlier in the expiry year. A zero collection rate remains zero. Contractual rent stays flat unless an explicit escalation is supplied; renewal/reletting uses the assumed market rent. Monthly exported cashflows reconcile to PV, including terminal value at the final month.

This is still a single-expiry expected-cashflow screen. Later lease expiries, breaks, incentives, tenant improvements, reletting costs and future market vacancy need real schedules. Aggregated future-year lease NOI is not evidence of observed historical NOI.

The approval-path simulator validates probabilities, makes lognormal duration means agree with the displayed means, and separates time until stopping (success or failure) from duration conditional on successful completion. The legacy `redesign_probability` key is explicitly a failure-probability alias; actual redesign probability is not estimated. Stage probabilities remain uncalibrated assumptions.

## Spatial constraints and missing evidence

Envelope generation preserves polygon holes. An empty setback-constrained footprint produces no feasible envelope instead of reverting to the entire site. Storeys and physical floor area reconcile and stay within the legal GFA and height limits. The advanced wrapper does not invent a redevelopment valuation when no envelope is feasible. Geometry, parking, daylight and planning remain screening assumptions requiring project evidence.

An empty/invalid building inventory now yields unavailable viewshed metrics, not zero obstruction or 100% open sky. Angular bins work at arbitrary supported resolutions. Map legends distinguish fictional polygons from cached planning layers; display fixtures are not legal zoning or calibrated forecasts.

## Public application and traceability

All fifteen tabs can be inspected on GitHub Pages through an allowlisted public snapshot. Saved calculations cannot be rerun there. The same frontend with the public Python service supports calculations and suppresses private decision/approval writes. API numeric requests have explicit bounds and reject nonfinite values. Large action draw arrays are served only through the dedicated scenario endpoint; list/detail requests carry summaries. File-backed API reads are cached by path, size and nanosecond modification time.

Result identity includes a deterministic code fingerprint, canonical public market snapshot hash, input asset and scenario seed. Core portfolio factors are shared; idiosyncratic randomness uses stable asset hashes and is unaffected by input ordering. The report and snapshot retain their data/model identifiers.

## Remaining limits

The ten public assets are fictional. No verified tenant, title, transaction, development-cost, debt or outcome evidence has been created. Calibrated-looking chart metrics are replaced with explicit source/status labels. Heuristic uncertainty, limited optimisation scenarios, annual funding buckets, fixed action assumptions and small synthetic evaluation samples remain limitations. Independent audit residuals establish consistency with encoded constraints, not the truth of real-world inputs or legal feasibility. The deployment Blueprint requires an authenticated Render account before a live backend exists.

See [valuation](valuation_revision.md), [optimisation](optimisation_revision.md), [simulation](simulation_revision.md), [forecasting](forecasting_revision.md), [official data](../data/reference/README.md), and the formal dashboard report for methods, tests and graph interpretations.
