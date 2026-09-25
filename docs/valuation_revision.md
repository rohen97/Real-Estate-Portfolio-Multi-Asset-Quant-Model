# Valuation and decision-basis revision — 25 September 2026

This revision corrects accounting identities and prevents unverified development upside from being interpreted as investment alpha. It does not establish market outperformance. The public assets, action assumptions and most underwriting values remain fictional or illustrative.

## Annual DCF and action comparison

Both `packages/valuation/engine.py` and `packages/actions/real_options.py` now use year-end cashflows, discounted at periods 1 through the holding horizon. The terminal value capitalises the following year's NOI and deducts selling costs. The old twin engine discounted year-one income at time zero and applied different growth rates to Hold and actions.

Hold is the exact comparison baseline: zero incremental NPV, zero incremental cashflow, zero incremental capex. Hold still has an absolute asset PV. Lower exit cap rates increase this absolute PV but cannot create incremental alpha merely by choosing Hold.

Actions use the same growth, discount rate, horizon and disposal-cost assumptions as Hold. NOI uplift starts after completion; disruption is charged through the operating cashflows, including partial execution years. Capex is charged at time zero in the annual screening engine. The financing allowance was removed from the unlevered decision NPV; mixing debt interest with an asset discount rate is not a consistent equity valuation.

Each development action has an explicit success branch and a failed-execution branch. The latter retains Hold income and loses 55% of planned capex, using the earlier implementation's 55% sunk-cost assumption. Expected NPV is the probability-weighted sum of these two branch NPVs. The assumption is visible and uncalibrated; it is not an observed recovery rate. Full planned capex remains available to the capital-budget optimiser as a conservative funding requirement. `success_incremental_npv_m` and `failure_incremental_npv_m` support coherent probability-based simulations.

Additional terminal-value uplift is zero in the default action specifications because the NOI improvement is already capitalised. Capacity residual is displayed as `capacity_option_unpriced_m` and excluded from DCF: its separate valuation overlaps with improvement/capitalisation assumptions and lacks independent verification. The historic positive Wait/Phase/Abandon/Expand heuristics are no longer credited. Their legacy numeric fields are zero with `status=not_valued`; this means no premium credited, not an estimated market option value of zero. A calibrated transition/exercise policy is needed before assigning a premium.

The action API retains its existing positional arguments and fields. New optional scenario arguments are `rent_growth`, `selling_cost_rate`, `capex_multiplier`, `approval_multiplier` and `sale_price_multiplier`. Sale proceeds are immediate; negative `capex_m` is the net cash receipt. `annual_cashflows_m` contains periods 1 onward, `time_zero_cashflow_m` is separate, and `incremental_cashflows_m` includes period zero. `pv_after_m` is the operating/sale PV before expected capex; `expected_project_pv_m` includes capex. This prevents silent interpretation of a mixture of cash receipts and asset values.

## Monthly redevelopment and financing

`packages/actions/detailed_cashflow.py` charges construction on all approved rebuilt GFA, including floors replacing the existing building. Incremental GFA is retained only for the separate LBC screening input. For example, rebuilding 24,000 sqm at SGD4,200/sqm costs SGD100.8m, not SGD33.6m from charging only the extra 8,000 sqm.

Every project investment includes the current asset's opportunity value at time zero. Owned-asset action NPV is compared with retaining that same asset through the same horizon: `npv_m = project_npv_m - hold_npv_m`. Both sides include the current asset value, so it cancels in the incremental comparison instead of being omitted from project returns. Acquire is explicitly compared with making no acquisition and includes buyer duty.

Predevelopment professional fees are sunk before the approval decision. Failure retains the Hold income and terminal asset value and loses those fees. Success retains income through predevelopment, has construction-period downtime, leases up and sells. Probability weights whole branches, rather than arbitrarily scaling all future costs and inventing an extra failure penalty. Approval probabilities, growth, lease-up and stabilised NOI yield remain supplied assumptions.

The principal decision NPV is unlevered. A separate equity ledger implements, for every month:

`equity cashflow = project cashflow + debt draws - cash interest - principal repayment`.

Development-only debt is drawn against construction/contingency/relocation/demolition/known LBC spending, accrues monthly interest and is fully repaid on sale. Acquisition and professional-fee borrowing are not assumed. Conditional draws and repayments reconcile exactly. `equity_npv_m` is unavailable unless an explicit equity discount rate is supplied; changing leverage cannot change unlevered NPV. Equity IRR includes the current asset opportunity cost and is not an incremental IRR. Nonconventional cashflows with multiple sign changes do not receive an arbitrary IRR root.

Disposal dates add actual calendar months rather than rounding the horizon to whole years. The existing seller-duty helper receives gross consideration rather than net-of-fee proceeds. No statutory tax rate was invented or changed by this revision.

## LBC and decision readiness

