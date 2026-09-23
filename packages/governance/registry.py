from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
def digest(path:Path):
 h=hashlib.sha256();
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def register(registry_dir:Path,name:str,version:str,artifacts:list[Path],metrics:dict,data_source:str,synthetic:bool):
 registry_dir.mkdir(parents=True,exist_ok=True);manifest={'name':name,'version':version,'trained_at':datetime.now(timezone.utc).isoformat(),'data_source':data_source,'synthetic_training':synthetic,'metrics':metrics,'artifacts':[{'path':str(p),'sha256':digest(p)} for p in artifacts if p.exists()]};path=registry_dir/(name+'-'+version+'.json');path.write_text(json.dumps(manifest,indent=2),encoding='utf-8');(registry_dir/(name+'-latest.json')).write_text(json.dumps(manifest,indent=2),encoding='utf-8');return manifest
