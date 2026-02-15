#!/usr/bin/env python3
"""
tag_catalog.py

Tags HOLD and EXCLUDE ideas from ALL runs and builds a public catalog.
"""

import json
from pathlib import Path

# Read from all runs
RUNS_BASE = Path("data/runs")
OUT_FILE = Path("data/catalog/catalog.json")

# -----------------------------
# Tagging dictionaries
# -----------------------------

CATEGORY_KEYWORDS = {
    "marketing": ["marketing", "newsletter", "social", "ads", "campaign"],
    "finance": ["invoice", "expense", "accounting", "payment", "billing"],
    "hr": ["employee", "onboarding", "attendance", "hiring"],
    "operations": ["inventory", "maintenance", "scheduling", "logistics"],
    "productivity": ["notes", "tasks", "email", "calendar", "documents"],
    "education": ["study", "course", "learning", "student"],
    "health": ["health", "medical", "fitness", "workout"],
    "legal": ["legal", "contract", "compliance"],
}

COMPLEXITY_KEYWORDS = {
    "low": ["automation", "script", "batch", "single", "tool"],
    "medium": ["dashboard", "platform", "service"],
    "high": ["real-time", "multi-role", "collaboration", "agent"],
}

MONETIZATION_KEYWORDS = {
    "subscription": ["saas", "subscription", "monthly", "recurring"],
    "freemium": ["freemium", "free", "upgrade"],
    "ads": ["ads", "advertising"],
    "commission": ["commission", "marketplace"],
}


def match_tag(text, rules, default="unknown"):
    text = text.lower()
    for tag, keywords in rules.items():
        for kw in keywords:
            if kw in text:
                return tag
    return default


def tag_idea(obj, verdict):
    text = obj.get("idea_text", "").lower()

    return {
        "idea_text": obj.get("idea_text"),
        "verdict": verdict,
        "tags": {
            "category": match_tag(text, CATEGORY_KEYWORDS),
            "complexity": match_tag(text, COMPLEXITY_KEYWORDS, "medium"),
            "monetization_model": match_tag(text, MONETIZATION_KEYWORDS),
        }
    }


def load_dir(path, verdict):
    items = []
    for file in path.glob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            obj = json.load(f)
        items.append(tag_idea(obj, verdict))
    return items


def main():
    catalog = []

    # Aggregate HOLD and EXCLUDE from all runs
    if RUNS_BASE.exists():
        for run_dir in sorted(RUNS_BASE.iterdir()):
            if not run_dir.is_dir():
                continue

            hold_dir = run_dir / "verdicts" / "hold"
            exclude_dir = run_dir / "verdicts" / "exclude"

            if hold_dir.exists():
                catalog += load_dir(hold_dir, "HOLD")

            if exclude_dir.exists():
                catalog += load_dir(exclude_dir, "EXCLUDE")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog built: {OUT_FILE} ({len(catalog)} ideas from all runs)")


if __name__ == "__main__":
    main()
