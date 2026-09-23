export const END_TO_END_MODEL=`flowchart LR
  subgraph Sources[Evidence and data sources]
    A[Company portfolio workbook]
    B[Underwriting workbook]
    C[URA SPACE MP2025]
    D[OneMap and public market data]
    E[Historical leases planning capex outcomes]
  end
  Sources --> F[Ingestion validation and provenance]
  F --> G[Evidence ledger and versioned snapshot]
  G --> H[Asset digital twin]
  H --> I[Zoning and physical capacity]
  H --> J[Lease cash flows and DCF]
  H --> K[ML ensemble quantiles and hierarchical priors]
  H --> L[Operational ESG and tenant risk]
  I --> M[Approval survival and development option]
  J --> N[Action cash flows]
  K --> N
  L --> N
  M --> N
  N --> O[Correlated heavy tailed scenarios]
  O --> P[Action NPVs VaR CVaR and loss probability]
  P --> Q[Zoning adjusted Buy Retain Sell selection]
  Q --> R[Five year multi period MILP]
  R --> S{Human review required?}
  S -->|Yes| T[Human review overrides and open conditions]
  S -->|No| U[Decision record]
  T --> U
  U --> V[Outcome monitoring backtesting and Bayesian updates]
  V --> H`;
export const ASSET_DECISION_GRAPH=`flowchart TD
  START([Start]) --> Load[Load asset and source records]
  Load --> Evidence[Validate evidence and conflicts]
  Evidence --> Zoning[Resolve MP2025 zoning and title boundary]
  Zoning --> Capacity[Calculate statutory physical de facto and economic capacity]
  Capacity --> Forecast[Forecast NOI rent vacancy cap rate and approval]
  Forecast --> Actions[Value Hold Retrofit Repurpose Redevelop Sell]
  Actions --> Risk[Simulate correlated downside scenarios]
  Risk --> Selection[Apply en bloc transformation view supply and lease adjustments]
  Selection --> Gate{Verified inputs and controls?}
  Gate -->|No| Review[Data Required or Human Review]
  Gate -->|Yes| Complete[Buy Invest Retain Monitor or Sell Release]
  Review --> END([End])
  Complete --> END`;
export const PORTFOLIO_GRAPH=`flowchart TD
  START([Start]) --> Portfolio[Load portfolio and constraints]
  Portfolio --> Twins[Build and evaluate asset twins]
  Twins --> Scenarios[Create portfolio scenario set]
  Scenarios --> Optimiser[Multi period mixed integer optimiser]
  Optimiser --> Budget[Annual capital and liquidity checks]
  Budget --> Risk[CVaR NOI and concentration checks]
  Risk --> Feasible{Feasible portfolio?}
  Feasible -->|No| Revise[Relax or review constraints]
  Revise --> Optimiser
  Feasible -->|Yes| Plan[Five year action and capital plan]
  Plan --> Committee[Investment committee review]
  Committee --> Audit[Versioned decision and audit record]
  Audit --> Monitor[Monitor realised outcomes]
  Monitor --> START`;
export const MODEL_TRAINING_GRAPH=`flowchart LR
  History[Verified historical financial lease planning and capex data] --> Split[Chronological train and holdout split]
  Split --> Ensemble[LightGBM plus Ridge point forecast]
  Split --> Quantiles[LightGBM P10 P50 P90 models]
  Split --> Hierarchy[Empirical Bayes asset class shrinkage]
  Split --> Survival[Discrete approval survival model]
  Ensemble --> Registry[Versioned model registry]
  Quantiles --> Registry
  Hierarchy --> Registry
  Survival --> Registry
  Registry --> Backtest[Temporal and policy backtests]
  Backtest --> Gate{Validation thresholds passed?}
  Gate -->|No| Block[Block production deployment]
  Gate -->|Yes| Deploy[Enable company calibrated predictions]`;
