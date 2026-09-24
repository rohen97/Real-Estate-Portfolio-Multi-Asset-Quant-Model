# Semi-synthetic digital-twin dashboard

Implemented on 24 September 2026.

## Purpose

The dashboard demonstrates the new portfolio model when verified underwriting is unavailable. It retains the real Far East portfolio identity, segment, location and URA MP2025 context, then fills missing financial and operating fields with deterministic synthetic values.

## Dashboard UI foundation

The dashboard shell and digital-twin workspace use the MIT-licensed Tabler open-source admin dashboard package (`@tabler/core` 1.5.1). Tabler supplies responsive cards, navigation, badges, tables, forms, alerts, progress indicators and layout utilities while the portfolio charts and model-specific components remain implemented in this repository.

## Portfolio twins

The generator creates one twin for each geocoded Singapore asset. Each twin includes:

- Real portfolio identity, address, coordinates, segment and planning context.
- Synthetic site area, GFA, NLA, valuation, NOI, occupancy, debt and capex.
- Twelve years of synthetic financial history.
- Synthetic lease, capex and planning-event histories.
- Field-level provenance identifying real anchors and synthetic underwriting.

Generated underwriting is never presented as verified company data.

## Model environments

The dashboard evaluates every twin under three controlled environments:

1. Base conditions.
2. Market and construction-cost stress.
3. Structural demand change.

For each environment, the model compares Hold, Retrofit, Repurpose, Redevelop and Sell using expected NPV, P10/P50/P90 ranges, probability of loss, CVaR, execution time and capital requirements.

## Portfolio optimisation

The multi-period optimiser selects actions and start years subject to capital, liquidity, concurrent-project, development-exposure and minimum-NOI constraints. The dashboard displays recommended allocations and the five-year capital plan.

## Validation boundary

Simulated realised outcomes are used only to test interval coverage, decision regret and stability. These statistics demonstrate software behaviour under the generator assumptions; they are not estimates of actual Far East investment performance.

Run:

```powershell
.venv/Scripts/python.exe scripts/build_digital_twin_dashboard.py
```
