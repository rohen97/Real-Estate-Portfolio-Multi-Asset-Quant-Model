from fastapi.testclient import TestClient
import pytest
from apps.api import main
from apps.api.hosted import create_app


def test_public_host_requires_explicit_demo_mode(tmp_path,monkeypatch):
    monkeypatch.delenv('PUBLIC_DEMO_MODE',raising=False)
    with pytest.raises(RuntimeError,match='PUBLIC_DEMO_MODE'):
        create_app(tmp_path)


def test_public_service_serves_web_and_calculations_but_no_approval_writes(tmp_path,monkeypatch):
    monkeypatch.setenv('PUBLIC_DEMO_MODE','1')
    monkeypatch.setattr(main,'DEMO_MODE',True)
    (tmp_path/'index.html').write_text('<h1>Public demonstration</h1>')
    with TestClient(create_app(tmp_path)) as client:
        assert 'Public demonstration' in client.get('/').text
        assert client.get('/api/health').json()['results_loaded']
        assert client.get('/api/portfolio').json()['assets'][0]['asset_id'].startswith('DEMO-')
        assert client.post('/api/decisions',json={}).status_code==403
        assert client.post('/api/reviews',json={}).status_code==403
        assert client.get('/api/decisions').status_code==403
        assert client.get('/api/artifacts/underwriting-template').status_code==404
        invalid=client.post('/api/optimise',json={'capital_budget_m':-1})
        assert invalid.status_code==422
        result=client.post('/api/optimise',json={'capital_budget_m':500,'max_projects':0}).json()
        assert result['feasible']
        assert all(x['action'] in ('Hold','Sell') for x in result['selections'])


def test_list_and_detail_do_not_duplicate_full_risk_samples(monkeypatch):
    monkeypatch.setattr(main,'DEMO_MODE',True)
    with TestClient(main.app) as client:
        asset=client.get('/portfolio?limit=1').json()['assets'][0]
        assert all('scenario_samples_m' not in x for x in asset['actions'])
        detail=client.get('/assets/'+asset['asset_id']).json()
        assert all('scenario_npvs_m' not in x for x in detail['actions'])
        assert client.get('/assets/'+asset['asset_id']+'/scenario-samples').json()['draws']==5000
