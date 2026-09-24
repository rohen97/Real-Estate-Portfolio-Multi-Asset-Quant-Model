from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import sqlite3,uuid
REQUIRED_ROLES=['valuation','planning_legal','tax_finance','investment_committee']
class ReviewLedger:
 def __init__(self,path:Path):
  self.path=path;path.parent.mkdir(parents=True,exist_ok=True);conn=sqlite3.connect(path)
  try:conn.executescript('create table if not exists review_cases(case_id text primary key,asset_id text,recommendation text,model_version text,data_snapshot_id text,status text,created_at text);create table if not exists signoffs(case_id text,role text,reviewer text,decision text,notes text,timestamp text,primary key(case_id,role));');conn.commit()
  finally:conn.close()
 def create_case(self,asset_id,recommendation,model_version,data_snapshot_id):
  case_id=str(uuid.uuid4());now=datetime.now(timezone.utc).isoformat();conn=sqlite3.connect(self.path)
  try:conn.execute('insert into review_cases values(?,?,?,?,?,?,?)',(case_id,asset_id,recommendation,model_version,data_snapshot_id,'pending',now));conn.commit()
  finally:conn.close()
  return case_id
 def signoff(self,case_id,role,reviewer,decision,notes=''):
  if role not in REQUIRED_ROLES:raise ValueError('Unknown review role')
  conn=sqlite3.connect(self.path)
  try:conn.execute('insert or replace into signoffs values(?,?,?,?,?,?)',(case_id,role,reviewer,decision,notes,datetime.now(timezone.utc).isoformat()));conn.commit()
  finally:conn.close()
  return self.status(case_id)
 def status(self,case_id):
  conn=sqlite3.connect(self.path);conn.row_factory=sqlite3.Row
  try:
   case=conn.execute('select * from review_cases where case_id=?',(case_id,)).fetchone();cursor=conn.execute('select * from signoffs where case_id=?',(case_id,));signoffs=[dict(x) for x in cursor.fetchall()];cursor.close()
  finally:conn.close()
  decisions={x['role']:x['decision'] for x in signoffs};approved=all(decisions.get(role)=='approved' for role in REQUIRED_ROLES);rejected=any(x=='rejected' for x in decisions.values());status='rejected' if rejected else 'approved' if approved else 'pending';return {'case':dict(case) if case else None,'signoffs':signoffs,'required_roles':REQUIRED_ROLES,'missing_roles':[r for r in REQUIRED_ROLES if r not in decisions],'status':status,'can_implement':approved}
