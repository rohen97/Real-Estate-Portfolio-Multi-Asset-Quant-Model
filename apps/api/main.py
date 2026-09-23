from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json,sqlite3,os
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from packages.optimisation.engine import optimise_portfolio
from packages.scenarios.engine import scenario_covariance,action_scenario_samples
from packages.zoning.ura import zoning_map_geojson
ROOT=Path(__file__).resolve().parents[2];PORTFOLIO=ROOT/'data/processed/portfolio.json';RESULTS=ROOT/'data/processed/full_model_results.json';URA_DB=ROOT/'data/processed/ura_mp2025.sqlite';AUDIT=ROOT/'data/processed/audit.sqlite'
app=FastAPI(title='Far East Singapore Portfolio Intelligence API',version='0.2.0');app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173'],allow_methods=['*'],allow_headers=['*'])
class Opt(BaseModel):capital_budget_m:float=500;max_projects:int=20;max_development_share:float=.45;cvar_penalty:float=.3;minimum_liquidity_m:float=50
class Decision(BaseModel):asset_id:str;decision:str;reviewer:str;rationale:str;open_conditions:list[str]=[]
EXAMPLES=ROOT/'data/examples'
DEMO_MODE=os.getenv('PUBLIC_DEMO_MODE','0')=='1'
def read(path):
 if path.exists() and not DEMO_MODE:return json.loads(path.read_text())
 fallback={PORTFOLIO:EXAMPLES/'demo_portfolio.json',RESULTS:EXAMPLES/'demo_full_model_results.json'}.get(path)
 return json.loads(fallback.read_text()) if fallback and fallback.exists() else []
def init_db():
 AUDIT.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(AUDIT) as c:c.execute('create table if not exists decisions(id integer primary key,asset_id text,decision text,reviewer text,rationale text,open_conditions text,timestamp text,model_version text)')
init_db()
@app.get('/health')
def health():return {'status':'ok','date':'2026-09-23','model_version':'economic-model-v2-zoning-ml-0.4','portfolio_loaded':PORTFOLIO.exists() or (EXAMPLES/'demo_portfolio.json').exists(),'demo_mode':DEMO_MODE or not PORTFOLIO.exists(),'ura_index_loaded':URA_DB.exists(),'results_loaded':RESULTS.exists()}
@app.get('/data/status')
def data_status():
 p=read(PORTFOLIO);r=read(RESULTS);return {'portfolio_assets':len(p),'singapore_assets':sum(x.get('country')=='Singapore' for x in p),'geocoded_assets':sum(x.get('latitude') is not None for x in p),'zoned_assets':sum(bool(x.get('ura_zoning',{}).get('matches')) for x in p),'modelled_assets':sum(x.get('model_status')=='provisional_proxy_run' for x in r),'portfolio_source':'Far_East_Asset_List.xlsx','ura_source':'Live URA SPACE Master Plan 2025 land-use layer','current_plan':'URA Master Plan 2025','current_plan_verification_required':True}
@app.get('/artifacts/underwriting-template')
def underwriting_template():
 path=ROOT/'outputs/far-east-underwriting-20260923/Far_East_Underwriting_Data_Request.xlsx'
 if not path.exists():raise HTTPException(404,'Underwriting template has not been generated')
 return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
@app.get('/artifacts/zoning-exceptions')
def zoning_exception_file():
 path=ROOT/'data/processed/zoning_exceptions.csv'
 if not path.exists():raise HTTPException(404,'Zoning exception export has not been generated')
 return FileResponse(path,filename=path.name,media_type='text/csv')
@app.get('/underwriting/status')
def underwriting_status():
 path=ROOT/'data/observed/underwriting_validation_report.json'
 return json.loads(path.read_text()) if path.exists() else {'status':'not_imported'}
@app.get('/calibration/status')
def calibration_status():
 path=ROOT/'data/calibration/calibration_report.json'
 return json.loads(path.read_text()) if path.exists() else {'status':'not_run'}
