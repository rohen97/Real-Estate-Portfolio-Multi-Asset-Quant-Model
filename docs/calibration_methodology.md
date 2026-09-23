# Historical calibration methodology

## NOI forecast

Requires at least 30 consecutive asset-year observations. A ridge regression uses prior NOI, occupancy, cap rate and maintenance capex. Validation uses a chronological holdout rather than a random split.

## Planning approval

Requires at least 25 verified planning-stage outcomes. Stage probabilities use a Beta(1,1) posterior and observed submission-to-decision durations.

## Execution risk

Requires at least 20 completed capex/development projects with valid budgets and actual spend. The model estimates mean and P90 cost overrun.

## Command

```powershell
.\tools\uv.exe run python scripts\calibrate_models.py
```

The calibration report remains blocked until minimum evidence thresholds are met. The system never silently fits models to insufficient history.
