# Rebuilding the dashboard report

Run `python scripts/report/build_report.py` from the repository root after preparing the public model snapshot. The report tools require `python-docx`, `matplotlib` and `numpy`; these are document-generation dependencies, not requirements for the hosted API. The builder checks source hashes and creates 28 figures, chart interpretations, the Word document and a source manifest in `docs/reports`. It also copies Word to `public/reports`.

On Windows with Microsoft Word and `pywin32` installed, run `python scripts/report/render_report.py` to update contents/page fields, export PDF, update binary hashes and copy both final documents to `public/reports`. The process uses a hidden Word instance. PDF generation is a separate local publication step; the Linux service serves the checked-in documents and does not require Microsoft Word.

The report reads saved demonstration results. Refresh `docs/reports/validation_results.json` only with checks actually executed, and review all pages after rendering. Keep both report copies and their manifests in the same release as the snapshots they explain.
