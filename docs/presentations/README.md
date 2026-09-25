# Presentation collection

- [Client deck: editable PowerPoint](client/Real_Estate_Portfolio_Intelligence_Client_Deck.pptx) and [PDF](client/Real_Estate_Portfolio_Intelligence_Client_Deck.pdf): 22 slides, including zoning and zoning ML interpretations, six editable charts and decision plots.
- [Demo workflows: editable PowerPoint](workflows/Portfolio_Intelligence_Demo_Workflows.pptx) and [PDF](workflows/Portfolio_Intelligence_Demo_Workflows.pdf): 11 slides explaining overall selection and dashboard components with editable diagrams.
- [Detailed report: Word](../reports/Real_Estate_Dashboard_Interpretation_Report.docx) and [PDF](../reports/Real_Estate_Dashboard_Interpretation_Report.pdf).
- [Live dashboard](https://real-estate-portfolio-multi-asset-quant.onrender.com/).

The decks preserve the reviewed presentation versions. Their GitHub Pages links refer to saved results; the Render URL above now provides live demo calculations. All asset examples are fictional. Zoning ML diagnostics are illustrative fixtures, not trained forecasts or automatic investment instructions. Detailed development analysis remains separate from the core action rankings.

Source scripts and original delivery/layout manifests accompany each deck. Builders require Python with python-pptx and lxml; finalization uses PyMuPDF. PDF export and font embedding use Windows, Microsoft PowerPoint and pywin32. Run each builder, renderer and finalizer in sequence. The builders read the repository's checked-in public snapshot. IBM Plex fonts and their licence are in client/fonts. Rebuilding against later snapshots can change values and file hashes.
