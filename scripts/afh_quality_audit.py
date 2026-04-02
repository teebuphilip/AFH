#!/usr/bin/env python3
# ============================================================
# afh_quality_audit.py
# Version: 1.0
# Purpose: Monthly 30-minute quality eyeball for AFH catalog.
#          Detects: repetition clusters, generic LLM language,
#          and score distribution drift.
#          Outputs a single terminal report. Green = done.
#          Red = spend 5 min adjusting prompts.
# Dependencies: scikit-learn, numpy (standard AFH stack)
# Usage: python scripts/afh_quality_audit.py
#        python scripts/afh_quality_audit.py --days 60
#        python scripts/afh_quality_audit.py --catalog /path/to/catalog.json
# ============================================================

import json
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ============================================================
# CONFIG — adjust these thresholds as your catalog matures
# ============================================================

# Repetition detection uses a LOOSER threshold than pipeline
# dedup (0.85). We want to catch semantic drift that squeaks
# past the strict dedup gate.
REPETITION_SIMILARITY_THRESHOLD = 0.70

# A cluster is flagged only if 3+ ideas land above the threshold.
# Two similar ideas = fine. Three = pattern problem.
CLUSTER_MIN_SIZE = 3

# Generic LLM language detector. Ideas hitting 2+ of these
# get flagged. This is NOT a blocklist for the pipeline —
# it's a canary for prompt drift.
GENERIC_PHRASES = [
    "revolutionize",
    "revolutionizing",
    "seamless",
    "seamlessly",
    "leverage",
    "leveraging",
    "game-changer",
    "game changer",
    "game-changing",
    "end-to-end",
    "end to end",
    "next-generation",
    "next generation",
    "innovative solution",
    "cutting-edge",
    "cutting edge",
    "disruptive",
    "disrupt the",
    "synergy",
    "paradigm shift",
    "unlock value",
    "unlock the potential",
    "empower",
    "empowering",
    "holistic",
    "robust solution",
    "scalable solution",
    "streamline",
    "streamlining",
    "optimize",
    "optimizing",
    "AI-powered",      # fine as a feature, suspicious as filler
    "powered by AI",
    "solution for",    # "a solution for X" = corporate template
    "platform for",    # same pattern
]

# How many generic phrase hits to trigger a flag
GENERIC_HIT_THRESHOLD = 2

# Score distribution: if the interquartile range of overlay
# scores shrinks below this, scoring has stopped differentiating.
SCORE_IQR_FLOOR = 12.0

# ============================================================
# LOAD CATALOG
# ============================================================

def load_catalog(catalog_path: str, days_back: int) -> list:
    """
    Load ideas from catalog.json, filtered to the last N days.
    Each idea must have at minimum:
        - idea_text (str)
        - overlay_score (float)
        - created_at (ISO-8601 str)
    Optional but used if present:
        - idea_id (str)
        - verdict (str)
    """
    if not os.path.exists(catalog_path):
        print(f"[FATAL] Catalog not found: {catalog_path}")
        sys.exit(1)

    with open(catalog_path, "r") as f:
        catalog = json.load(f)

    # Determine cutoff date
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    filtered = []
    for idea in catalog:
        # Parse created_at — handle with or without timezone
        raw_date = idea.get("created_at", "")
        if not raw_date:
            continue
        try:
            # Try parsing with timezone
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue

        if dt >= cutoff:
            filtered.append(idea)

    return filtered


# ============================================================
# CHECK 1: REPETITION CLUSTER DETECTION
# Uses TF-IDF + cosine similarity at 0.70 threshold.
# Groups ideas into clusters where ALL pairs score >= 0.70.
# Flags clusters of 3+ ideas.
# ============================================================

