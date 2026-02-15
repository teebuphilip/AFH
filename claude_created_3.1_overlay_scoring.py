#!/usr/bin/env python3
import sys
import json
import re

# ------------------------------------------------------------
# Simple keyword-based scoring helpers
# (lightweight deterministic heuristics)
# ------------------------------------------------------------

def score_pricing_power(text: str) -> int:
    text = text.lower()
    if any(k in text for k in ["b2b", "enterprise", "subscription", "saas"]):
        return 90
    if any(k in text for k in ["freemium", "pro tier", "trial"]):
        return 75
    if any(k in text for k in ["ads", "affiliate", "commission"]):
        return 60
    if any(k in text for k in ["community", "data", "future monetization"]):
        return 40
    return 30


def score_user_feasibility(text: str) -> int:
    text = text.lower()
    if any(k in text for k in ["developers", "marketers", "small businesses"]):
        return 90
    if any(k in text for k in ["students", "freelancers", "creators"]):
        return 75
    if any(k in text for k in ["consumers", "general users"]):
        return 60
    return 40


def score_automation_level(text: str) -> int:
    text = text.lower()
    if any(k in text for k in ["automated", "background", "batch", "pipeline"]):
        return 90
    if any(k in text for k in ["dashboard", "insights", "report"]):
        return 70
    if any(k in text for k in ["manual", "workflow", "tool"]):
        return 50
    return 40


def score_market_clarity(text: str) -> int:
    text = text.lower()
    if any(k in text for k in ["invoice", "email", "analytics", "crm"]):
        return 85
    if any(k in text for k in ["productivity", "tracking", "management"]):
        return 70
    if any(k in text for k in ["platform", "community", "network"]):
        return 55
    return 45


def score_competition_inverse(text: str) -> int:
    text = text.lower()
    if any(k in text for k in ["niche", "specific", "industry"]):
        return 85
    if any(k in text for k in ["tool", "automation", "service"]):
        return 65
    if any(k in text for k in ["platform", "social", "general"]):
        return 45
    return 55


# ------------------------------------------------------------
# Overlay score computation
# ------------------------------------------------------------

def compute_overlay_score(text: str):
    components = {
        "pricing_power": score_pricing_power(text),
        "user_feasibility": score_user_feasibility(text),
        "automation": score_automation_level(text),
        "market_clarity": score_market_clarity(text),
        "competition_inverse": score_competition_inverse(text),
    }

    overlay_score = round(
        0.30 * components["pricing_power"] +
        0.25 * components["user_feasibility"] +
        0.25 * components["automation"] +
        0.10 * components["market_clarity"] +
        0.10 * components["competition_inverse"],
        2
    )

    return overlay_score, components


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python overlay_scoring.py <input.jsonl>", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]

    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            idea = json.loads(line)
            text = idea["idea_text"]

            overlay_score, components = compute_overlay_score(text)

            idea["overlay_score"] = overlay_score
            idea["overlay_components"] = components

            print(json.dumps(idea, ensure_ascii=False))


if __name__ == "__main__":
    main()
