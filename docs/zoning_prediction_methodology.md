# Zoning prediction and LULC methodology

## Separation of truth and prediction

URA SPACE Master Plan 2025 remains the authoritative legal zoning source. Machine learning does not overwrite legal zoning. It is used as a challenger for missing, conflicting or suspicious records and for future-change screening.

The architecture was informed by the open-source Spatially-Complete-Zoning-Maps and to-lulc-scale projects. We adopted their spatial predictor stacks, hierarchical labels, accuracy maps, image tiling and interactive map ideas, while replacing random pixel splits, class-number averaging and uncalibrated forced predictions.

## Parcel and spatial features

- Site area, compactness and aspect ratio.
- Building height and building density.
- Road density and impervious/vegetation/water fractions.
- Population and employment density.
- Distance to MRT, roads, parks and commercial nodes.
- Neighbourhood mean GPR at 250, 500 and 1,000 metres.
- Nearby high-density, residential, commercial and industrial shares.
- Observed LULC and conservation status.

Planning area and subzone are retained for grouped validation but excluded as predictors to reduce geographic memorisation.

## Hierarchical challenger

1. Predict broad zoning core: Residential, Commercial, Mixed Use, Industrial, Hotel, Institutional, Transport, Open Space or Special.
2. Predict detailed land-use subtype.
3. Predict GPR band.
4. Return top-three classes, calibrated probability, normalised entropy and abstention state.

The LightGBM probabilities are temperature-calibrated on held-out planning areas. Predictions abstain when confidence is below 50% or entropy exceeds 0.82.

## Spatial validation

Validation uses stratified planning-area groups rather than random pixels. Reported measures include macro F1, balanced accuracy, log loss, multiclass Brier score, confusion matrix and spatial fold results.

## LULC U-Net

The optional imagery pipeline uses a four-level U-Net. Large images are predicted through overlapping patches. Softmax probabilities—not class IDs—are blended with a Hann weighting window before the final class and entropy maps are produced.

Classes: building, road, paved, vegetation, water, construction and vacant land.

Install optional imagery dependencies from requirements-imagery.txt.

## Discrepancy and future change

The discrepancy service compares legal zoning, predicted zoning, observed physical LULC, GPR band and current use. High-severity differences enter the review queue.

The separate rezoning model estimates future zoning/GPR change probability from historical Master Plan snapshots. Synthetic training exists only for software validation; production training requires historical Singapore amendments.

## Outputs

- data/processed/zoning_predictions.json
- data/processed/zoning_discrepancy_map.geojson
- models/zoning-challenger/<version>/zoning_challenger.joblib
- models/zoning-change/<version>/rezoning_probability.joblib

These generated and potentially private artifacts are excluded from the public repository.
