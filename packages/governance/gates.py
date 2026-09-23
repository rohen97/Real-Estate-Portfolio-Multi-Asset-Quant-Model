from __future__ import annotations
from pathlib import Path
import json
class GovernanceError(RuntimeError):pass
def load_manifest(path:Path):return json.loads(path.read_text())
def require_production_model(manifest:dict,allow_synthetic=False):
 if manifest.get('synthetic_training') and not allow_synthetic:raise GovernanceError('Synthetic-pilot model cannot be used for portfolio recommendations without --allow-synthetic-model')
 if not manifest.get('artifacts'):raise GovernanceError('Model manifest contains no artifacts')
 return True
