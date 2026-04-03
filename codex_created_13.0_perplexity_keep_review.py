#!/usr/bin/env python3
"""
AFH v1.4 — Perplexity Keep Review

- Every KEEP is scored via Perplexity competitive intel.
- If score >= 65: mark as build_keep.
- If score < 65: queue for monthly rerun.
- If score < 65 for 3 monthly runs: demote to HOLD.

State is tracked in data/perplexity/keep_status.json keyed by idea_hash.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = os.environ.get("PERPLEXITY_MODEL", "sonar-pro")

SCORE_THRESHOLD = int(os.environ.get("PERPLEXITY_KEEP_THRESHOLD", "65"))
MAX_FAILS = int(os.environ.get("PERPLEXITY_MAX_FAILS", "3"))
RETRY_DAYS = int(os.environ.get("PERPLEXITY_RETRY_DAYS", "30"))

PROMPT_TEMPLATE = """\
Give a structured assessment of the following micro-SaaS idea. Be brutally honest — not encouraging.
Respond ONLY in valid JSON with exactly these keys:

- "idea_title": short name you derive from the idea
- "competitors": array of exactly 3 objects, each with "name" and "pricing"
- "market_gap_real": boolean — true if a genuine underserved gap exists
- "market_gap_notes": 1-2 sentence honest explanation
- "prob_500mrr_90days": integer 0-100 — realistic probability of reaching $500 MRR within 90 days
- "prob_rationale": 1 sentence explaining the number
- "biggest_kill_risk": 1 sentence on the single biggest risk that could kill it

Return ONLY the JSON object. No preamble, no markdown fences.

Idea:
{idea_text}
"""


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _extract_json(raw: str) -> Dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return json.loads(cleaned)


def _score_item(item: Dict[str, Any]) -> int:
    prob = int(item.get("prob_500mrr_90days", 0) or 0)
    gap = 30 if item.get("market_gap_real", False) else 0
    competitors = item.get("competitors", [])
    named = sum(
        1 for c in competitors
        if str(c.get("name", "")).strip().lower() not in ("none", "n/a", "")
    )
    if named <= 1:
        comp_score = 20
    elif named == 2:
        comp_score = 10
    else:
        comp_score = 0
    return round((prob * 0.5) + gap + comp_score)


def _call_perplexity(idea_text: str) -> Dict[str, Any]:
    if not PERPLEXITY_API_KEY:
        raise RuntimeError("PERPLEXITY_API_KEY not set")
    prompt = PROMPT_TEMPLATE.format(idea_text=idea_text)
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a ruthless SaaS market analyst. You respond only in valid JSON. No markdown.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    resp = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    return _extract_json(raw)


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path)


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    _write_json(path, state)


def _should_run(last_run: str | None, today: date) -> bool:
    if not last_run:
        return True
    try:
        last = datetime.fromisoformat(last_run).date()
    except ValueError:
        return True
    return (today - last) >= timedelta(days=RETRY_DAYS)


def _update_keep_file(path: Path, updates: Dict[str, Any]) -> None:
    obj = _load_json(path)
    obj.update(updates)
    _write_json(path, obj)


def _demote_keep(path: Path, reason: str) -> None:
    obj = _load_json(path)
    obj["verdict"] = "HOLD"
    obj["hold_reason"] = reason
    hold_dir = path.parents[1] / "hold"
    hold_dir.mkdir(parents=True, exist_ok=True)
    hold_path = hold_dir / path.name
    _write_json(hold_path, obj)
    path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Perplexity review for KEEP ideas")
    parser.add_argument("--run-date", default=None, help="Run date YYYY-MM-DD (default: today or AFH_RUN_DATE)")
    args = parser.parse_args()

    run_date = args.run_date or os.getenv("AFH_RUN_DATE") or date.today().isoformat()
    run_dir = Path("data") / "runs" / run_date
    keep_dir = run_dir / "verdicts" / "keep"
    keep_files = sorted(keep_dir.glob("*.json")) if keep_dir.exists() else []

    if not keep_files:
        print("No KEEP ideas to review.")
        return 0

    state_path = Path("data") / "perplexity" / "keep_status.json"
    state = _load_state(state_path)
    today = date.fromisoformat(run_date)

    processed = 0
    skipped = 0
    demoted = 0

    for path in keep_files:
        idea = _load_json(path)
        idea_text = (idea.get("idea_text") or "").strip()
        if not idea_text:
            skipped += 1
            continue
        idea_hash = _hash_text(idea_text)
        entry = state.get(idea_hash, {})

        if not _should_run(entry.get("last_run"), today):
            skipped += 1
            continue

        try:
            result = _call_perplexity(idea_text)
        except Exception as exc:
            print(f"Perplexity failed for {path.name}: {exc}")
            skipped += 1
            continue

        score = _score_item(result)
        status = "build_keep" if score >= SCORE_THRESHOLD else "queued"
        fail_count = int(entry.get("fail_count", 0))
        if score < SCORE_THRESHOLD:
            fail_count += 1

        entry.update({
            "idea_hash": idea_hash,
            "last_run": today.isoformat(),
            "score": score,
            "status": status,
            "fail_count": fail_count,
            "last_result": result,
        })
        state[idea_hash] = entry

        _update_keep_file(path, {
            "perplexity_score": score,
            "perplexity_status": status,
            "perplexity_last_run": today.isoformat(),
            "perplexity_fail_count": fail_count,
        })

        if status != "build_keep" and fail_count >= MAX_FAILS:
            _demote_keep(path, "perplexity_failed_3_months")
            entry["status"] = "demoted"
            state[idea_hash] = entry
            demoted += 1

        processed += 1

    _save_state(state_path, state)
    print(f"Perplexity review complete. processed={processed} skipped={skipped} demoted={demoted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
