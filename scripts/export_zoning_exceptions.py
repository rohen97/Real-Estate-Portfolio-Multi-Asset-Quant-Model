import json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];rows=json.loads((ROOT/'data/processed/full_model_results.json').read_text());exceptions=[]
for a in rows:
 if a.get('country')=='Singapore' and a.get('zoning_model_status')=='review_required':
  z=a.get('ura_zoning',{});selected=(z.get('matches') or [{}])[0]
  exceptions.append({'asset_id':a['asset_id'],'name':a['name'],'address':a.get('address'),'segments':'; '.join(a.get('segments',[])),'match_method':z.get('match_method'),'original_land_use':','.join(x.get('lu_desc','') for x in z.get('original_point_matches',[])),'selected_land_use':selected.get('lu_desc'),'selected_gpr':selected.get('gpr_text'),'gpr_used':a.get('statutory_gpr_used'),'gpr_source':a.get('gpr_source'),'snap_distance_m':z.get('snap_distance_m'),'planning_area':selected.get('planning_area'),'subzone':selected.get('subzone'),'review_reasons':'; '.join(a.get('proxy_inputs',[])),'required_action':'Obtain title-lot polygon; verify MP2025 zoning, GPR, current use and applicable controls'})
out=ROOT/'data/processed/zoning_exceptions.csv';out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(exceptions[0]) if exceptions else ['asset_id']);w.writeheader();w.writerows(exceptions)
(ROOT/'data/processed/zoning_exceptions.json').write_text(json.dumps(exceptions,indent=2),encoding='utf-8');print(json.dumps({'exceptions':len(exceptions),'csv':str(out)},indent=2))
