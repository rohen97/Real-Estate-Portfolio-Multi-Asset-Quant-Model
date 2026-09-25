# Numerical review of the revised public run

Reviewed 25 September 2026 from the regenerated `public/data/api_snapshot.json` (143 allowlisted routes) and digital-twin snapshot. All ten asset records remain fictional. Official Singapore price/rent indices are separate aggregate context and do not verify these property inputs. Figures below are SGD millions unless stated otherwise.

## Core portfolio and constraints

- Core proxy value totals **564.00** and annual proxy NOI **25.84**. Independent action rankings are **8 Sell / 2 Hold**. Every transaction-readiness signal remains **Data Required / Monitor**.
- The default multi-period portfolio selects **3 Sell / 7 Hold**, with **zero construction capex**, **167.70 sale receipts**, **9.947621 expected incremental NPV**, **20.025108 positive-loss CVaR95**, and **3.940089 risk-adjusted objective** at the 0.30 penalty.
- The selected sales are DEMO-001, DEMO-003 and DEMO-009. They remove 7.73 annual baseline NOI, leaving **70.0851%** of the original 25.84, close to the 70% retention floor. This income constraint explains why the portfolio does not implement all eight independent Sell rankings.
- Year-one net funding is **−167.70**: this is a receipt surplus, not negative construction expense. Remaining model liquidity is 500 + 167.70 = **667.70**. It is an annual capital-reserve approximation, not a verified bank balance.
- Joint risk is compared with **20.108753** summed marginal CVaR calculated on the **same 128 scenarios**. The small reduction is consistent with strong shared exposures in a sale-dominated plan. The original 5,000-draw card sum, 19.198553, is retained separately and must not be compared as if it used the same sample.

These Sell preferences reflect the assumed immediate sale prices relative to discounted retained income and the 7.8% required return. They do not establish exploitable mispricing in actual Singapore properties. Correcting artificial Hold uplift, duplicate terminal/capacity credits and understated construction costs can legitimately make modelled development less attractive; a more optimistic answer is not automatically a better model.

## Two-stage portfolio and perturbation

The saved two-stage plan also commits to three sales and seven Holds, with no construction. The probability-weighted result is **7.633548 expected incremental NPV**, **11.281396 positive-loss CVaR95**, and **4.813199 objective** at penalty 0.25. The scenario outcomes are **9.979280 Base**, **−11.281396 Downside**, and **21.857028 Upside**, with probabilities 0.50/0.25/0.25.

The downside now reduces actual sale proceeds and NPV together; it is no longer guaranteed profitable merely because an aggregate NPV multiplier stayed positive. All ten actions execute and none cancels in each saved scenario. This run exercises funding and loss sensitivity; it does not demonstrate the benefit of construction cancellation. Probability-weighted first-year proceeds are **165.603750**.

These three assumed scenarios are not the core optimiser's 128 observations, so their CVaRs should not be interpreted as a clean before/after improvement. The twenty-run stability output is assumption sensitivity rather than a future-return interval. Modal asset actions need not be jointly feasible.

## Digital twins are a separate underwriting population

Generated value is **1,312.8964** and generated annual NOI **57.1837**, rather than the core proxies above. The classification is **Mixed Use 1, Commercial 2, Mall 2, Industrial 2, Residential 2, Hotel 1**. There are **0 verified real portfolio anchors**, **10 fictional asset contexts**, **80% populated-context completeness** and **0% verified underwriting**.

| Measure | Base | Stress | Structural change |
|---|---:|---:|---:|
| Constrained expected incremental NPV | 79.8007 | 66.9548 | 68.0952 |
| Sale receipts | 420.7940 | 267.3002 | 367.5736 |
| Construction capex | 0 | 0 | 0 |
| Portfolio Hold / Sell count | 4 / 6 | 4 / 6 | 8 / 2 |
| Environment baseline annual NOI | 58.041453 | 44.371938 | 55.454051 |
| Predictive P10–P90 synthetic coverage | 74% | 78% | 76% |
| Recommendation/oracle agreement | 80% | 90% | 70% |
| Mean synthetic per-asset regret | 4.7791 | 1.0251 | 4.8792 |

The environment-specific income baseline now drives retention constraints as well as cashflow valuation. Counting sales without checking asset size can mislead: the two structural-case sales release 367.57, more than the six stress sales' 267.30. All standalone-vs-portfolio selections remain available; no count is silently substituted for another.

Nominal 80% interval coverage is evaluated over 50 synthetic action outcomes in each environment. Coverage below 80% is evidence of assumed-model mismatch with the separate hidden-effect evaluation generator, not measured failure against real properties. Two assets change standalone recommendation across the three cases. The three-case stability score is not the twenty-run portfolio perturbation statistic.

The twin portfolio's zero sampled positive-loss CVaR in some cases means none of the selected **128** model outcomes shows a loss. It does not prove zero actual market risk or eliminate uncertainty outside those assumptions. Hold is zero incremental risk relative to itself; retained property value still has absolute market risk.

## Advanced results and diagnostics

All advanced development and en-bloc outputs have `decision_ready=false`. LBC remains unassessed; surrounding-building/view evidence is unavailable. No empty view chart establishes an unobstructed view.

For DEMO-001, expected project NPV is **−40.154802**, Hold investment NPV is **−3.132386**, and incremental redevelopment NPV is their difference, **−37.022416**. These include the current asset opportunity cost consistently. Conditional development debt draws and repayments both equal **30.799036**; no financing cash is counted as unlevered value. Equity NPV is unavailable without a supplied equity discount rate.

Its en-bloc residual before buyer duty is **3.773736**, proposed land offer **3.622987** and buyer duty **0.150749**, reconciling to rounding. The difference from current assumed value is large and negative. Those numbers exclude unknown LBC and remain conditional; the gross 80.9172 completed value is not profit available to the owner.

The ten public NOI formula rows now reconcile exactly: MAE **0.004600**, RMSE **0.004733**, bias **−0.004600**, and **100%** interval coverage. They are fictional formula examples. The registry states no training occurred; action/legacy-policy hit rates remain unavailable instead of using fabricated percentages. Zoning agreement compares hand-authored fixture labels and is neither classifier accuracy nor legal verification.

## Cross-layer checks performed

The review independently checked all 50 core action records and ten advanced records: Hold's incremental NPV/risk/capex are zero; all stored core chart samples contain the same 5,000 observations used by cards; displayed CVaRs are nonnegative; only Sell has negative capex; advanced NPV equals project less Hold; debt draws equal principal repayment; en-bloc cost residuals reconcile; and all three twin plus both core portfolio audits pass with zero violations at the stated tolerance.

No real-world alpha, transaction feasibility or legal approval conclusion follows from those software consistency checks. Final package source fingerprints should be refreshed after all code changes, even when an unrelated change leaves these figures unchanged.
