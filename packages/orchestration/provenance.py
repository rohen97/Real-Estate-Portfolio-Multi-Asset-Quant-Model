"""Stable result identity includes model code and public market inputs."""
from hashlib import sha256
from pathlib import Path
import json

MODEL_VERSION = "economic-model-0.9.0"


def model_provenance(root: Path) -> dict:
    digest = sha256()
    for path in sorted((root / "packages").rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    path = root / "data/public/singapore_market_snapshot.json"
    if not path.exists():
        path = root / "data/reference/singapore_market_snapshot.json"
    market_hash = sha256(json.dumps(json.loads(path.read_text(encoding="utf-8")), sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest() if path.exists() else None
    return {"model_version": MODEL_VERSION, "code_sha256": digest.hexdigest(),
            "market_snapshot_sha256": market_hash,
            "warning": "Public indices may be revised; historical index dates do not establish historical availability."}


def result_key(asset: dict, seed: int, provenance: dict) -> str:
    return sha256(json.dumps({"asset": asset, "seed": seed, "provenance": provenance},
                             sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()[:20]
