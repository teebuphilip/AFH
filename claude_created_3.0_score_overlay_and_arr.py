#!/usr/bin/env python3
"""
AFH — Overlay + ARR Scoring (v1.3 LOCKED)

Purpose:
--------
Deterministically score startup ideas across 5 dimensions
using keyword/pattern heuristics, then compute:

- Overlay Score (economic + operational viability)
- ARR Score (revenue feasibility)

NO LLM calls.
Conservative bias: ambiguity → lower band.

Input:
------
data/normalized/*.json

Output:
-------
data/scored/*.json
(with overlay_score + arr_score added)

Formulas (LOCKED v1.3):
----------------------
Overlay =
  0.30 * pricing_power +
  0.25 * user_count +
  0.25 * automation +
  0.10 * market_clarity +
  0.10 * competition_inverse

ARR =
  0.35 * pricing_power +
  0.30 * user_count +
  0.20 * automation +
  0.10 * market_clarity +
  0.05 * competition_inverse
"""

import json
import shutil
from pathlib import Path
from datetime import date

# ------------------------------------------------------------------
# Paths (AUTO - Run-specific)
# ------------------------------------------------------------------

run_date = date.today().isoformat()
BASE = Path("data") / "runs" / run_date
IN_DIR = BASE / "normalized"
OUT_DIR = BASE / "scored"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Rubrics (v1.3 LOCKED)
# ------------------------------------------------------------------

RUBRICS = {
    "pricing_power": [
        (90, ["subscription", "saas", "per seat", "monthly", "annual", "b2b", "enterprise"]),
        (70, ["freemium", "trial", "upgrade", "pro tier", "premium"]),
        (50, ["ads", "affiliate", "commission", "marketplace"]),
        (30, ["future monetization", "community", "network"]),
        (10, [])  # default floor
    ],
    "user_count": [
        (90, ["teams", "companies", "businesses", "organizations"]),
        (70, ["professionals", "creators", "freelancers"]),
        (50, ["consumers", "individuals"]),
        (30, ["hobbyists", "enthusiasts"]),
        (10, [])
    ],
    "automation": [
        (90, ["automated", "scheduled", "background", "pipeline"]),
        (70, ["assisted", "ai-generated", "recommendation"]),
        (50, ["manual input", "user-driven"]),
        (30, ["fully manual"]),
        (10, [])
    ],
    "market_clarity": [
        (90, ["clear pain", "compliance", "cost reduction", "time savings"]),
        (70, ["optimization", "productivity"]),
        (50, ["insights", "analytics"]),
        (30, ["engagement", "community"]),
        (10, [])
    ],
    "competition_inverse": [
        (90, ["niche", "underserved", "specific vertical"]),
        (70, ["vertical-specific", "regional"]),
        (50, ["general market"]),
        (30, ["crowded", "competitive"]),
        (10, [])
    ]
}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def score_dimension(text: str, rubric) -> int:
    text = text.lower()
    for score, keywords in rubric:
        if any(k in text for k in keywords):
            return score
    return 40  # conservative default

def weighted_sum(scores: dict, weights: dict) -> int:
    return round(sum(scores[k] * w for k, w in weights.items()))

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    for path in IN_DIR.glob("*.json"):
        with open(path) as f:
            idea = json.load(f)

        idea_text = idea.get("idea_text", "")

        scores = {
            "pricing_power": score_dimension(idea_text, RUBRICS["pricing_power"]),
            "user_count": score_dimension(idea_text, RUBRICS["user_count"]),
            "automation": score_dimension(idea_text, RUBRICS["automation"]),
            "market_clarity": score_dimension(idea_text, RUBRICS["market_clarity"]),
            "competition_inverse": score_dimension(idea_text, RUBRICS["competition_inverse"]),
        }

        overlay_weights = {
            "pricing_power": 0.30,
            "user_count": 0.25,
            "automation": 0.25,
            "market_clarity": 0.10,
            "competition_inverse": 0.10
        }

        arr_weights = {
            "pricing_power": 0.35,
            "user_count": 0.30,
            "automation": 0.20,
            "market_clarity": 0.10,
            "competition_inverse": 0.05
        }

        idea["scores"] = scores
        idea["overlay_score"] = weighted_sum(scores, overlay_weights)
        idea["arr_score"] = weighted_sum(scores, arr_weights)

        out_path = OUT_DIR / path.name
        with open(out_path, "w") as f:
            json.dump(idea, f, indent=2)

if __name__ == "__main__":
    main()