@app.get('/visualisations/scenario-matrix')
def visual_scenario_matrix():return scenario_covariance()
@app.get('/assets/{asset_id}/scenario-samples')
def visual_scenario_samples(asset_id:str):
 row=next((x for x in read(RESULTS) if x.get('asset_id')==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 return action_scenario_samples(row.get('actions',[]),600,20260923+abs(hash(asset_id))%10000)
@app.get('/visualisations/model-diagnostics')
def visual_model_diagnostics():
 path=ROOT/'data/processed/backtest_report.json';fallback=EXAMPLES/'demo_backtest_report.json';return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/models/registry')
def model_registry():
 path=ROOT/'models/registry/portfolio-forecasting-latest.json';fallback=EXAMPLES/'demo_model_registry.json';return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else {'status':'not_trained'}
@app.get('/models/backtest')
def model_backtest():
 path=ROOT/'data/processed/backtest_report.json';fallback=EXAMPLES/'demo_backtest_report.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/pilot/v2')
def pilot_v2():
 path=ROOT/'data/processed/pilot_model_v2.json';fallback=EXAMPLES/'demo_pilot_model_v2.json';return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/portfolio/v2')
def portfolio_v2():
 path=ROOT/'data/processed/full_portfolio_v2.json';fallback=EXAMPLES/'demo_full_portfolio_v2.json';return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/legacy/spec')
def legacy_spec():
 path=ROOT/'data/legacy/legacy_spec.json';return json.loads(path.read_text())
@app.get('/legacy/comparison')
def legacy_comparison():
 path=ROOT/'data/processed/legacy_comparison.json';fallback=EXAMPLES/'demo_legacy_comparison.json';return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else []
@app.get('/market/public')
def public_market():
 path=ROOT/'data/public/singapore_market_snapshot.json';fallback=EXAMPLES/'demo_market_snapshot.json'
 return json.loads((path if path.exists() else fallback).read_text()) if fallback.exists() or path.exists() else {'status':'not_refreshed'}
@app.get('/portfolio')
def portfolio(country:str|None=None,search:str|None=None,limit:int=500):
 rows=read(RESULTS) or read(PORTFOLIO)
 if country:rows=[x for x in rows if x.get('country','').lower()==country.lower()]
 if search:rows=[x for x in rows if search.lower() in (x.get('name','')+' '+x.get('address','')+' '+' '.join(x.get('segments',[]))).lower()]
 rows=rows[:limit];return {'assets':rows,'summary':{'assets':len(rows),'singapore':sum(x.get('country')=='Singapore' for x in rows),'requires_verification':sum(x.get('verification_required',False) for x in rows),'provisional_recommendations':sum(x.get('recommendation') is not None for x in rows)},'as_of':'2026-09-22'}
@app.get('/assets/{asset_id}')
def detail(asset_id:str):
 row=next((x for x in (read(RESULTS) or read(PORTFOLIO)) if x['asset_id']==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 return row
@app.get('/zoning/prediction/{asset_id}')
def zoning_prediction(asset_id:str):
 path=ROOT/'data/processed/zoning_predictions.json';fallback=EXAMPLES/'demo_zoning_predictions.json';path=fallback if DEMO_MODE or not path.exists() else path
 if not path.exists():return {'status':'not_trained','asset_id':asset_id}
 row=next((x for x in json.loads(path.read_text()) if x.get('asset_id')==asset_id),None)
 if not row:raise HTTPException(404,'Zoning prediction not found')
 return row
@app.get('/zoning/discrepancy-map')
def zoning_discrepancy_map():
 path=ROOT/'data/processed/zoning_discrepancy_map.geojson';fallback=EXAMPLES/'demo_zoning_discrepancy_map.geojson';path=fallback if DEMO_MODE or not path.exists() else path
 return json.loads(path.read_text()) if path.exists() else {'type':'FeatureCollection','features':[],'status':'not_trained'}
@app.get('/zoning/map/{asset_id}')
def zoning_map(asset_id:str,radius_m:int=750):
 row=next((x for x in read(RESULTS) if x.get('asset_id')==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 if row.get('latitude') is None or row.get('longitude') is None:raise HTTPException(422,'Asset has no verified coordinate')
 radius_m=max(100,min(radius_m,2000));return zoning_map_geojson(URA_DB,row['latitude'],row['longitude'],radius_m)
@app.get('/selection/{asset_id}')
def asset_selection(asset_id:str):
 row=next((x for x in read(RESULTS) if x.get('asset_id')==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 return {'asset_id':asset_id,'name':row.get('name'),'selection':row.get('selection'),'recommendation':row.get('recommendation'),'input_quality':row.get('input_quality'),'verification_required':row.get('verification_required')}
@app.get('/zoning/exceptions')
def zoning_exceptions():
 rows=[x for x in read(RESULTS) if x.get('country')=='Singapore' and x.get('zoning_model_status')=='review_required']
 return {'count':len(rows),'assets':[{'asset_id':x['asset_id'],'name':x['name'],'address':x.get('address'),'match_method':x.get('ura_zoning',{}).get('match_method'),'original_land_use':[m.get('lu_desc') for m in x.get('ura_zoning',{}).get('original_point_matches',[])],'selected_land_use':(x.get('ura_zoning',{}).get('matches') or [{}])[0].get('lu_desc'),'snap_distance_m':x.get('ura_zoning',{}).get('snap_distance_m'),'gpr_source':x.get('gpr_source'),'required_action':'Verify title-lot polygon and current planning controls'} for x in rows]}
@app.get('/zoning/source-status')
def zoning_status():return {'layer':'URA SPACE Master Plan 2025 - approved amendments incorporated','arcgis_layer':'MP25/Updated_Landuse_gaz/MapServer/45','index_ready':URA_DB.exists(),'current_statutory_plan':'Master Plan 2025','retrieved_at':'2026-09-23','current_plan_verification_required':True,'warning':'The zoning layer is current MP2025. Title-lot boundaries, written permission, SDCPs and project-specific development-control requirements still require professional verification.'}
@app.post('/optimise')
def optimise(req:Opt):
 rows=[x for x in read(RESULTS) if x.get('country')=='Singapore' and x.get('actions')]
 actions=[{'asset_id':x['asset_id'],'name':x['name'],'base_noi_m':x.get('economics',{}).get('current_noi_m',0),'actions':x['actions']} for x in rows]
 return optimise_portfolio(actions,req.capital_budget_m,req.max_projects,req.max_development_share,req.cvar_penalty,req.minimum_liquidity_m)
@app.post('/decisions')
def decision(d:Decision):
 now=datetime.now(timezone.utc).isoformat()
 with sqlite3.connect(AUDIT) as c:cur=c.execute('insert into decisions(asset_id,decision,reviewer,rationale,open_conditions,timestamp,model_version) values(?,?,?,?,?,?,?)',(d.asset_id,d.decision,d.reviewer,d.rationale,json.dumps(d.open_conditions),now,'sg-full-model-0.3'))
 return {'decision_id':cur.lastrowid,'timestamp':now}
@app.get('/decisions')
def decisions():
 with sqlite3.connect(AUDIT) as c:c.row_factory=sqlite3.Row;return [dict(x) for x in c.execute('select * from decisions order by id desc limit 100')]
