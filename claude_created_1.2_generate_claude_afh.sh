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
