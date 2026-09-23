# Visualisation methodology

## Portfolio

- Recommended-action bar chart.
- Selection-signal donut chart.
- Asset segment by action heatmap.
- Longitude/latitude MP2025 zoning scatter map coloured by GPR.

## Evidence and governance

- Evidence records by source sheet.
- Observed versus proxy input status.
- Decision-gate status chart.
- Evidence-to-decision process visual.

## Zoning

- Statutory-to-economic capacity waterfall.
- Zoning sensitivity bars.
- Interactive Leaflet map with coloured MP2025 polygons, asset marker, land-use/GPR popups, legend and adjustable radius.
- Surrounding GPR versus distance scatterplot.
- P10/P50/P90 attainable-GFA chart.

## Valuation and actions

- DCF annual cash-flow chart.
- Current, DCF and terminal value comparison.
- Expected versus P10 action NPVs.
- Capital requirement versus execution period.

## Scenarios

- Action NPV violin distributions.
- Six-factor correlation heatmap for rent, vacancy, cap rate, interest, cost inflation and approval delay.
- P10/P50/P90 action ranges.
- Probability-of-loss chart.

## Selection

- Action-selection waterfall from base NPV through zoning, transformation and risk adjustments.
- Adjusted NPV by action.
- Operating, market and incremental return decomposition against required return.
- View, supply and lease-decay risk deductions.

## Portfolio optimisation

- Five-year capex, capital-release and active-project timeline.
- Optimised action allocation donut.

## Legacy and ML diagnostics

- Legacy current-performance/future-potential quadrant scatter.
- Published-versus-corrected score bars.
- Predicted-versus-actual NOI scatter.
- Residual histogram.
- Quantile coverage and policy hit-rate chart.

Plotly is lazy-loaded into a separate application chunk so the portfolio table and navigation load without waiting for the charting library.
