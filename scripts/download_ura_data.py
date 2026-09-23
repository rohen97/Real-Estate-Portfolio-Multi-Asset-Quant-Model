import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.zoning.ura import build_mp2025_index
db=ROOT/'data/processed/ura_mp2025.sqlite'
print(build_mp2025_index(db))
