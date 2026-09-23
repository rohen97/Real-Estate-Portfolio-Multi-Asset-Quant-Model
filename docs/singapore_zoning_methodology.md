# Singapore zoning methodology

## Current source

The model uses the public URA SPACE Master Plan 2025 land-use service directly:

- Map application: https://eservice.ura.gov.sg/maps/index.html?service=mp
- ArcGIS layer: https://maps.ura.gov.sg/arcgis/rest/services/MP25/Updated_Landuse_gaz/MapServer/45
- Layer title: UPD GAZ MP25 LAND USE
- URA SPACE description: Master Plan 2025 with approved amendments incorporated
- Local retrieval: 23 September 2026
- Indexed features: 113,418

The previous MP2019 and September 2025 amendment indexes are no longer used by the application.

## OneMap Planning Area API

The OneMap Planning Area API is available as an optional validation and aggregation connector. Its documented boundary years extend only through 2019 and it requires an API token. It is useful for administrative comparison and population analytics, but it is not used as the Master Plan 2025 zoning source.

The MP2025 URA layer already provides current REGION_N, PLN_AREA_N and SUBZONE_N attributes for every matched zoning polygon.

## Pipeline

1. Import and deduplicate the company workbook while preserving source sheet and row.
2. Geocode Singapore properties through the official OneMap address-search API.
3. Download all current MP2025 land-use features from URA SPACE in paginated ArcGIS queries.
4. Build a local SQLite geometry index with land use, detailed use, GPR, region, planning area and subzone.
5. Perform local point-in-polygon matching for portfolio coordinates.
6. Separate statutory, physical, de facto, expected-approved and economic capacity.
7. Simulate staged planning approval probabilities and durations.
8. Feed capacity distributions into action valuation, downside scenarios and portfolio optimisation.

## Verification control

A current MP2025 polygon match does not replace professional planning verification. Title-lot boundaries, cadastral geometry, written permission, Special and Detailed Control Plans, conservation controls, development-control handbooks and other agency requirements must still be checked for each project.

## Current portfolio result

- 260 deduplicated company properties.
- 177 Singapore properties.
- 172 geocoded and matched against live MP2025.
- Five unresolved addresses retained for manual review.
- All missing company financial and site inputs remain visibly labelled as proxies.
