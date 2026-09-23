from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,sqlite3
from packages.domain.contracts import EvidenceRecord
class EvidenceLedger:
 def __init__(self,path:Path):
  self.path=path;path.parent.mkdir(parents=True,exist_ok=True)
  with sqlite3.connect(path) as c:c.execute('create table if not exists evidence(evidence_id text primary key,asset_id text,field text,value_json text,unit text,source text,source_type text,observation_date text,publication_date text,effective_date text,quality real,verification_status text,reviewer text,created_at text)')
 def upsert(self,record:EvidenceRecord):
  d=record.model_dump(mode='json');
  with sqlite3.connect(self.path) as c:c.execute('insert or replace into evidence values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(d['evidence_id'],d['asset_id'],d['field'],json.dumps(d['value']),d['unit'],d['source'],d['source_type'],d['observation_date'],d['publication_date'],d['effective_date'],d['quality'],d['verification_status'],d['reviewer'],datetime.now(timezone.utc).isoformat()))
 def conflicts(self,asset_id:str,field:str):
  with sqlite3.connect(self.path) as c:
   c.row_factory=sqlite3.Row;rows=[dict(x) for x in c.execute('select * from evidence where asset_id=? and field=? and verification_status!='rejected'',(asset_id,field))]
  values={r['value_json'] for r in rows};return {'conflict':len(values)>1,'records':rows}
 def snapshot(self,asset_id:str):
  with sqlite3.connect(self.path) as c:
   c.row_factory=sqlite3.Row;rows=[dict(x) for x in c.execute('select * from evidence where asset_id=? order by field,effective_date',(asset_id,))]
  payload=json.dumps(rows,sort_keys=True,default=str);return {'snapshot_id':hashlib.sha256(payload.encode()).hexdigest()[:20],'asset_id':asset_id,'records':rows}
