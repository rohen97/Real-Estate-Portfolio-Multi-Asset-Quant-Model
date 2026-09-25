"""Public demo: the complete web app and its calculation API on one origin."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from apps.api.main import app as api, health
from apps.api import main as api_module
import json

ROOT = Path(__file__).resolve().parents[2]
CALCULATIONS = {'/api/optimise', '/api/optimise/two-stage', '/api/optimise/stability'}


def create_app(web_directory: Path | None = None) -> FastAPI:
    if os.getenv('PUBLIC_DEMO_MODE') != '1':
        raise RuntimeError('Public hosting requires PUBLIC_DEMO_MODE=1 and fictional demo data.')

    if not api_module.DEMO_MODE:
        raise RuntimeError('Set PUBLIC_DEMO_MODE before importing the API.')
    for relative in ('data/processed/portfolio.json', 'data/processed/ura_mp2025.sqlite',
                     'data/calibration/market_scenarios.json', 'data/calibration/calibration_report.json',
                     'data/observed/underwriting_validation_report.json', 'models/registry/portfolio-forecasting-latest.json'):
        if (ROOT / relative).exists():
            raise RuntimeError('Public hosting requires a clean demonstration checkout without private input artifacts.')
    for relative, key in (('data/processed/digital_twin_dashboard.json', 'assets'),
                          ('data/synthetic/semisynthetic_twins.json', None)):
        path = ROOT / relative
        if path.exists():
            value = json.loads(path.read_text(encoding='utf-8'))
            assets = value[key] if key else value
            if len(assets) != 10 or any(not str(asset.get('asset_id', '')).startswith('DEMO-') for asset in assets):
                raise RuntimeError('The public service may expose only the ten fictional DEMO assets.')
    app = FastAPI(title='Public portfolio demonstration', docs_url=None, redoc_url=None)
    calculation_slot = asyncio.Semaphore(1)

    @app.middleware('http')
    async def public_access(request, call_next):
        path = request.url.path.rstrip('/') or '/'
        # Public visitors can calculate, but cannot impersonate reviewers or save decisions.
        if path.startswith('/api/reviews') or path == '/api/decisions':
            return JSONResponse({'detail': 'Decision and approval records are not available on the public demo.'}, status_code=403)
        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and not (request.method == 'POST' and path in CALCULATIONS):
            return JSONResponse({'detail': 'This public demo permits calculations only.'}, status_code=403)
        expensive = request.method == 'POST' or path.endswith('/advanced-analysis') or path.endswith('/scenario-samples')
        if expensive:
            if calculation_slot.locked():
                return JSONResponse({'detail': 'A calculation is already running. Please try again shortly.'}, status_code=503, headers={'Retry-After': '5'})
            async with calculation_slot:
                return await call_next(request)
        return await call_next(request)

    @app.get('/health')
    def readiness():
        status = health()
        status['digital_twins_loaded'] = (ROOT / 'data/processed/digital_twin_dashboard.json').is_file()
        ready = status['portfolio_loaded'] and status['results_loaded'] and status['digital_twins_loaded']
        return JSONResponse({**status, 'status': 'ok' if ready else 'starting'}, status_code=200 if ready else 503)

    app.mount('/api', api)
    app.mount('/', StaticFiles(directory=web_directory or ROOT / 'dist', html=True), name='dashboard')
    return app
