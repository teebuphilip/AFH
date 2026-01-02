#!/usr/bin/env python3
import sys
import json
import re
import hashlib
from datetime import date
from pathlib import Path

# ============================================================
# AFH — Normalize & Deduplicate
# ============================================================

STOPWORDS = {
    "the","a","an","to","for","of","and","or","with","by","on","in","at"
}

HISTORY_FILE = Path("data/normalized/history.txt")
OUTPUT_DIR = Path("data/normalized")
TODAY = date.today().isoformat()

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def normalize_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".") + "."
    return text

def tokenize(text: str):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in STOPWORDS)

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def structural_signature(text: str) -> str:
    # crude but cheap structural pattern
    text = text.lower()
    text = re.sub(r"\b(for|to|that|which)\b", "|", text)
    return re.sub(r"[a-z0-9]+", "X", text)

def idea_id(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:12]

# ------------------------------------------------------------
# Load history
# ------------------------------------------------------------

HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
HISTORY_FILE.touch(exist_ok=True)

with open(HISTORY_FILE) as f:
    history = [line.strip() for line in f if line.strip()]

history_tokens = {h: tokenize(h) for h in history}
history_structs = {h: structural_signature(h) for h in history}

# ------------------------------------------------------------
# Load input ideas
# ------------------------------------------------------------

raw_ideas = []

for path in sys.argv[1:]:
    with open(path) as f:
        for line in f:
            obj = json.loads(line)
            raw_ideas.append(obj["idea_text"])

# ------------------------------------------------------------
# Process
# ------------------------------------------------------------

seen_today = []
output = []

for raw in raw_ideas:
    norm = normalize_text(raw)
    tokens = tokenize(norm)
    struct = structural_signature(norm)

    discard = False
    merge_target = None

    for h in history:
        if norm == h:
            discard = True
            break

        if jaccard(tokens, history_tokens[h]) >= 0.80:
            discard = True
            break

        if struct == history_structs[h]:
            merge_target = h
            break

    if discard:
        continue

    if merge_target:
        # MERGE: keep older idea, skip new
        continue

    iid = idea_id(norm)

    output.append({
        "idea_id": iid,
        "idea_text": norm,
        "source": "afh",
        "ingest_date": TODAY
    })

    seen_today.append(norm)

# ------------------------------------------------------------
# Write outputs
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

for obj in output:
    print(json.dumps(obj, ensure_ascii=False))

# Update history ONLY with kept normalized ideas
with open(HISTORY_FILE, "a") as f:
    for idea in seen_today:
        f.write(idea + "\n")

