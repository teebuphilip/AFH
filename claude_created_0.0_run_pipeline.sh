#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "================================================="
echo "AFH PIPELINE START"
echo "================================================="

# ---------------------------------------
# STEP 1: IDEA GENERATION (ChatGPT + Claude)
# ---------------------------------------

echo "[STEP 1] Generating ideas..."
python3 "$BASE_DIR/claude_created_1.0_generate_ideas.py"

echo "[STEP 1] COMPLETE"

# ---------------------------------------
# FUTURE STEPS (placeholders)
# ---------------------------------------
# STEP 2: normalize_and_dedup.py


echo "[STEP 2] Normalize and Dedup..."
python3 "$BASE_DIR/claude_created_2.0_normalize_and_dedup.py"

echo "[STEP 2] COMPLETE"




# STEP 3: overlay_scoring.py
# STEP 4: verdict_router.py
# STEP 5: perplexity_check.py
# STEP 6: arr_scoring.py
# STEP 7: fo_intake.py
# STEP 8: af_gate.py
# STEP 9: move_to_af_bucket.py

echo "================================================="
echo "AFH PIPELINE END"
echo "================================================="