Unknown Land Betterment Charge stays `total_sgd=null`, with `decision_ready=false`, `valuation_status=incomplete_inputs`, explicit blockers and `excluded_costs`. Numeric legacy NPVs are retained for dashboard compatibility but exclude the unknown charge; they must not be described as executable underwriting.

Supplying `assessed_lbc_m` permits an externally assessed charge, including an explicitly assessed zero. The older additional-area/rate function is retained as a screening estimate, and even a supplied rate continues to require assessment verification: actual LBC depends on pre/post chargeable value, sector, use, tenure and applicable rules. Supplying a number does not verify it. `inputs_verified` is false by default; the advanced wrapper always leaves it false because its site rectangle and envelope remain synthetic.

Corporate income tax, ABSD, existing debt, lease top-up and other unprovided levies are not modelled by these inputs. The output states these exclusions so a completed arithmetic model is not mistaken for a complete transaction appraisal.

## En-bloc reconciliation and interpretation

`packages/actions/enbloc.py` solves the residual equation `offered land value + buyer duty(on that offer) = residual before duty`. The earlier implementation calculated duty on current strata value, which did not reconcile with its proposed land offer. Construction remains based on total allowable GFA. Finance remains a supplied effective development-cost allowance, explicitly excluding acquisition finance.

The supplied consent threshold now affects the calculation. Without observed voting shares, a binomial screen assumes independent equal-weight owners and uses the existing heuristic support score. This assumption is uncalibrated, is not a legal vote and remains a decision blocker. A supplied observed consent share is compared with a supplied threshold; legal voting basis still requires verification. Higher required consent cannot improve modeled completion probability.

The legacy `expected_discounted_enbloc_value_m` remains the success-weighted sale component. New fields separately report the retained asset on failure and `incremental_npv_vs_hold_m`, comparing the same future transaction date with Hold. Failure does not destroy the existing asset. Attempt costs are an explicit input. Intervening income is assumed common to the two alternatives and cancels; disrupted income requires an additional project-specific cost input.

The advanced wrapper labels synthetic geometry, inferred tax-use shares and unavailable surrounding-building evidence. An empty surrounding-building list cannot establish an unobstructed view. If no feasible replacement envelope exists, no redevelopment monetary value is reported: existing GFA cannot be substituted for permission to rebuild. All advanced results remain screening outputs.

## Analytical examples and tests

For current value SGD120m, NOI SGD5.8m, 10 years, 7.8% discount, 5% exit cap, 2.5% growth and 2.5% selling costs, the revised annual Hold PV is SGD114.439529m. Incremental action NPVs are Hold 0, Retrofit -0.998635m, Repurpose -9.797801m, Redevelop -30.543156m and Sell +2.560471m. These are arithmetic examples using defaults, not transaction recommendations. Conservative corrected values can be lower than earlier prototype outputs.

For 24,000 sqm rebuilt at SGD4,200/sqm, SGD120m current value, SGD5.8m NOI, SGD12m assessed LBC and the detailed default timing/costs, construction is SGD100.8m, incremental unlevered NPV is -SGD56.484343m, total debt draws and repayments are both SGD72.5184m and conditional financing interest is SGD13.661784m over 75 months. This illustrates why asset opportunity cost, total replacement construction cost and the Hold counterfactual matter.

`tests/unit/test_valuation_invariants.py` checks a closed-form one-period DCF, exact Hold zero, weighted branch identities, sale accounting, cost monotonicity, no duplicate capacity credit, full rebuilt-area costs, every-month financing reconciliation, leverage invariance of unlevered NPV, project-minus-Hold identity, failed-approval cashflows, missing-LBC gating, exact disposal dates, ambiguous IRR rejection, offer/duty reconciliation, and threshold/fallback behavior. Existing cap-rate tests now compare absolute Hold PV while requiring incremental Hold NPV to remain zero.

Final focused command: `python -m pytest tests/unit/test_valuation_invariants.py tests/unit/test_remaining_components.py tests/unit/test_v2_model.py tests/unit/test_forecasting_invariants.py -q` — **51 passed**. A workspace temporary directory was supplied for sandbox-compatible pytest fixtures.

## Primary methodology references

- NYU Stern / Aswath Damodaran, [Valuation framework](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html): distinguish asset cashflows before debt payments from equity cashflows after financing; use the corresponding discount rate.
- NYU Stern / Aswath Damodaran, [Valuation Basics](https://pages.stern.nyu.edu/~adamodar/pdfiles/papers/value.pdf): net debt issuance adds to equity cashflow; principal repayment reduces it.
- Singapore Land Authority, [Land Betterment Charge](https://www.sla.gov.sg/properties/land-betterment-charge/): assessment requires the applicable sector/use framework and current official schedules. These references support the methodology; they do not verify the fictional input assets.
