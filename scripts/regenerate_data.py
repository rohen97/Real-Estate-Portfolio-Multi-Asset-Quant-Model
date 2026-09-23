import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from packages.domain.model import assets,MASTER_SEED
p=ROOT/'data'/'synthetic';p.mkdir(parents=True,exist_ok=True);x=assets(MASTER_SEED);(p/'assets.json').write_text(json.dumps(x,indent=2));print(p/'assets.json')
