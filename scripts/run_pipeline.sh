#!/usr/bin/env bash
set -euo pipefail

RUN_DATE=$(date +%F)

echo "[AFH] Starting pipeline for ${RUN_DATE}"

mkdir -p data/raw data/normalized data/scored data/verdicts

echo "[AFH] Generating ideas from ChatGPT"
./scripts/generate_chatgpt.sh > data/raw/chatgpt_${RUN_DATE}.json

echo "[AFH] Generating ideas from Claude"
./scripts/generate_claude.sh > data/raw/claude_${RUN_DATE}.json

echo "[AFH] Normalizing and deduplicating"
python3 scripts/normalize_and_dedup.py \
  data/raw/chatgpt_${RUN_DATE}.json \
  data/raw/claude_${RUN_DATE}.json \
  > data/normalized/ideas_${RUN_DATE}.jsonl

echo "[AFH] Scoring and assigning verdicts"
python3 scripts/score_and_verdict.py \
  data/normalized/ideas_${RUN_DATE}.jsonl \
  > data/verdicts/verdicts_${RUN_DATE}.jsonl

echo "[AFH] Pipeline completed successfully"

