from __future__ import annotations
from pathlib import Path
import json
def load_snapshot(root:Path)->dict:
 path=root/'data/public/singapore_market_snapshot.json'
 return json.loads(path.read_text()) if path.exists() else {'status':'not_refreshed'}
def context_for_asset(asset:dict,snapshot:dict)->dict:
 segments=' '.join(asset.get('segments',[])).lower()
 if 'industrial' in segments or 'factory' in segments or 'warehouse' in segments:key='industrial'
 elif 'mall' in segments or 'retail' in segments:key='retail'
 elif 'commercial' in segments or 'office' in segments or 'medical' in segments:key='office'
 elif 'residential' in segments:key='private_residential'
 elif 'hotel' in segments:key='hospitality'
 else:key='general'
 return {'market_segment':key,'indicators':snapshot.get('market_indicators',{}).get(key,{}),'as_of':snapshot.get('as_of'),'warning':'Public market indicators are contextual evidence and are not asset-level forecasts.'}
