# Optimisation revision — 25 September 2026

The scheduling solvers now enforce the actual project and funding constraints, explicitly distinguish joint portfolio risk from marginal risk scores, and publish an independent audit of each selected schedule. These changes improve internal consistency; they do not establish investment alpha or validate fictional inputs.

## Behaviour changed

- Development share is an exact asset-count limit: `floor(asset_count * max_development_share)`. A zero share, or one asset at a 45% share, permits zero development projects. The old minimum-one override is removed.
- The full duration and funding must fit inside the horizon. A seven-year project can no longer enter a five-year model with only five years of its costs.
- Deferred NPVs and action loss distributions are discounted by `(1 + discount_rate)^-(start_year - 1)`. The rate is action-specific, then asset-specific, then the default 7.8%. Budgets and reserves remain nominal cash amounts. The action NPV is assumed incremental to its supplied passive baseline at action start; passive pre-start carry contributes zero incremental NPV. This aggregate-discount approximation cannot substitute for re-underwriting deferred rents, leases, costs and terminal cash flows.
- Sale receipts enter the funding plan at settlement, including `sale_delay_years`; baseline NOI is retained before settlement and removed afterwards. End-of-year netting still assumes within-year cash availability: this is an annual liquidity screen, not a daily treasury forecast.
- Two-stage recourse enforces simultaneous-project limits, contractor resources, NOI continuity and cumulative liquidity **in every scenario and every year**. Future sale receipts cannot finance earlier spending. Scenario delays move construction spending, disruption and contractor use; execution beyond the horizon is prohibited.
- Cancelling a development project uses that asset's explicit Hold economics and Hold funding, plus an 8% default cancellation fee charged in decision year 1. A negative Hold can no longer be replaced by a cheaper artificial project cancellation. Without an explicit feasible Hold, cancellation is unavailable. Scenarios are assumed known before construction; this is a two-stage contingent planning model, not a multi-stage learning policy.
- Dependencies apply to all start options and actual scenario execution. The prerequisite must be selected and completed before the dependent development starts. Concentration and financing constraints are independently audited as well. The 60%-of-gross-capex leverage formula is retained only as an explicitly labelled financing proxy, not a balance-sheet LTV calculation.
- A scenario NPV multiplier `m` applies as `NPV + abs(NPV)*(m-1)`, so downside scenarios worsen negative NPVs instead of making them less negative. Additional construction-cost shocks also reduce NPV by their discounted cost, rather than affecting only budget capacity. These coarse stress assumptions are not empirically calibrated probabilities or a factor cash-flow model.
- A loss-CVaR penalty cannot reward all-profitable outcomes: the risk variable measures `max(0, -portfolio_NPV)`, with nonnegative eta. Unpenalised expected NPV, loss CVaR and penalised objective are now separate fields.

## Joint versus marginal risk

`optimise_multi_period` accepts `scenario_npvs_m` on every feasible action, with identical scenario ordering across every asset and action. It then optimises expected NPV minus the CVaR of **aggregate positive-part portfolio loss**. Probabilities default to equal weights or can be supplied with `scenario_probabilities`; the default tail level is 95%. Correlations are inherited from the input scenarios, not inferred by the optimiser. The synthetic dashboard uses a deterministic aligned 128-draw subset of its 2,048-draw simulator. Small-sample tail estimates remain sensitive to the generator and sample size.

Without aligned scenarios, the legacy sum of individual nonnegative CVaR penalties remains available and is explicitly labelled `sum_of_marginal_cvar_penalties`. `portfolio_loss_cvar_m` is null in that mode. A sum of asset CVaRs is not presented as joint portfolio risk.

The two-stage optimiser calculates joint CVaR from its scenario-level portfolio outcomes and recourse decisions. The three illustrative default scenarios are a coarse stress test; the worst 5% in such a distribution may be identical to the worst scenario and should not be described as a calibrated 1-in-20 loss.

## Output and audit contract

Both solvers expose `selections`, `portfolio_expected_npv_m`, `risk_adjusted_objective_m`, `annual_plan`, `constraint_audit` and `constraint_violations`. Two-stage retains `first_stage`, `objective` and schedule aliases for compatibility. Its top-level annual plan is explicitly probability-weighted recourse; each scenario also has its own actual plan, selections, cancelled commitments, payoff and audit. Planned first-stage expected NPVs are not the recourse-weighted outcome: per-commitment `recourse_expected_npv_m` and the portfolio outcome make the difference explicit.

