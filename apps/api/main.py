from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import json,sqlite3,os
from hashlib import sha256
from functools import lru_cache
from fastapi import FastAPI,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
from packages.optimisation.engine import optimise_portfolio
from packages.optimisation.two_stage import optimise_two_stage
from packages.optimisation.stability import analyse_stability
from packages.orchestration.advanced import analyse_asset
from packages.governance.review import ReviewLedger
from packages.scenarios.engine import scenario_covariance,action_scenario_samples
from packages.zoning.ura import zoning_map_geojson
ROOT=Path(__file__).resolve().parents[2];PORTFOLIO=ROOT/'data/processed/portfolio.json';RESULTS=ROOT/'data/processed/full_model_results.json';URA_DB=ROOT/'data/processed/ura_mp2025.sqlite';AUDIT=ROOT/'data/processed/audit.sqlite';TWIN_DASHBOARD=ROOT/'data/processed/digital_twin_dashboard.json';TWIN_DATA=ROOT/'data/synthetic/semisynthetic_twins.json';REVIEWS=ReviewLedger(ROOT/'data/processed/reviews.sqlite')
app=FastAPI(title='Singapore Portfolio Intelligence API',version='0.9.0');app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()],allow_methods=['GET','POST','OPTIONS'],allow_headers=['Content-Type'])
class CalculationRequest(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False,extra='forbid')
 capital_budget_m:float=Field(default=500,ge=0,le=1000000)
 minimum_liquidity_m:float=Field(default=50,ge=0,le=1000000)
 cvar_penalty:float=Field(default=.3,ge=0,le=10)
class Opt(CalculationRequest):
 max_projects:int=Field(default=20,ge=0,le=500)
 max_development_share:float=Field(default=.45,ge=0,le=1)
class Decision(BaseModel):asset_id:str;decision:str;reviewer:str;rationale:str;open_conditions:list[str]=[]
class TwoStageRequest(CalculationRequest):
 max_development_share:float=Field(default=1,ge=0,le=1)
 max_concurrent_projects:int=Field(default=8,ge=0,le=500)
 minimum_noi_ratio:float=Field(default=.7,ge=0,le=1)
 cvar_penalty:float=Field(default=.25,ge=0,le=10)
class ReviewCreate(BaseModel):asset_id:str;recommendation:str;model_version:str='economic-model-v2';data_snapshot_id:str='pending'
class ReviewSignoff(BaseModel):role:str;reviewer:str;decision:str;notes:str=''
EXAMPLES=ROOT/'data/examples'
DEMO_MODE=os.getenv('PUBLIC_DEMO_MODE','0')=='1'
@lru_cache(maxsize=12)
def _cached_json(path,mtime,size):
 return json.loads(Path(path).read_text(encoding='utf-8'))

def read(path):
 target=path if path.exists() and not DEMO_MODE else {PORTFOLIO:EXAMPLES/'demo_portfolio.json',RESULTS:EXAMPLES/'demo_full_model_results.json'}.get(path)
 if target is None or not target.exists():return []
 stat=target.stat();return _cached_json(str(target),stat.st_mtime_ns,stat.st_size)

def asset_view(row):
 # Risk charts have a dedicated endpoint; list/detail responses need summaries.
 return {**row,'actions':[{k:v for k,v in action.items() if k not in ('scenario_samples_m','scenario_npvs_m')} for action in row.get('actions',[])]} if row.get('actions') else row

def init_db():
 AUDIT.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(AUDIT) as c:c.execute('create table if not exists decisions(id integer primary key,asset_id text,decision text,reviewer text,rationale text,open_conditions text,timestamp text,model_version text)')
init_db()
@app.get('/health')
def health():return {'status':'ok','date':datetime.now(timezone.utc).date().isoformat(),'model_version':'economic-model-0.9.0','portfolio_loaded':bool(read(PORTFOLIO)),'demo_mode':DEMO_MODE or not PORTFOLIO.exists(),'ura_index_loaded':URA_DB.exists() and not DEMO_MODE,'results_loaded':bool(read(RESULTS))}
@app.get('/model/revision')
def model_revision():
 from packages.orchestration.provenance import model_provenance
 return model_provenance(ROOT)
@app.get('/data/status')
def data_status():
 p=read(PORTFOLIO);r=read(RESULTS);return {'portfolio_assets':len(p),'singapore_assets':sum(x.get('country')=='Singapore' for x in p),'geocoded_assets':sum(x.get('latitude') is not None for x in p),'zoned_assets':sum(bool(x.get('ura_zoning',{}).get('matches')) for x in p),'modelled_assets':sum(x.get('model_status')=='provisional_proxy_run' for x in r),'portfolio_source':'Fictional public demonstration' if DEMO_MODE or not PORTFOLIO.exists() else 'User portfolio catalogue','ura_source':'Illustrative zoning fixtures, not statutory evidence' if DEMO_MODE else 'URA cached spatial layer; verify provenance','current_plan':'URA Master Plan 2025','current_plan_verification_required':True}
