# Open-source zoning and LULC review

Reviewed repositories:

- malawrim/Spatially-Complete-Zoning-Maps
- connorcrowe/to-lulc-scale

## Adopted methods

- Hierarchical broad and detailed zoning classes.
- Parcel and raster predictor stacking.
- Building height/density, road density, population, impervious surface, vegetation, water and proximity features.
- Spatially separated validation and local error maps.
- Feature importance, confusion matrices and per-class metrics.
- High-resolution imagery tiling and lazy processing.
- Overlapping U-Net patches and interactive Leaflet layers.

## Improvements over the reference implementations

- URA MP2025 remains legal truth; ML is only a challenger.
- Stratified planning-area validation replaces random pixel splitting.
- Macro F1, balanced accuracy, log loss and multiclass Brier replace R-squared as classification measures.
- Temperature-calibrated probabilities, entropy, top-three classes and mandatory abstention.
- Softmax probability blending with a Hann window replaces averaging numeric class IDs.
- Socioeconomic and political variables are excluded from the initial predictor set.
- Legal-versus-observed-versus-predicted discrepancy is an explicit review workflow.
- Future rezoning is trained separately from current zoning classification.

## Synthetic validation status

The included synthetic challenger validates software execution only. Production use requires historical Singapore zoning snapshots, parcel/building features and independently labelled LULC imagery. The future-change synthetic model currently has weak discrimination and remains blocked from decision use.
