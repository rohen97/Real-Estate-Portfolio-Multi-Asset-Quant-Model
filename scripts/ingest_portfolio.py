import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse,json
from packages.data.portfolio import build_portfolio
from packages.zoning.ura import enrich_assets
p=argparse.ArgumentParser();p.add_argument('--workbook',required=True);p.add_argument('--output',default='data/processed/portfolio.json');p.add_argument('--no-geocode',action='store_true');a=p.parse_args();root=ROOT;output=root/a.output;assets=build_portfolio(Path(a.workbook),output,not a.no_geocode,root/'data/overrides/address_overrides.json');db=root/'data/processed/ura_mp2025.sqlite';assets=enrich_assets(assets,db);output.write_text(json.dumps(assets,indent=2),encoding='utf-8');print(json.dumps({'assets':len(assets),'singapore':sum(x['country']=='Singapore' for x in assets),'geocoded':sum(x.get('latitude') is not None for x in assets),'zoned':sum(bool(x.get('ura_zoning',{}).get('matches')) for x in assets)},indent=2))
