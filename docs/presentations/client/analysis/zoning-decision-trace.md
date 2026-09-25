# Zoning outputs and investment decisions

Reviewed 25 September 2026 against the repository snapshot used for the client deck.

The zoning ML code remains present. Its public outputs are hand-authored fictional examples, and its predictions are not consumed by the main action-ranking engine. The detailed zoning-based development valuation also remains a separate analysis. These are implementation limits, not merely missing slide explanations.

| Component | Outputs | Current use |
| --- | --- | --- |
| Planning lookup | Land use, gross plot ratio (GPR), spatial match and review flags | Defines assumptions for capacity and contributes to evidence readiness. Public records are fictional. |
| Current-zoning ML challenger | Land-use class, subtype, GPR band, probabilities, entropy, abstention and discrepancy reasons | Analyst diagnostics; not an automatic financial recommendation. No trained public prediction is provided. |
| Future-change classifier | Zoning/GPR change score and qualitative signal | Separate research screen; no calibrated public forecast or defined investment horizon is supplied. |
| Capacity screen | Floor-area ceilings, unused gross floor area (GFA), binding constraints and sensitivity estimates | Identifies a development case to investigate. The simple residual is excluded from additive action value. |
| Development envelope | Tower, storey, height and area alternatives | Selected gross area feeds the separate monthly redevelopment cash flows. |
| Detailed redevelopment and en-bloc valuation | Incremental redevelopment NPV versus Hold and residual land value | Separate feasibility evidence; these outputs are not substituted into the core action templates or portfolio optimiser. |

## What should a decision maker do?

An ML discrepancy prompts evidence review. Verified capacity creates a candidate development design. That design must be costed, timed and compared with retaining the existing property, including opportunity costs and unresolved charges. Retention, improvements, redevelopment and sale then need comparable cash flows and the same portfolio constraints.

Hold means retain the asset. Sell means dispose of it; the relevant comparison includes net sale proceeds and retained value. Retrofit, Repurpose and Redevelop are improvement alternatives. Buy is not implemented and would require an acquisition-price comparison, transaction costs and a purchase benchmark. Data Required / Monitor is an evidence status, not a conclusion that Hold is economically best.

The current main action ranking uses expected incremental NPV less a CVaR risk penalty, followed by evidence readiness and portfolio constraints. Zoning ML predictions and separate detailed redevelopment NPVs are not inputs to those rankings today. A new connection must reconcile time horizons, costs, scenario cash flows and baseline definitions; simply adding a zoning residual or replacing a single NPV number would be unsound.

## Fictional DEMO-001 example

- Site: 2,600 sqm; assumed GPR: 4.2; existing GFA: 7,862.4 sqm.
- GPR-based ceiling: 10,920 sqm; core adjusted capacity: 10,046.4 sqm; unused capacity: 2,184 sqm.
- Approval-weighted GFA uses an assumed 62% factor, not an ML forecast or an approval.
- Separate geometric envelope: 10,774.19 sqm under different assumptions from the core capacity screen.
- Detailed redevelopment: approximately **−S$37.02m incremental NPV versus Hold**. Assessed Land Betterment Charge and other verified evidence remain missing.
- The separate core annual templates favour Sell at approximately **+S$3.76m expected incremental NPV**, before the readiness block. This is not a zoning-ML conclusion.
- Management signal: **Data Required / Monitor**, not an executable Sell instruction.

Potential investment advantage would come from finding mispriced capacity that can actually be delivered profitably. Neither a predicted zoning label nor unused floor area establishes that advantage.

## Implementation evidence

- `packages/zoning/challenger.py`: LightGBM classification, spatial validation, calibration and abstention code.
- `packages/zoning/change_model.py`: separate future-change classifier.
- `scripts/create_public_demo.py`: untrained, abstained, hand-authored zoning display fixtures.
- `packages/orchestration/engine.py`: main calculation path does not load the zoning prediction file.
- `packages/valuation/engine.py`: core action templates use assumed capex and uplift parameters.
- `packages/actions/real_options.py`: screening capacity residual explicitly excluded from action NPV.
- `packages/orchestration/advanced.py`: geometric envelope feeds detailed development calculations separately.
- `packages/selection/engine.py`: candidate scoring and evidence readiness; acquisition not assessed.

A read-only perturbation check changed unused capacity from 0 to 100,000 sqm and screening residual from S$0m to S$100m. Core action NPVs did not change. This confirms that those diagnostics are not priced in the main action engine.

## Corrections delivered

The client deck now has dedicated zoning slides 7–10. The dashboard probability charts and metrics exclude unsupported fixture, untrained, synthetic-trained, uncalibrated and abstained values using explicit evidence checks. Visible copy explains the separate analytical paths. These presentation changes do not complete the missing valuation integration or train a model on real historical data.
