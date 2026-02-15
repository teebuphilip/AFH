#!/usr/bin/env python3

"""
arr_scoring.py

AFH v1.3 — ARR Feasibility Scoring
---------------------------------
Calculates ARR score from existing dimension scores
and routes ideas to FO intake, HOLD, or EXCLUDE.
"""

import json
from pathlib import Path
from datetime import datetime

# -----------------------------
# CONFIG (LOCKED)
# -----------------------------

INPUT_DIR = Path("data/verdicts/keep")

OUTPUT_DIRS = {
    "FO_INTAKE": Path("data/ready/fo_intake"),
    "HOLD": Path("data/verdicts/hold"),
    "EXCLUDE": Path("data/verdicts/exclude"),
}

ARR_WEIGHTS = {
    "pricing_power": 0.35,
    "user_count_feasibility": 0.30,
    "automation_level": 0.20,
    "market_clarity": 0.10,
    "competition_inverse": 0.05,
}

# Thresholds
FO_THRESHOLD = 90
HOLD_THRESHOLD = 70

# -----------------------------
# HELPERS
# -----------------------------

def compute_arr_score(dim_scores: dict) -> float:
    return round(
        sum(dim_scores[k] * w for k, w in ARR_WEIGHTS.items()),
        2
    )


def determine_arr_verdict(score: float) -> str:
    if score >= FO_THRESHOLD:
        return "FO_INTAKE"
    elif score >= HOLD_THRESHOLD:
        return "HOLD"
    else:
        return "EXCLUDE"


# -----------------------------
# MAIN
# -----------------------------

def main():
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"Input directory not found: {INPUT_DIR}")

    for path in OUTPUT_DIRS.values():
        path.mkdir(parents=True, exist_ok=True)

    files = list(INPUT_DIR.glob("*.json"))
    if not files:
        print("No KEEP files found for ARR scoring.")
        return

    for file_path in files:
        with open(file_path, "r") as f:
            obj = json.load(f)

        if "dimension_scores" not in obj:
            raise ValueError(f"Missing dimension_scores in {file_path.name}")

        arr_score = compute_arr_score(obj["dimension_scores"])
        verdict = determine_arr_verdict(arr_score)

        obj["arr_score"] = arr_score
        obj["arr_verdict"] = verdict
        obj["arr_scored_at"] = datetime.utcnow().isoformat()

        if verdict == "HOLD":
            obj["hold_reason"] = "arr_70_89"

        target_path = OUTPUT_DIRS[verdict] / file_path.name

        with open(target_path, "w") as f:
            json.dump(obj, f, indent=2)

        # State transition
        file_path.unlink()

    print(f"ARR scoring complete. Processed {len(files)} files.")


if __name__ == "__main__":
    main()
