#!/usr/bin/env python3
"""
AFH — Promote AF Bucket -> Catalog (v1.3/v1.4)

Purpose:
--------
Materialize "accepted build candidates" into a durable catalog,
with stable IDs and an index file for browsing + tooling.

Input:
------
data/af_bucket/*.json

Outputs:
--------
data/catalog/ideas/{catalog_id}.json
data/catalog/index.json
logs/catalog_moves_{YYYY-MM-DD}.jsonl

Notes:
------
- Fully automatic; no CLI args.
- Idempotent: if item already in catalog, it updates metadata/index.
- Conservative: only removes from af_bucket after successful writes.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

DATA = Path("data")
AF_BUCKET = DATA / "af_bucket"

CATALOG = DATA / "catalog"
CATALOG_IDEAS = CATALOG / "ideas"
CATALOG_INDEX = CATALOG / "index.json"

LOGS = Path("logs")
LOGS.mkdir(parents=True, exist_ok=True)

CATALOG_IDEAS.mkdir(parents=True, exist_ok=True)
CATALOG.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"

def stable_id_from_text(text: str) -> str:
    """
    Stable ID from idea_text. If idea_text changes materially, ID changes.
    That is fine for AFH: idea_text should be stable once enriched.
    """
    h = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
    return f"cat_{h[:12]}"

def read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    tmp.replace(path)

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")

def load_index() -> List[Dict[str, Any]]:
    if not CATALOG_INDEX.exists():
        return []
    with open(CATALOG_INDEX, "r") as f:
        return json.load(f)

def save_index(index: List[Dict[str, Any]]) -> None:
    write_json(CATALOG_INDEX, index)

def upsert_index(index: List[Dict[str, Any]], entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_id = {e["catalog_id"]: e for e in index if "catalog_id" in e}
    by_id[entry["catalog_id"]] = entry
    # stable ordering: newest first
    out = list(by_id.values())
    out.sort(key=lambda x: x.get("catalog_added_at", ""), reverse=True)
    return out

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:
    run_date = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = LOGS / f"catalog_moves_{run_date}.jsonl"

    if not AF_BUCKET.exists():
        return

    index = load_index()

    for src in sorted(AF_BUCKET.glob("*.json")):
        idea = read_json(src)

        idea_text = idea.get("idea_text", "").strip()
        if not idea_text:
            # Do not move unknown garbage into catalog
            append_jsonl(log_file, {
                "timestamp": utc_now(),
                "action": "SKIP",
                "reason": "missing_idea_text",
                "source_file": str(src),
            })
            continue

        catalog_id = idea.get("catalog_id") or stable_id_from_text(idea_text)
        idea["catalog_id"] = catalog_id

        # Set/Preserve catalog timestamps
        if "catalog_added_at" not in idea:
            idea["catalog_added_at"] = utc_now()
        idea["catalog_updated_at"] = utc_now()

        # Minimal catalog entry
        entry = {
            "catalog_id": catalog_id,
            "idea_text": idea_text,
            "overlay_score": idea.get("overlay_score"),
            "arr_score": idea.get("arr_score"),
            "verdict": idea.get("verdict"),
            "catalog_added_at": idea.get("catalog_added_at"),
            "catalog_updated_at": idea.get("catalog_updated_at"),
            "source": {
                "from": "af_bucket",
                "file": src.name,
            },
        }

        dst = CATALOG_IDEAS / f"{catalog_id}.json"

        # Write idea + index safely before removing source
        write_json(dst, idea)
        index = upsert_index(index, entry)
        save_index(index)

        append_jsonl(log_file, {
            "timestamp": utc_now(),
            "action": "PROMOTE",
            "catalog_id": catalog_id,
            "source_file": str(src),
            "dest_file": str(dst),
        })

        # Remove from bucket only after successful promotion
        src.unlink()

if __name__ == "__main__":
    main()
