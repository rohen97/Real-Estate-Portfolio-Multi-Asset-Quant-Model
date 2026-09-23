# Economic portfolio decision model v2

## Positioning

The November 2025 weighted scorecard is frozen as a comparison baseline. It is not the primary recommendation engine.

## End-to-end layers

1. Company portfolio register from Far_East_Asset_List.xlsx.
2. Evidence ledger and versioned domain contracts.
3. Asset digital twins linking financials, leases, planning, capex, ESG and market context.
4. Live URA SPACE Master Plan 2025 zoning and title-boundary resolution.
5. LightGBM/Ridge NOI ensemble with P10/P50/P90 quantile models.
6. Empirical-Bayes partial pooling for sparse asset classes.
7. Discrete approval-survival model with stage duration distributions.
8. Lease-level cash flows, action NPVs and real options.
9. Correlated heavy-tailed scenarios and downside measures.
10. Five-year MILP with annual capital, liquidity, concurrent-project, development-exposure and NOI-preservation constraints.
11. Legacy-versus-economic comparison.
12. Temporal and policy backtesting.
13. Model registry, artifact hashes and synthetic-model governance gates.

## Production gate

Synthetic-pilot models are blocked from portfolio use unless the caller explicitly passes --allow-synthetic-model. Company-calibrated deployment requires completed underwriting and historical financial, planning, capex and outcome records.

## Full command

```powershell
.\scripts\run-end-to-end.ps1 -PortfolioWorkbook "C:\Users\RohenVeeraKumaran\Downloads\Far_East_Asset_List.xlsx" -UseSyntheticPilot
```

Remove -UseSyntheticPilot and provide -CompletedUnderwritingWorkbook when verified company history is ready.
