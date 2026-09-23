import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.zoning.ura import lookup_title_boundary
p=argparse.ArgumentParser();p.add_argument('--boundaries-dir',required=True);p.add_argument('--portfolio',default='data/processed/portfolio.json');a=p.parse_args();portfolio_path=ROOT/a.portfolio;rows=json.loads(portfolio_path.read_text());directory=Path(a.boundaries_dir);resolved=0;errors=[]
for asset in rows:
 path=directory/(asset['asset_id']+'.geojson')
 if not path.exists():continue
 try:
  payload=json.loads(path.read_text());asset['ura_zoning']=lookup_title_boundary(ROOT/'data/processed/ura_mp2025.sqlite',payload);asset['title_boundary_source']=str(path);asset['zoning_exception']=asset['ura_zoning']['spatial_review_required'];resolved+=int(not asset['zoning_exception'])
 except Exception as exc:errors.append({'asset_id':asset['asset_id'],'error':str(exc)})
portfolio_path.write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps({'boundary_files':len(list(directory.glob('*.geojson'))),'resolved':resolved,'errors':errors},indent=2))
