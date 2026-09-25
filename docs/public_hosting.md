# Full public dashboard hosting

GitHub Pages supports every tab from a saved public snapshot. Live Python calculations need a running backend. The repository includes a same-origin service that hosts both components, using only the ten fictional public assets.

## Render

1. Open [Deploy to Render](https://render.com/deploy?repo=https://github.com/rohen97/Real-Estate-Portfolio-Multi-Asset-Quant-Model) while signed in to your Render account.
2. Review the repository Blueprint: Docker web service, Singapore, free plan, `Dockerfile.public`, `/health` readiness endpoint, one worker. The free plan may sleep when idle and has limited resources.
3. Create the service and wait until its health check passes. Use the Render-issued URL for the full dashboard; all calculation requests then use its same-origin `/api`.
4. Optionally set the GitHub repository **Actions variable** `PUBLIC_API_URL` to `https://YOUR-SERVICE.onrender.com/api`, then dispatch the Pages workflow. The GitHub Pages URL will use that backend. `CORS_ORIGINS` includes `https://rohen97.github.io`.

These steps require an authenticated Render account. The code and deployment blueprint are ready; account creation or provider authorisation is not performed by this repository. No hosted-service URL is assumed to exist before provider deployment succeeds.

## Local reproduction

```shell
uv sync --frozen
PUBLIC_DEMO_MODE=1 uv run python scripts/prepare_public_demo.py
npm ci
VITE_PUBLIC_DEMO=1 VITE_API_BASE=/api npm run build
PUBLIC_DEMO_MODE=1 uv run uvicorn apps.api.hosted:create_app --factory --host 127.0.0.1 --port 10000 --workers 1
```

On PowerShell, set environment variables with `$env:NAME='value'` before running each command. Alternatively, `docker build -f Dockerfile.public -t real-estate-dashboard .` then `docker run --rm -p 10000:10000 real-estate-dashboard` reproduces the hosted configuration.

The public preparation command refuses an existing private processed portfolio; the API snapshot builder also rejects private calibration, spatial index and registry inputs. Use a clean checkout. Official aggregate market series are public context; asset-level financials and locations remain fictional.

## Runtime behaviour

The frontend waits for the API to become ready and offers retry during a cold start. One expensive calculation runs at a time; other calculation requests receive a clear retry response. Invalid, nonfinite or out-of-range budget/risk inputs are rejected. Public visitors cannot save review signoffs or decision records. Calculation outcomes are transient; no paid database or persistent disk is required.

The Dockerfile copies only application code, checked-in examples, public reference data and web assets. Private data folders, credentials, caches and local artifacts are excluded. This demonstration is not a private-data production service: authenticated users, authorisation, durable audit storage, operational monitoring and a reviewed deployment architecture would be required before hosting real underwriting.

## Regeneration and rollout

`python scripts/prepare_public_demo.py` produces the canonical examples, digital twins, all-tab API snapshot and saved default optimiser runs. Snapshot entries contain exact inputs and model/data provenance. The report builder under `scripts/report` reads these saved outputs. Run tests and refresh the report before publishing a revised model.

The CI workflow tests Python, frontend checks and the Docker build. Main updates publish Pages; Render auto-deploys after provider-linked checks pass when the service has been created. Revert the release commit to roll back the code and saved snapshots together. Unset `PUBLIC_API_URL` and redeploy Pages to return to saved results if the backend is unavailable.

Sources: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [Render free instances](https://render.com/docs/free).