@app.get('/artifacts/underwriting-template')
def underwriting_template():
 if DEMO_MODE:raise HTTPException(404,'Private underwriting artifacts are unavailable in the public demo')
 path=ROOT/'outputs/far-east-underwriting-20260923/Far_East_Underwriting_Data_Request.xlsx'
 if not path.exists():raise HTTPException(404,'Underwriting template has not been generated')
 return FileResponse(path,filename=path.name,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
@app.get('/artifacts/zoning-exceptions')
def zoning_exception_file():
 if DEMO_MODE:raise HTTPException(404,'Private exception artifacts are unavailable in the public demo')
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
 return action_scenario_samples(row.get('actions',[]),600,20260923+int(sha256(asset_id.encode()).hexdigest()[:8],16)%10000)
@app.get('/visualisations/model-diagnostics')
def visual_model_diagnostics():
 path=ROOT/'data/processed/backtest_report.json';fallback=EXAMPLES/'demo_backtest_report.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/models/market-scenarios')
def market_scenarios():
 path=ROOT/'data/calibration/market_scenarios.json'
 return json.loads(path.read_text()) if path.exists() else {'status':'not_calibrated'}
@app.get('/digital-twins/dashboard')
def digital_twin_dashboard():
 return json.loads(TWIN_DASHBOARD.read_text(encoding='utf-8')) if TWIN_DASHBOARD.exists() else {'status':'not_run','message':'Run scripts/build_digital_twin_dashboard.py'}
@app.get('/digital-twins/assets/{asset_id}')
def digital_twin_asset(asset_id:str):
 if not TWIN_DATA.exists():raise HTTPException(404,'Digital twins have not been generated')
 twins=json.loads(TWIN_DATA.read_text(encoding='utf-8'));twin=next((x for x in twins if x.get('asset_id')==asset_id),None)
 if not twin:raise HTTPException(404,'Digital twin not found')
 dashboard_asset=None
 if TWIN_DASHBOARD.exists():dashboard_asset=next((x for x in json.loads(TWIN_DASHBOARD.read_text(encoding='utf-8')).get('assets',[]) if x.get('asset_id')==asset_id),None)
 return {'twin':twin,'model_dashboard':dashboard_asset}
@app.get('/models/registry')
def model_registry():
 path=ROOT/'models/registry/portfolio-forecasting-latest.json';fallback=EXAMPLES/'demo_model_registry.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_trained'}
@app.get('/models/backtest')
def model_backtest():
 path=ROOT/'data/processed/backtest_report.json';fallback=EXAMPLES/'demo_backtest_report.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/pilot/v2')
def pilot_v2():
 path=ROOT/'data/processed/pilot_model_v2.json';fallback=EXAMPLES/'demo_pilot_model_v2.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/portfolio/v2')
def portfolio_v2():
 path=ROOT/'data/processed/full_portfolio_v2.json';fallback=EXAMPLES/'demo_full_portfolio_v2.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else {'status':'not_run'}
@app.get('/legacy/spec')
def legacy_spec():
 path=ROOT/'data/legacy/legacy_spec.json';return json.loads(path.read_text())
@app.get('/legacy/comparison')
def legacy_comparison():
 path=ROOT/'data/processed/legacy_comparison.json';fallback=EXAMPLES/'demo_legacy_comparison.json';return json.loads((fallback if DEMO_MODE or not path.exists() else path).read_text()) if fallback.exists() or path.exists() else []
@app.get('/market/public')
def public_market():
 from packages.market.public_data import load_snapshot
 return load_snapshot(ROOT)
@app.get('/portfolio')
def portfolio(country:str|None=None,search:str|None=None,limit:int=Query(default=500,ge=1,le=1000)):
 rows=read(RESULTS) or read(PORTFOLIO)
 if country:rows=[x for x in rows if x.get('country','').lower()==country.lower()]
 if search:rows=[x for x in rows if search.lower() in (x.get('name','')+' '+x.get('address','')+' '+' '.join(x.get('segments',[]))).lower()]
 rows=[asset_view(row) for row in rows[:limit]];return {'assets':rows,'summary':{'assets':len(rows),'singapore':sum(x.get('country')=='Singapore' for x in rows),'requires_verification':sum(x.get('verification_required',False) for x in rows),'provisional_recommendations':sum(x.get('recommendation') is not None for x in rows)},'as_of':datetime.now(timezone.utc).date().isoformat()}
