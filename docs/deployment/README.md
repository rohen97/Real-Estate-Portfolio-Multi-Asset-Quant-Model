# Public deployment validation — 25 September 2026

Live URL: https://real-estate-portfolio-multi-asset-quant.onrender.com/

The Render service responded with healthy portfolio, results and digital-twin readiness. A clean Edge browser loaded all 15 tabs, found all 15 mobile navigation entries, and completed a live multi-period calculation with no JavaScript errors, failed site responses or localhost requests. See render_access_validation.json.

All three POST calculation endpoints returned results. Multi-period optimisation was feasible with zero constraint violations; two-stage and stability responses are included here. Stability completed 20 of 20 runs. This is functional demo validation, not load testing or evidence of investment alpha.

The service uses fictional public-demo data. The health check reports ura_index_loaded=false; a private full spatial index is not part of this public deployment. Public review/signoff writes remain disabled.

GitHub Pages continues serving its saved snapshot. At validation, Render did not return Access-Control-Allow-Origin for https://rohen97.github.io. Before enabling PUBLIC_API_URL on GitHub, save CORS_ORIGINS=https://rohen97.github.io in Render and redeploy, then verify cross-origin responses. The direct Render dashboard works without this cross-origin connection.

The original checkout also contains regenerated model snapshots that remove contextual market/spatial evidence. These were not promoted over the reviewed canonical examples.
