from __future__ import annotations
from pathlib import Path
import json
from datetime import date
from packages.market.official import build_snapshot
def load_snapshot(root:Path)->dict:
 path=root/'data/public/singapore_market_snapshot.json'
 if not path.exists():path=root/'data/reference/singapore_market_snapshot.json'
 if not path.exists():return {'status':'not_refreshed'}
 snapshot=json.loads(path.read_text(encoding='utf-8'))
 if snapshot.get('history'):
  updated=build_snapshot(snapshot['history'],date.today(),snapshot.get('provenance',{}))
  if snapshot.get('status')=='partial_or_cached':updated['status']='partial_or_cached'
  return updated
 return snapshot
def context_for_asset(asset:dict,snapshot:dict)->dict:
 segments=' '.join(asset.get('segments',[])).lower()
 if 'mixed' in segments:key='general'
 elif 'industrial' in segments or 'factory' in segments or 'warehouse' in segments or 'logistics' in segments:key='industrial'
 elif 'mall' in segments or 'retail' in segments:key='retail'
 elif 'commercial' in segments or 'office' in segments or 'medical' in segments:key='office'
 elif 'residential' in segments:key='private_residential'
 elif 'hotel' in segments or 'hospitality' in segments:key='hospitality'
 else:key='general'
 return {'market_segment':key,'indicators':snapshot.get('market_indicators',{}).get(key,{}),'as_of':snapshot.get('as_of'),'warning':'Public market indicators are contextual evidence and are not asset-level forecasts.'}
