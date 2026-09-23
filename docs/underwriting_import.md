# Underwriting import workflow

## Workbook

Use the generated Far East Underwriting Data Request workbook. Yellow cells are editable. Asset IDs, MP2025 matches and calculated validation fields must not be overwritten.

## Import command

```powershell
.\tools\uv.exe run python scripts\import_underwriting.py --workbook "path-to-completed-workbook.xlsx" --strict --rebuild
```

Without `--strict`, valid assets are imported and invalid assets remain on the error report. With `--strict`, any invalid asset causes a nonzero exit.

## Validation controls

- Required ownership, title, site, GFA, NLA, occupancy, valuation, NOI, current-use and evidence fields.
- Ownership and occupancy ranges.
- Positive site/GFA/NLA/valuation values.
- NLA cannot exceed GFA.
- NOI reconciliation to passing rent less operating expenses within 5%.
- Verification status must be Verified.
- Planning capacity remains provisional until title boundary and current use are both verified.

## Outputs

- `data/observed/portfolio_enriched.json`
- `data/observed/underwriting_validation_report.json`
- Normalised financial, lease, debt, capex, planning-history and comparable evidence JSON files.

Verified rows automatically replace proxy site, GFA, valuation, NOI and occupancy inputs in the next model rebuild.
