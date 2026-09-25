"""Generate the public server's model data at build time, never on first visit."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    # Refuse to run over a private portfolio; the public Dockerfile only copies examples.
    private_portfolio = ROOT / 'data/processed/portfolio.json'
    if private_portfolio.exists():
        raise RuntimeError('Build the public demo in a clean checkout without a private processed portfolio.')
    environment = {**os.environ, 'PUBLIC_DEMO_MODE': '1', 'FERE_MASTER_SEED': '20260923'}
    for script in ('create_public_demo.py', 'build_digital_twin_dashboard.py', 'build_public_dashboard_snapshot.py', 'build_public_api_snapshot.py'):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT, env=environment, check=True)
    dashboard = json.loads((ROOT / 'data/processed/digital_twin_dashboard.json').read_text(encoding='utf-8'))
    if len(dashboard.get('assets', [])) != 10 or not all(a['asset_id'].startswith('DEMO-') for a in dashboard['assets']):
        raise RuntimeError('Public hosting expects exactly the ten fictional demo assets.')
    print('Public demo prepared: 10 assets; all dashboard API calculations available.', flush=True)


if __name__ == '__main__':
    main()
