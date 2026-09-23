# Known limitations

- The model now uses the live URA SPACE Master Plan 2025 land-use layer, but zoning polygons do not replace title-lot, written-permission, SDCP or project-specific development-control verification.
- The workbook is a catalogue, not an underwriting or fixed-asset ledger.
- All Singapore records are geocoded, but 15 zoning cases require title-lot or use-permission review.
- Address-point snapping cannot establish legal site boundaries; title-lot GeoJSON and written-permission review are required for the 15-item zoning queue.
- Site area, current GFA, NLA, title/tenure, valuation, NOI, leases, debt and capex are missing for most assets and are replaced by visible proxies.
- Development-control parameters beyond land use/GPR are configurable assumptions pending handbook and written-permission review.
- Approval-stage probabilities are illustrative and not calibrated to Far East or URA application histories.
- Valuation and action cash flows are demonstrative rather than professional valuations.
- The MILP is operational but consumes proxy action economics.
- International assets are ingested but excluded from the Singapore zoning model.
- No model output predicts live investment performance.
