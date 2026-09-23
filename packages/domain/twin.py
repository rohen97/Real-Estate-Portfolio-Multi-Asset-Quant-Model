from __future__ import annotations
from pathlib import Path
import json
from packages.domain.contracts import AssetCore,FinancialPeriod,LeaseRecord,PlanningEvent,CapexProject
def load(path:Path):return json.loads(path.read_text()) if path.exists() else []
def build_twins(portfolio:list[dict],data_dir:Path):
 financials=load(data_dir/'financials.json');leases=load(data_dir/'leases.json');planning=load(data_dir/'planning_history.json');capex=load(data_dir/'capex.json');twins=[]
 for asset in portfolio:
  aid=asset['asset_id'];twins.append({'asset':asset,'financials':[x for x in financials if x.get('Asset ID')==aid],'leases':[x for x in leases if x.get('Asset ID')==aid],'planning_history':[x for x in planning if x.get('Asset ID')==aid],'capex_history':[x for x in capex if x.get('Asset ID')==aid],'twin_version':'asset-twin-0.1','synthetic_history':any(x.get('Synthetic') for x in financials if x.get('Asset ID')==aid)})
 return twins