def detect_repetition_clusters(ideas: list) -> list:
    """
    Returns list of flagged clusters. Each cluster is:
    {
        "cluster_id": int,
        "size": int,
        "similarity_min": float,   # lowest pairwise sim in cluster
        "similarity_max": float,   # highest pairwise sim in cluster
        "ideas": [
            {"idea_text": str, "idea_id": str, "overlay_score": float},
            ...
        ]
    }
    """
    if len(ideas) < CLUSTER_MIN_SIZE:
        return []

    texts = [idea.get("idea_text", "") for idea in ideas]

    # TF-IDF vectorize — same vectorizer approach as pipeline dedup
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        ngram_range=(1, 2)   # unigrams + bigrams catch more drift
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    # Full pairwise similarity matrix
    sim_matrix = cosine_similarity(tfidf_matrix)

    # Build adjacency: two ideas are "connected" if sim >= threshold.
    # Then find connected components. A component is flagged if its
    # AVERAGE pairwise similarity >= threshold AND size >= min.
    # This is more practical than strict cliques for audit use:
    # real prompt drift produces clusters where most pairs are high
    # but one or two pairs dip below due to word substitution.
    n = len(ideas)
    adjacency = defaultdict(set)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i][j] >= REPETITION_SIMILARITY_THRESHOLD:
                adjacency[i].add(j)
                adjacency[j].add(i)

    # BFS to extract connected components
    visited = set()
    clusters = []
    cluster_id = 0

    for node in range(n):
        if node in visited:
            continue
        if not adjacency[node]:
            continue

        # BFS
        component = set()
        queue = [node]
        while queue:
            current = queue.pop(0)
            if current in component:
                continue
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in component:
                    queue.append(neighbor)

        visited.update(component)

        if len(component) < CLUSTER_MIN_SIZE:
            continue

        # Compute ALL pairwise similarities within the component
        component_list = sorted(component)
        all_sims = []
        for i in range(len(component_list)):
            for j in range(i + 1, len(component_list)):
                all_sims.append(
                    sim_matrix[component_list[i]][component_list[j]]
                )

        avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0

        # Flag if average pairwise sim >= threshold
        if avg_sim < REPETITION_SIMILARITY_THRESHOLD:
            continue

        clique = component_list
        clique_sims = all_sims

        cluster_id += 1
        clusters.append({
            "cluster_id": cluster_id,
            "size": len(clique),
            "similarity_min": round(float(min(clique_sims)), 3),
            "similarity_max": round(float(max(clique_sims)), 3),
            "ideas": [
                {
                    "idea_text": ideas[idx].get("idea_text", ""),
                    "idea_id": ideas[idx].get("idea_id", "unknown"),
                    "overlay_score": ideas[idx].get("overlay_score", 0),
                }
                for idx in clique
            ]
        })

    return clusters


# ============================================================
# CHECK 2: GENERIC LLM LANGUAGE DETECTION
# Scans each idea for corporate/LLM filler phrases.
# Flags ideas hitting GENERIC_HIT_THRESHOLD or more.
# ============================================================

def detect_generic_language(ideas: list) -> list:
    """
    Returns list of flagged ideas:
    {
        "idea_text": str,
        "idea_id": str,
        "overlay_score": float,
        "hits": [str, ...],       # which phrases matched
        "hit_count": int
    }
    """
    flagged = []

    for idea in ideas:
        text = idea.get("idea_text", "").lower()
        hits = []

        for phrase in GENERIC_PHRASES:
            if phrase.lower() in text:
                hits.append(phrase)

        if len(hits) >= GENERIC_HIT_THRESHOLD:
            flagged.append({
                "idea_text": idea.get("idea_text", ""),
                "idea_id": idea.get("idea_id", "unknown"),
                "overlay_score": idea.get("overlay_score", 0),
                "hits": hits,
                "hit_count": len(hits),
            })

    # Sort by hit count descending — worst offenders first
    flagged.sort(key=lambda x: x["hit_count"], reverse=True)
    return flagged


# ============================================================
# CHECK 3: SCORE DISTRIBUTION HEALTH
# Histograms overlay scores. Flags if distribution is
# compressing (IQR shrinking) or clustering in one band.
# ============================================================

def analyze_score_distribution(ideas: list) -> dict:
    """
    Returns distribution analysis:
    {
        "count": int,
        "mean": float,
        "median": float,
        "std": float,
        "min": float,
        "max": float,
        "p25": float,      # 25th percentile
        "p75": float,      # 75th percentile
        "iqr": float,      # interquartile range
        "iqr_flag": bool,  # True if IQR < SCORE_IQR_FLOOR
        "histogram": {     # bucket counts
            "0-29": int,
            "30-49": int,
            "50-64": int,   # EXCLUDE boundary
            "65-80": int,   # HOLD band
            "81-100": int,  # KEEP band
        },
        "dominant_band": str,  # band with most ideas
        "dominant_pct": float, # % of ideas in dominant band
    }
    """
    scores = [idea.get("overlay_score", 0) for idea in ideas]

    if not scores:
        return {"count": 0, "iqr_flag": False}

    scores_arr = np.array(scores, dtype=float)

    p25 = float(np.percentile(scores_arr, 25))
    p75 = float(np.percentile(scores_arr, 75))
    iqr = p75 - p25

    # Histogram buckets aligned with AFH verdict thresholds
    buckets = {
        "0-29":   int(np.sum((scores_arr >= 0) & (scores_arr <= 29))),
        "30-49":  int(np.sum((scores_arr >= 30) & (scores_arr <= 49))),
        "50-64":  int(np.sum((scores_arr >= 50) & (scores_arr <= 64))),
        "65-80":  int(np.sum((scores_arr >= 65) & (scores_arr <= 80))),
        "81-100": int(np.sum((scores_arr >= 81) & (scores_arr <= 100))),
    }

    # Find dominant band
    dominant_band = max(buckets, key=buckets.get)
    total = len(scores)
    dominant_pct = round((buckets[dominant_band] / total) * 100, 1) if total else 0

    return {
        "count": total,
        "mean": round(float(np.mean(scores_arr)), 1),
        "median": round(float(np.median(scores_arr)), 1),
        "std": round(float(np.std(scores_arr)), 1),
        "min": round(float(np.min(scores_arr)), 1),
        "max": round(float(np.max(scores_arr)), 1),
        "p25": round(p25, 1),
        "p75": round(p75, 1),
        "iqr": round(iqr, 1),
        "iqr_flag": iqr < SCORE_IQR_FLOOR,
        "histogram": buckets,
        "dominant_band": dominant_band,
        "dominant_pct": dominant_pct,
    }


