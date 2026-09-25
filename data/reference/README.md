# Official market context

Six data.gov.sg datasets provide eight quarterly index series: private residential, Central Region office, Central Region retail, and industrial prices and rents. URA is the underlying source for residential/commercial data; JTC supplies industrial data through SingStat.

The raw API responses are checked in under `raw/`. `source_manifest.json` records retrieval times and URLs; the snapshot records SHA-256 hashes, exact series labels, observation counts, dates, geographic scope, missing comparisons, and age. Latest values are derived from the newest completed quarter present, with exact quarter-on-quarter and year-on-year comparisons. Missing quarters are not bridged or interpolated. Cached data stays visibly dated when refresh fails.

```shell
python scripts/refresh_public_data.py
python scripts/refresh_public_data.py --offline
```

Source data are reused under the [Singapore Open Data Licence](https://data.gov.sg/open-data-licence). Each snapshot series links directly to its official dataset. These are currently published, potentially revised histories, not archived historical publication vintages. They cannot establish point-in-time trading performance. Regional macro data do not turn fictional asset financials into verified underwriting. No hospitality, mixed-use or HDB observations are invented.

The prior hardcoded office price movement of 4.6% was replaced by the index-derived 111.3 / 110.9 - 1 = approximately 0.36% for 2026-Q2. All price/rental change rates now follow the same reproducible rule.
