from fastapi.testclient import TestClient
from apps.api.main import app
c=TestClient(app)
def test_status_and_portfolio():
 h=c.get('/health').json();assert h['status']=='ok' and (h['ura_index_loaded'] or h.get('demo_mode'));s=c.get('/data/status').json();assert s['portfolio_assets']>=10 and s['singapore_assets']>=10;p=c.get('/portfolio?country=Singapore&limit=20').json();assert len(p['assets'])>=10
def test_asset_and_verification_gate():
 a=c.get('/portfolio?country=Singapore&limit=1').json()['assets'][0];d=c.get('/assets/'+a['asset_id']).json();assert d['verification_required'];assert d['capacity']['statutory_gfa_sqm']>=d['capacity']['physical_gfa_sqm']
def test_optimiser():
 r=c.post('/optimise',json={'capital_budget_m':500,'max_projects':20}).json();assert 'feasible' in r

def test_workflow_status_endpoints():
 assert c.get('/market/public').status_code==200
 assert c.get('/underwriting/status').status_code==200
 assert c.get('/calibration/status').status_code==200
 z=c.get('/zoning/exceptions');assert z.status_code==200 and z.json()['count']>=0
 assert c.get('/artifacts/underwriting-template').status_code in (200,404)
 assert c.get('/artifacts/zoning-exceptions').status_code in (200,404)

def test_v2_model_endpoints():
 assert c.get('/models/registry').status_code==200
 assert c.get('/models/backtest').json()['status'] in ('synthetic_pilot_backtest','public_synthetic_demo')
 assert len(c.get('/pilot/v2').json()['assets'])==10
 assert c.get('/legacy/comparison').status_code==200

def test_visualisation_endpoints():
 matrix=c.get('/visualisations/scenario-matrix').json();assert len(matrix['factors'])==6 and len(matrix['correlation'])==6
 asset=c.get('/portfolio?country=Singapore&limit=1').json()['assets'][0]
 samples=c.get('/assets/'+asset['asset_id']+'/scenario-samples').json();assert samples['draws']==600 and len(samples['samples'])==5

def test_zoning_map_geojson():
 asset=c.get('/portfolio?country=Singapore&limit=1').json()['assets'][0]
 result=c.get('/zoning/map/'+asset['asset_id']+'?radius_m=500');assert result.status_code==200
 body=result.json();assert body['type']=='FeatureCollection' and len(body['features'])>1
 assert body['features'][-1]['geometry']['type']=='Point'

def test_zoning_prediction_endpoints():
 asset=c.get('/portfolio?country=Singapore&limit=1').json()['assets'][0]
 prediction=c.get('/zoning/prediction/'+asset['asset_id']);assert prediction.status_code==200
 body=prediction.json();assert body.get('status')=='not_trained' or 'prediction' in body
 discrepancy=c.get('/zoning/discrepancy-map');assert discrepancy.status_code==200 and discrepancy.json()['type']=='FeatureCollection'


def test_digital_twin_dashboard_endpoints():
 dashboard=c.get('/digital-twins/dashboard');assert dashboard.status_code==200
 body=dashboard.json();assert body['status'] in ('synthetic_software_validation','not_run')
 if body['status']=='synthetic_software_validation':
  assert body['portfolio_summary']['assets']>=10 and len(body['environments'])==3
  asset_id=body['assets'][0]['asset_id'];detail=c.get('/digital-twins/assets/'+asset_id)
  assert detail.status_code==200 and detail.json()['twin']['asset_id']==asset_id