# ============================================================
# TERMINAL REPORT RENDERER
# Single pass read. Green/Yellow/Red status indicators.
# ============================================================

# ANSI color codes — work in Terminal.app on macOS
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def status_color(flag: bool, severity: str = "red") -> str:
    """Return GREEN if clean, RED/YELLOW if flagged."""
    if not flag:
        return GREEN
    return RED if severity == "red" else YELLOW


def render_report(ideas: list, clusters: list, generic_flags: list,
                  score_dist: dict, days_back: int) -> str:
    """
    Render the full audit report as a terminal string.
    """
    lines = []
    sep = "=" * 62

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------
    lines.append(f"\n{BOLD}{sep}")
    lines.append("  AFH QUALITY AUDIT REPORT")
    lines.append(f"  {sep}{RESET}")
    lines.append(f"{DIM}  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  Window:    last {days_back} days")
    lines.append(f"  Ideas:     {len(ideas)}{RESET}")
    lines.append(sep)

    # --------------------------------------------------------
    # OVERALL STATUS — the one thing you read first
    # --------------------------------------------------------
    all_clean = (
        len(clusters) == 0
        and len(generic_flags) == 0
        and not score_dist.get("iqr_flag", False)
    )

    if all_clean:
        lines.append(f"\n{GREEN}{BOLD}  STATUS: ALL GREEN — catalog healthy.{RESET}")
        lines.append(f"{DIM}  Nothing to action. Done for this month.{RESET}\n")
    else:
        lines.append(f"\n{RED}{BOLD}  STATUS: REVIEW NEEDED{RESET}")
        lines.append(f"{DIM}  Flagged items below. Adjust generation prompts as needed.{RESET}\n")

    lines.append(sep)

    # --------------------------------------------------------
    # CHECK 1: REPETITION CLUSTERS
    # --------------------------------------------------------
    cluster_color = status_color(len(clusters) > 0)
    lines.append(f"\n{BOLD}  CHECK 1: REPETITION CLUSTERS{RESET}")
    lines.append(f"  Threshold: {REPETITION_SIMILARITY_THRESHOLD} | Min cluster size: {CLUSTER_MIN_SIZE}")
    lines.append(f"  {cluster_color}Flagged clusters: {len(clusters)}{RESET}\n")

    if not clusters:
        lines.append(f"{DIM}  No repetition drift detected.{RESET}")
    else:
        for cluster in clusters:
            lines.append(f"  {RED}{BOLD}--- Cluster #{cluster['cluster_id']} "
                         f"({cluster['size']} ideas, "
                         f"sim {cluster['similarity_min']}-{cluster['similarity_max']}) ---{RESET}")
            for i, idea in enumerate(cluster["ideas"]):
                # Truncate long idea text for readability
                text_preview = idea["idea_text"][:80]
                if len(idea["idea_text"]) > 80:
                    text_preview += "..."
                lines.append(f"    {i+1}. [{idea['idea_id']}] "
                             f"(score: {idea['overlay_score']}) "
                             f"{text_preview}")
            lines.append("")

    lines.append(sep)

    # --------------------------------------------------------
    # CHECK 2: GENERIC LLM LANGUAGE
    # --------------------------------------------------------
    generic_color = status_color(len(generic_flags) > 0)
    lines.append(f"\n{BOLD}  CHECK 2: GENERIC LLM LANGUAGE{RESET}")
    lines.append(f"  Hit threshold: {GENERIC_HIT_THRESHOLD}+ phrases")
    lines.append(f"  {generic_color}Flagged ideas: {len(generic_flags)}{RESET}\n")

    if not generic_flags:
        lines.append(f"{DIM}  No generic language drift detected.{RESET}")
    else:
        for flag in generic_flags:
            text_preview = flag["idea_text"][:80]
            if len(flag["idea_text"]) > 80:
                text_preview += "..."
            lines.append(f"  {YELLOW}{BOLD}[{flag['idea_id']}] {RESET}"
                         f"({flag['hit_count']} hits) "
                         f"{text_preview}")
            lines.append(f"    {DIM}Matched: {', '.join(flag['hits'])}{RESET}")

    lines.append(f"\n{sep}")

    # --------------------------------------------------------
    # CHECK 3: SCORE DISTRIBUTION
    # --------------------------------------------------------
    if score_dist.get("count", 0) == 0:
        lines.append(f"\n{BOLD}  CHECK 3: SCORE DISTRIBUTION{RESET}")
        lines.append(f"  {YELLOW}No scores to analyze.{RESET}")
    else:
        iqr_color = status_color(score_dist["iqr_flag"], severity="yellow")
        lines.append(f"\n{BOLD}  CHECK 3: SCORE DISTRIBUTION{RESET}")
        lines.append(f"  IQR floor: {SCORE_IQR_FLOOR}")
        lines.append(f"  {iqr_color}IQR: {score_dist['iqr']} "
                     f"{'[COMPRESSING — scoring may not be differentiating]' if score_dist['iqr_flag'] else '[healthy spread]'}"
                     f"{RESET}\n")

        # Stats row
        lines.append(f"  {DIM}mean={score_dist['mean']}  "
                     f"median={score_dist['median']}  "
                     f"std={score_dist['std']}  "
                     f"range=[{score_dist['min']}, {score_dist['max']}]"
                     f"{RESET}")

        # Histogram — ASCII bar chart aligned to verdict bands
        lines.append(f"\n  {'Band':<10} {'Count':>6}  {'Bar'}")
        lines.append(f"  {'-'*10} {'-'*6}  {'-'*30}")

        hist = score_dist["histogram"]
        max_count = max(hist.values()) if hist else 1
        band_labels = {
            "0-29":   "EXCLUDE",
            "30-49":  "EXCLUDE",
            "50-64":  "EXCLUDE",
            "65-80":  "HOLD",
            "81-100": "KEEP",
        }
        for band, count in hist.items():
            bar_len = int((count / max_count) * 28) if max_count > 0 else 0
            # Color the bar by verdict
            verdict = band_labels[band]
            if verdict == "KEEP":
                bar_color = GREEN
            elif verdict == "HOLD":
                bar_color = YELLOW
            else:
                bar_color = DIM
            bar = f"{bar_color}{'█' * bar_len}{RESET}"
            lines.append(f"  {band:<10} {count:>6}  {bar} {DIM}[{verdict}]{RESET}")

        # Flag if one band dominates
        if score_dist["dominant_pct"] > 60:
            lines.append(f"\n  {YELLOW}Warning: {score_dist['dominant_pct']}% of ideas "
                         f"cluster in band {score_dist['dominant_band']}. "
                         f"Scoring may lack differentiation.{RESET}")

    lines.append(f"\n{sep}")

    # --------------------------------------------------------
    # FOOTER — actionable next steps if anything is red
    # --------------------------------------------------------
    if not all_clean:
        lines.append(f"\n{BOLD}  SUGGESTED ACTIONS:{RESET}")
        if clusters:
            lines.append(f"  {RED}• Repetition:{RESET} Review cluster ideas above. "
                         f"Adjust generation prompts to avoid")
            lines.append("    repeating themes in these categories. "
                         "Consider tightening dedup threshold if")
            lines.append("    clusters persist next month.")
        if generic_flags:
            lines.append(f"  {YELLOW}• Generic language:{RESET} "
                         f"Add negative constraints to generation prompts.")
            lines.append("    Example: 'Avoid corporate buzzwords like "
                         "revolutionize, seamless, leverage.'")
        if score_dist.get("iqr_flag"):
            lines.append(f"  {YELLOW}• Score compression:{RESET} "
                         f"Review scoring rubrics for dimensions that")
            lines.append("    always land in the same band. May need "
                         "keyword list expansion.")
    else:
        lines.append(f"\n{DIM}  No actions needed. See you next month.{RESET}")

    lines.append(f"\n{sep}\n")

    return "\n".join(lines)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AFH monthly quality audit — 30 min/month eyeball"
    )
    parser.add_argument(
        "--catalog",
        default="data/catalog/catalog.json",
        help="Path to catalog.json (default: data/catalog/catalog.json)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Look-back window in days (default: 30)"
    )
    args = parser.parse_args()

    # Load and filter catalog
    ideas = load_catalog(args.catalog, args.days)

    if not ideas:
        print(f"\n[INFO] No ideas found in last {args.days} days. "
              "Nothing to audit.\n")
        sys.exit(0)

    # Run all three checks
    clusters      = detect_repetition_clusters(ideas)
    generic_flags = detect_generic_language(ideas)
    score_dist    = analyze_score_distribution(ideas)

    # Render and print
    report = render_report(ideas, clusters, generic_flags, score_dist, args.days)
    print(report)


if __name__ == "__main__":
    main()
