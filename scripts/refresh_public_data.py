"""Refresh official market indices, or reproduce the checked-in snapshot offline."""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packages.market.official import DATASETS, build_snapshot, parse_dataset


def refresh(root=ROOT, offline=False, as_of=None):
    as_of = as_of or date.today()
    cache = root / "data/reference/raw"
    cache.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "data/reference/source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    series, sources, errors = [], {}, []
    with httpx.Client(timeout=40, follow_redirects=True) as client:
        for name, spec in DATASETS.items():
            path = cache / (spec["id"] + ".json")
            url = "https://data.gov.sg/api/action/datastore_search?resource_id=" + spec["id"] + "&limit=1000"
            downloaded = False
            if not offline:
                try:
                    for attempt in range(3):
                        response = client.get(url)
                        if response.status_code != 429 or attempt == 2:
                            break
                        time.sleep(min(30, max(2, int(response.headers.get("Retry-After", 5 * (attempt + 1))))))
                    response.raise_for_status()
                    raw = response.content
                    parse_dataset(json.loads(raw), spec, as_of)
                    path.write_bytes(raw)
                    manifest[name] = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "api_url": url}
                    downloaded = True
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    errors.append({"dataset": name, "error": str(exc), "cached": path.exists()})
            if not path.exists():
                continue
            raw = path.read_bytes()
            try:
                parsed = parse_dataset(json.loads(raw), spec, as_of)
            except (ValueError, KeyError) as exc:
                errors.append({"dataset": name, "error": str(exc), "cached": True})
                continue
            series.extend(parsed)
            sources[name] = {**manifest.get(name, {}), "api_url": url,
                             "sha256": sha256(raw).hexdigest(), "mode": "downloaded" if downloaded else "cached",
                             "path": path.relative_to(root).as_posix()}
    if not series:
        raise RuntimeError("No validated public data available; existing snapshots were not overwritten")
    snapshot = build_snapshot(series, as_of, {"sources": sources, "errors": errors, "offline": offline,
                                             "licence": "Singapore Open Data Licence", "available_datasets": len(sources), "expected_datasets": len(DATASETS)})
    if len(sources) < len(DATASETS) or errors:
        snapshot["status"] = "partial_or_cached"
    for relative in ("data/public/singapore_market_snapshot.json", "data/reference/singapore_market_snapshot.json"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(snapshot, indent=2, allow_nan=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat)
    args = parser.parse_args()
    result = refresh(offline=args.offline, as_of=args.as_of)
    print(json.dumps({"status": result["status"], "as_of": result["as_of"], "sources": result["provenance"]["available_datasets"], "errors": result["provenance"]["errors"]}, indent=2))