@app.get('/assets/{asset_id}')
def detail(asset_id:str):
 row=next((x for x in (read(RESULTS) or read(PORTFOLIO)) if x['asset_id']==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 return asset_view(row)
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
 if row.get('latitude') is None or row.get('longitude') is None:raise HTTPException(422,'Asset has no coordinate')
 radius_m=max(100,min(radius_m,2000));return zoning_map_geojson(URA_DB,row['latitude'],row['longitude'],radius_m)
@app.get('/assets/{asset_id}/advanced-analysis')
def advanced_analysis(asset_id:str):
 row=next((x for x in read(PORTFOLIO) if x.get('asset_id')==asset_id),None)
 if not row:raise HTTPException(404,'Asset not found')
 if row.get('country')!='Singapore' or row.get('latitude') is None:raise HTTPException(422,'Advanced Singapore analysis requires a geocoded Singapore asset')
 return analyse_asset(row)
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
def zoning_status():
 if DEMO_MODE:return {'layer':'Fictional zoning fixtures','index_ready':False,'legal_status':'not_statutory','current_plan_verification_required':True,'warning':'Demonstration polygons are not official planning evidence.'}
 return {'layer':'URA SPACE Master Plan 2025 - approved amendments incorporated','arcgis_layer':'MP25/Updated_Landuse_gaz/MapServer/45','index_ready':URA_DB.exists(),'current_statutory_plan':'Master Plan 2025','retrieved_at':'2026-09-23','current_plan_verification_required':True,'warning':'The zoning layer is current MP2025. Title-lot boundaries, written permission, SDCPs and project-specific development-control requirements still require professional verification.'}
@app.post('/optimise/two-stage')
def optimise_two_stage_api(req:TwoStageRequest):
 rows=[x for x in read(RESULTS) if x.get('country')=='Singapore' and x.get('actions')];actions=[{'asset_id':x['asset_id'],'name':x['name'],'segment':(x.get('segments') or ['Unknown'])[0],'planning_area':(x.get('ura_zoning',{}).get('matches') or [{}])[0].get('planning_area','Unknown'),'base_noi_m':x.get('economics',{}).get('current_noi_m',0),'current_value_m':x.get('economics',{}).get('current_value_m',0),'actions':x['actions']} for x in rows];return optimise_two_stage(actions,total_capital_budget_m=req.capital_budget_m,minimum_liquidity_m=req.minimum_liquidity_m,max_concurrent_projects=req.max_concurrent_projects,minimum_noi_ratio=req.minimum_noi_ratio,cvar_penalty=req.cvar_penalty,max_development_share=req.max_development_share)
@app.post('/optimise/stability')
def optimise_stability_api(req:Opt):
 rows=[x for x in read(RESULTS) if x.get('country')=='Singapore' and x.get('actions')];actions=[{'asset_id':x['asset_id'],'name':x['name'],'base_noi_m':x.get('economics',{}).get('current_noi_m',0),'actions':x['actions']} for x in rows];return analyse_stability(actions,runs=20,total_capital_budget_m=req.capital_budget_m,minimum_liquidity_m=req.minimum_liquidity_m,max_concurrent_projects=req.max_projects,max_development_share=req.max_development_share,cvar_penalty=req.cvar_penalty)
@app.post('/optimise')
def optimise(req:Opt):
 rows=[x for x in read(RESULTS) if x.get('country')=='Singapore' and x.get('actions')]
 actions=[{'asset_id':x['asset_id'],'name':x['name'],'base_noi_m':x.get('economics',{}).get('current_noi_m',0),'actions':x['actions']} for x in rows]
 return optimise_portfolio(actions,req.capital_budget_m,req.max_projects,req.max_development_share,req.cvar_penalty,req.minimum_liquidity_m)
@app.post('/reviews')
def create_review(req:ReviewCreate):return {'case_id':REVIEWS.create_case(req.asset_id,req.recommendation,req.model_version,req.data_snapshot_id)}
@app.post('/reviews/{case_id}/signoff')
def signoff_review(case_id:str,req:ReviewSignoff):return REVIEWS.signoff(case_id,req.role,req.reviewer,req.decision,req.notes)
@app.get('/reviews/{case_id}')
def review_status(case_id:str):return REVIEWS.status(case_id)
@app.post('/decisions')
def decision(d:Decision):
 now=datetime.now(timezone.utc).isoformat()
 with sqlite3.connect(AUDIT) as c:cur=c.execute('insert into decisions(asset_id,decision,reviewer,rationale,open_conditions,timestamp,model_version) values(?,?,?,?,?,?,?)',(d.asset_id,d.decision,d.reviewer,d.rationale,json.dumps(d.open_conditions),now,'sg-full-model-0.3'))
 return {'decision_id':cur.lastrowid,'timestamp':now}
@app.get('/decisions')
def decisions():
 with sqlite3.connect(AUDIT) as c:c.row_factory=sqlite3.Row;return [dict(x) for x in c.execute('select * from decisions order by id desc limit 100')]