The audit recomputes one-selection-per-asset, annual cash, each-year cumulative liquidity, simultaneous projects, NOI continuity and applicable additional constraints from selected schedules. It does not use the solver constraint matrix or assume that solver success proves feasibility. Every check reports its name, left-hand side, bound, violation and pass/fail at 1e-6 tolerance. Any audit failure prevents a result from being marked feasible. This validates the encoded plan, not the accuracy of input costs or legal feasibility.

Selection rows expose `discount_factor`, `discount_rate`, `undiscounted_expected_npv_m`, actual discounted `expected_npv_m`, and full capex, receipt, income-loss and resource schedules. Scenario arrays are not repeated in published selection rows.

## Stability reporting

The perturbation run now reports successful and failed runs separately, includes every input asset, and uses null rather than NaN when no audited feasible samples exist. Modal frequencies are conditional on successful runs; the feasibility rate is separate. `modal_action` replaces the misleading conceptual meaning of `robust_action`, which remains a compatibility alias. Independent modal choices need not form a jointly feasible portfolio.

`objective_mean_m` and `objective_p10_m` now summarise the actual **risk-adjusted objective**. `portfolio_expected_npv_mean_m` and `portfolio_expected_npv_p10_m` report unpenalised expected value separately. Perturbed capex/receipt changes also change economic NPV; they no longer affect funding while leaving value untouched. None of these perturbation percentiles are forecast confidence intervals, independent backtests or evidence of alpha.

## Regression evidence

Focused tests: `tests/unit/test_optimisation_revision.py` plus the existing multi-period and two-stage/stability smoke tests: **19 passed** on 25 September 2026.

1. A single asset at 0% or 45% development share selects Hold (zero permissible projects).
2. An overlong project is rejected instead of silently truncating its funding.
3. A 110m start-value project forced into year 2 at 10% discount rate is worth 100m at decision time and retains its entire funding requirement.
4. Two two-year projects with concurrency one are staggered into years 1 and 3.
5. A 100m project and 100m sale settling in year 3, with only 50m initial funding, cannot execute the project before year 3.
6. A one-year scenario delay shifts a two-year project's spending to years 2/3 and discounts 110m to 100m; a project that cannot finish is not executed.
7. A -10m Hold cannot be displaced by a -100m project cancelled for a cheap fee. A genuine cancellation retains the 2m Hold cost and adds its 0.8m cancellation fee to both NPV and cash funding.
8. An all-profitable 10m scenario produces zero loss CVaR and a 10m objective, with no artificial CVaR reward.
9. Opposite aligned [-10,+10] and [+10,-10] exposures give zero joint loss CVaR despite 20m summed marginal CVaR. The joint formulation chooses the hedge over an alternative with greater expected value but a larger combined tail loss.
10. Exact weighted CVaR correctly splits discrete probability mass at the tail boundary (46m in the supplied fixture).
11. A manually corrupted funding schedule triggers the independent audit with an 80m maximum residual.
12. Dependencies enforce predecessor completion for later start options, probabilities must sum to one, downside shocks worsen negative NPVs, objective/stability names match their data, and entirely infeasible perturbation runs produce no NaN.

## Sale and risk-comparison audit addendum

Malformed positive `Sell.capex_m` is rejected: a sale must encode its net proceeds as nonpositive capex. A sale settlement delay also discounts its aggregate immediate-sale incremental NPV while retaining passive income until settlement. The approximation retains the same baseline convention as deferred developments; detailed sale timing requires cash-flow underwriting.

Two-stage scenarios now accept `sale_receipt_multiplier`: base 1.00, downside 0.90 and upside 1.05 by default. The multiplier changes both actual cash funding and incremental NPV by the discounted receipt difference. Custom scenarios default to 1.00 when the field is absent. These are explicit assumed exit-price shocks in addition to the aggregate NPV stress, not measured market forecasts.

For aligned joint scenarios, `sum_of_marginal_cvar_95_m` is recomputed from the same selected scenario arrays and weights as portfolio CVaR, allowing a valid diversification comparison. The original card-level input sum is separately available as `sum_of_input_marginal_cvar_95_m`; sample sizes can differ and those quantities must not be used to infer diversification.

After these two additional sale regressions, focused validation is **21 passed**. A 121m immediate-sale incremental NPV settling two years later at 10% discounts to 100m; a 10m NPV sale with 100m receipts stressed to 90% has 90m available funding and approximately zero NPV.
