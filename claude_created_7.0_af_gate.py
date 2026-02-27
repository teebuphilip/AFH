#!/usr/bin/env python3
"""
AFH — AF Build Readiness Gate (v1.3 LOCKED)

Purpose:
--------
Validate FO-enriched ideas before promotion to AF bucket.

Input:
------
data/fo_intake/*.json

Output:
-------
PASS -> data/af_bucket/*.json
FAIL -> data/runs/YYYY-MM-DD/verdicts/hold/*.json
"""

import json
import re
from pathlib import Path
from datetime import datetime, date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE = Path("data")

run_date = date.today().isoformat()
RUN_BASE = BASE / "runs" / run_date

FO_DIR = BASE / "fo_intake"
AF_DIR = BASE / "af_bucket"
HOLD_DIR = RUN_BASE / "verdicts" / "hold"

AF_DIR.mkdir(parents=True, exist_ok=True)
HOLD_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Keyword Sets
# ------------------------------------------------------------------

LEGAL_BLOCK = [
    "gambling", "casino", "betting",
    "adult", "porn",
    "medical advice", "diagnosis", "treatment",
    "financial advice", "investment advice"
]

DEPENDENCY_BLOCK = [
    "partnership", "approval", "invite-only",
    "private beta", "exclusive access",
    "requires agreement", "nda"
]

AUTONOMY_BLOCK = [
    "oauth", "login", "sign up", "authentication",
    "manual review", "human approval", "onboarding"
]

BUILD_COMPLEXITY_BLOCK = [
    "real-time", "dashboard", "multi-role",
    "permissions", "admin panel",
    "notifications system", "collaboration"
]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def contains_any(text: str, keywords) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)

def gate_fail(reason: str):
    return False, reason

def gate_pass():
    return True, None

# ------------------------------------------------------------------
# Gate Checks
# ------------------------------------------------------------------

def check_legal(idea):
    text = idea["idea_text"]
    if contains_any(text, LEGAL_BLOCK):
        return gate_fail("legal_policy_risk")
    return gate_pass()

def check_dependencies(idea):
    q8 = idea["intake_answers"]["Q8"]
    if contains_any(q8, DEPENDENCY_BLOCK):
        return gate_fail("non_public_dependency")
    return gate_pass()

def check_build_surface(idea):
    q2 = idea["intake_answers"]["Q2"]
    q4 = idea["intake_answers"]["Q4"]
    q9 = idea["intake_answers"]["Q9"]

    combined = f"{q2} {q4} {q9}"
    if contains_any(combined, BUILD_COMPLEXITY_BLOCK):
        return gate_fail("excessive_build_surface")
    return gate_pass()

def check_cost_ceiling(idea):
    # Conservative heuristic:
    # batch + API + no UI usually < $20
    q4 = idea["intake_answers"]["Q4"]
    q8 = idea["intake_answers"]["Q8"]

    risky = ["streaming", "real-time", "gpu", "video", "audio"]
    if contains_any(q4 + q8, risky):
        return gate_fail("cost_ceiling_risk")
    return gate_pass()

def check_autonomy(idea):
    q6 = idea["intake_answers"]["Q6"]
    if contains_any(q6, AUTONOMY_BLOCK):
        return gate_fail("non_autonomous")
    return gate_pass()

def check_internal_conflict(idea, af_texts):
    if not af_texts:
        return gate_pass()

    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = af_texts + [idea["idea_text"]]
    vectors = vectorizer.fit_transform(corpus)

    sims = cosine_similarity(vectors[-1], vectors[:-1])[0]
    if max(sims) >= 0.85:
        return gate_fail("internal_conflict")
    return gate_pass()

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    af_existing = []
    for f in AF_DIR.glob("*.json"):
        with open(f) as fh:
            af_existing.append(json.load(fh)["idea_text"])

    for path in FO_DIR.glob("*.json"):
        with open(path) as f:
            idea = json.load(f)

        checks = [
            check_legal,
            check_dependencies,
            check_build_surface,
            check_cost_ceiling,
            check_autonomy,
        ]

        failed_reason = None
        for chk in checks:
            ok, reason = chk(idea)
            if not ok:
                failed_reason = reason
                break

        if not failed_reason:
            ok, reason = check_internal_conflict(idea, af_existing)
            if not ok:
                failed_reason = reason

        if failed_reason:
            idea["verdict"] = "HOLD"
            idea["hold_reason"] = "gate_failure"
            idea["gate_failed_check"] = failed_reason
            idea["verdict_timestamp"] = datetime.utcnow().isoformat() + "Z"

            out = HOLD_DIR / path.name
        else:
            idea["verdict"] = "AF_READY"
            idea["af_ready_timestamp"] = datetime.utcnow().isoformat() + "Z"

            out = AF_DIR / path.name
            af_existing.append(idea["idea_text"])

        with open(out, "w") as f:
            json.dump(idea, f, indent=2)

        path.unlink()

if __name__ == "__main__":
    main()
