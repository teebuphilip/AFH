#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AFH — Claude Generator (FINAL, JSON-SAFE)
# ============================================================

MODEL="claude-3-haiku-20240307"
IDEA_COUNT=25
HISTORY_FILE="data/normalized/history.txt"
PROMPT_FILE="prompts/afh_ideas_default.txt"

if [[ -n "${1-}" ]]; then
  PROMPT_FILE="$1"
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "❌ Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$HISTORY_FILE")"
touch "$HISTORY_FILE"
mkdir -p logs

HISTORY_SNIPPET="$(tail -n 400 "$HISTORY_FILE")"

# ------------------------------------------------------------
# Build prompt (raw text)
# ------------------------------------------------------------

PROMPT="$(cat "$PROMPT_FILE")"


# ------------------------------------------------------------
# JSON-escape the prompt (CRITICAL)
# ------------------------------------------------------------

ESCAPED_PROMPT="$(jq -Rs . <<<"$PROMPT")"

# ------------------------------------------------------------
# Call Claude
# ------------------------------------------------------------

RESPONSE="$(curl -sS https://api.anthropic.com/v1/messages \
  -H "x-api-key: ${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY not set}" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"max_tokens\": 2000,
    \"messages\": [
      {\"role\": \"user\", \"content\": $ESCAPED_PROMPT}
    ]
  }"
)"

# ------------------------------------------------------------
# Extract + validate JSON
# ------------------------------------------------------------

IDEAS_JSON="$(echo "$RESPONSE" | jq -e '.content[0].text | fromjson')"

echo "$IDEAS_JSON" \
  | jq -c '.[] | {idea_text: .idea_text}' \
  | while read -r line; do
      idea="$(echo "$line" | jq -r '.idea_text')"
      [[ -n "$idea" ]] || { echo "❌ Empty idea_text" >&2; exit 1; }
      echo "$line"
    done

# Log cost
python3 - <<'PY' "$RESPONSE" "$MODEL"
import json
import os
from datetime import datetime
from pathlib import Path
import sys

raw = sys.argv[1]
model = sys.argv[2]
log_path = Path("logs") / "ai_costs_claude_ideas.csv"
new_file = not log_path.exists()

try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

usage = data.get("usage", {})
in_tokens = usage.get("input_tokens", 0) or 0
out_tokens = usage.get("output_tokens", 0) or 0
in_rate = float(os.getenv("ANTHROPIC_INPUT_PER_MTOK", "3.00"))
out_rate = float(os.getenv("ANTHROPIC_OUTPUT_PER_MTOK", "15.00"))
total = (in_tokens * in_rate + out_tokens * out_rate) / 1_000_000

now = datetime.utcnow()
with log_path.open("a", newline="") as f:
    if new_file:
        f.write("date,time,provider,model,input_tokens,output_tokens,cost_usd\n")
    f.write(
        f"{now.strftime('%Y-%m-%d')},"
        f"{now.strftime('%H:%M:%S')},"
        f"anthropic,{model},{in_tokens},{out_tokens},{total:.6f}\n"
    )
PY
