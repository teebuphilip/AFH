#!/usr/bin/env python3
"""
verdict_routing.py

AFH v1.4 — Verdict Routing (4.2)
--------------------------------
Reads overlay-scored idea files and routes them into
KEEP / HOLD / EXCLUDE directories based on overlay_score.

Supports inputs:
- Directory (default: data/runs/YYYY-MM-DD/scored) containing:
  - *.json   (single object OR array)
  - *.jsonl  (one object per line)
- Or a single file path via CLI.

Filesystem = state machine.
No command-line output paths.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, date, timedelta

# -----------------------------
# CONFIG (LOCKED - Run-specific)
# -----------------------------

run_date = os.getenv("AFH_RUN_DATE") or date.today().isoformat()
RUN_BASE = Path("data") / "runs" / run_date

DEFAULT_INPUT_DIR = RUN_BASE / "scored"

OUTPUT_DIRS = {
    "KEEP": RUN_BASE / "verdicts" / "keep",
    "HOLD": RUN_BASE / "verdicts" / "hold",
    "EXCLUDE": RUN_BASE / "verdicts" / "exclude",
}

# -----------------------------
# Thresholds (CONFIGURABLE)
# -----------------------------
# NOTE: Adjust these thresholds based on your scoring performance
# - Higher thresholds = more selective (fewer KEEP ideas)
# - Lower thresholds = more permissive (more ideas flow through)
#
# 4.2: incremented all thresholds by +15 vs 4.0

OVERLAY_KEEP_THRESHOLD = 65  # 4.0: 50
OVERLAY_HOLD_THRESHOLD = 55  # 4.0: 40

ARR_KEEP_THRESHOLD = 70  # 4.0: 55
ARR_HOLD_THRESHOLD = 60  # 4.0: 45

# Optional: dynamic KEEP cutoff based on rolling history
# If AFH_KEEP_TARGET is set (e.g., 100), KEEP is decided by max(overlay, arr)
# against a cutoff computed from scored files in data/runs/*/scored within
# a rolling window (AFH_KEEP_WINDOW_DAYS).
KEEP_TARGET = int(os.getenv("AFH_KEEP_TARGET", "0") or "0")
KEEP_GLOBAL_CAP = os.getenv("AFH_KEEP_GLOBAL_CAP", "1") == "1"
KEEP_WINDOW_DAYS = int(os.getenv("AFH_KEEP_WINDOW_DAYS", "30") or "30")

# -----------------------------
# HELPERS
# -----------------------------


def determine_verdict(overlay_score: float, arr_score: float) -> str:
    """
    Determine verdict based on overlay and ARR scores.

    Logic:
    - KEEP if overlay >= OVERLAY_KEEP_THRESHOLD OR arr >= ARR_KEEP_THRESHOLD
    - HOLD if mid-range on either score
    - EXCLUDE if below both thresholds
    """
    # Check overlay score
    if overlay_score >= OVERLAY_KEEP_THRESHOLD:
        return "KEEP"
    elif overlay_score >= OVERLAY_HOLD_THRESHOLD:
        verdict_from_overlay = "HOLD"
    else:
        verdict_from_overlay = "EXCLUDE"

    # Check ARR score (can override)
    if arr_score >= ARR_KEEP_THRESHOLD:
        return "KEEP"
    elif arr_score >= ARR_HOLD_THRESHOLD:
        verdict_from_arr = "HOLD"
    else:
        verdict_from_arr = "EXCLUDE"

    # Return the better of the two verdicts
    if verdict_from_overlay == "KEEP" or verdict_from_arr == "KEEP":
        return "KEEP"
    elif verdict_from_overlay == "HOLD" or verdict_from_arr == "HOLD":
        return "HOLD"
    else:
        return "EXCLUDE"

def _parse_run_date(run_dir: Path):
    try:
        return datetime.strptime(run_dir.name, "%Y-%m-%d").date()
    except ValueError:
        return None


def _iter_scored_files(runs_base: Path, window_days: int, as_of: date):
    if not runs_base.exists():
        return
    window_start = as_of - timedelta(days=max(window_days, 1) - 1)
    for run_dir in sorted(runs_base.iterdir()):
        if not run_dir.is_dir():
            continue
        run_dt = _parse_run_date(run_dir)
        if run_dt is None or run_dt < window_start or run_dt > as_of:
            continue
        scored_dir = run_dir / "scored"
        if not scored_dir.exists():
            continue
        for p in scored_dir.glob("*.json"):
            yield p

def compute_keep_cutoff(runs_base: Path, target: int, window_days: int, as_of: date) -> float:
    """
    Compute cutoff score (max(overlay, arr)) so that top N scores are KEEP.
    Returns -inf if not enough scored ideas exist.
    """
    if target <= 0:
        return float("-inf")

    scores = []
    for p in _iter_scored_files(runs_base, window_days, as_of):
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        try:
            overlay = float(obj.get("overlay_score", -1))
            arr = float(obj.get("arr_score", -1))
        except Exception:
            continue
        scores.append(max(overlay, arr))

    if len(scores) < target:
        return float("-inf")

    scores.sort(reverse=True)
    return scores[target - 1]

def enforce_global_keep_cap(runs_base: Path, target: int, window_days: int, as_of: date) -> None:
    if target <= 0:
        return
    keep_files = list(runs_base.glob("*/verdicts/keep/*.json"))
    if not keep_files:
        return

    window_start = as_of - timedelta(days=max(window_days, 1) - 1)
    items = []
    for p in keep_files:
        run_dt = _parse_run_date(p.parents[2])
        if run_dt is None:
            continue
        if run_dt < window_start or run_dt > as_of:
            obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            obj["verdict"] = "HOLD"
            obj["hold_reason"] = "keep_window_expired"
            hold_dir = p.parents[1] / "hold"
            hold_dir.mkdir(parents=True, exist_ok=True)
            hold_path = hold_dir / p.name
            hold_path.write_text(json.dumps(obj, indent=2))
            p.unlink()
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        try:
            overlay = float(obj.get("overlay_score", -1))
            arr = float(obj.get("arr_score", -1))
        except Exception:
            continue
        score = max(overlay, arr)
        items.append((score, p, obj))

    items.sort(key=lambda x: x[0], reverse=True)
    items.sort(key=lambda x: x[0], reverse=True)
    keep_set = set(p for _, p, _ in items[:target])

    for _, p, obj in items[target:]:
        obj["verdict"] = "HOLD"
        obj["hold_reason"] = "keep_cap"
        hold_dir = p.parents[1] / "hold"
        hold_dir.mkdir(parents=True, exist_ok=True)
        hold_path = hold_dir / p.name
        hold_path.write_text(json.dumps(obj, indent=2))
        p.unlink()

def enrich_with_verdict_metadata(obj: dict, verdict: str) -> dict:
    obj["verdict"] = verdict
    obj["verdict_timestamp"] = datetime.utcnow().isoformat()
    obj["verdict_source"] = "overlay_score"
    return obj


def _load_records_from_text(text: str, src_name: str):
    """
    Returns list[dict] from:
      - JSON object
      - JSON array
      - JSONL (one JSON object per line)
    """
    s = text.strip()
    if not s:
        return []

    # JSON array
    if s.startswith("["):
        data = json.loads(s)
        if not isinstance(data, list):
            raise ValueError(f"{src_name}: JSON starts with '[' but is not an array.")
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(f"{src_name}: JSON array contains a non-object element.")
        return data

    # Try single JSON object
    if s.startswith("{"):
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return [obj]
            if isinstance(obj, list):
                # rare but valid
                for item in obj:
                    if not isinstance(item, dict):
                        raise ValueError(f"{src_name}: JSON list contains a non-object element.")
                return obj
        except json.JSONDecodeError:
            # fall through to JSONL
            pass

    # JSONL fallback: parse line-by-line
    records = []
    for i, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{src_name}: invalid JSONL at line {i}: {e}") from e
        if not isinstance(obj, dict):
            raise ValueError(f"{src_name}: JSONL line {i} is not an object.")
        records.append(obj)
    return records


def load_records(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return _load_records_from_text(text, path.name)


def iter_input_files(input_path: Path):
    if input_path.is_file():
        return [input_path]

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    if not input_path.is_dir():
        raise ValueError(f"Input path must be a file or directory: {input_path}")

    files = []
    files.extend(sorted(input_path.glob("*.json")))
    files.extend(sorted(input_path.glob("*.jsonl")))
    return files


def safe_stem_for_outputs(src: Path) -> str:
    # Keep stable, readable output filenames
    return src.name.replace("/", "_").replace("\\", "_")


# -----------------------------
# MAIN
# -----------------------------

def main() -> int:
    # Input can be: argv[1] file/dir, else default directory
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT_DIR

    # Ensure output directories exist
    for p in OUTPUT_DIRS.values():
        p.mkdir(parents=True, exist_ok=True)

    files = iter_input_files(input_path)
    if not files:
        print("No overlay-scored files found. Nothing to do.")
        return 0

    keep_cutoff = None
    if KEEP_TARGET > 0:
        keep_cutoff = compute_keep_cutoff(
            Path("data") / "runs",
            KEEP_TARGET,
            KEEP_WINDOW_DAYS,
            date.fromisoformat(run_date),
        )
        print(f"Dynamic KEEP cutoff (top {KEEP_TARGET} in {KEEP_WINDOW_DAYS}d): {keep_cutoff}")

    processed_files = 0
    written_records = 0

    for file_path in files:
        try:
            records = load_records(file_path)
            if not records:
                # Empty file -> skip but do not delete (signals something went wrong upstream)
                print(f"⚠️  Skipping empty input: {file_path}")
                continue

            base = safe_stem_for_outputs(file_path)

            for idx, obj in enumerate(records, start=1):
                if "overlay_score" not in obj:
                    raise ValueError(f"Missing overlay_score in record #{idx} of {file_path.name}")
                if "arr_score" not in obj:
                    raise ValueError(f"Missing arr_score in record #{idx} of {file_path.name}")

                overlay_score = float(obj["overlay_score"])
                arr_score = float(obj["arr_score"])
                if keep_cutoff is not None and max(overlay_score, arr_score) >= keep_cutoff:
                    verdict = "KEEP"
                else:
                    verdict = determine_verdict(overlay_score, arr_score)
                obj = enrich_with_verdict_metadata(obj, verdict)

                target_dir = OUTPUT_DIRS[verdict]

                # Write one-file-per-record to preserve filesystem state machine
                out_name = f"{base}__{idx:04d}.json"
                target_path = target_dir / out_name

                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(obj, f, ensure_ascii=False, indent=2)

                written_records += 1

            # Keep scored inputs for auditability; re-runs will overwrite outputs.
            processed_files += 1

        except Exception as e:
            # Fail-safe: do not delete input file; print error and continue
            print(f"❌ Failed processing {file_path}: {e}")
            continue

    print(f"Verdict routing complete. Processed {processed_files} files. Wrote {written_records} idea files.")
    if KEEP_TARGET > 0 and KEEP_GLOBAL_CAP:
        enforce_global_keep_cap(
            Path("data") / "runs",
            KEEP_TARGET,
            KEEP_WINDOW_DAYS,
            date.fromisoformat(run_date),
        )
        print(f"Global KEEP cap enforced at {KEEP_TARGET} in {KEEP_WINDOW_DAYS}d window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
