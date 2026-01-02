#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AFH — Claude Generator (AFH-Compliant)
# ============================================================

MODEL="claude-3-haiku-20240307"
IDEA_COUNT=25
HISTORY_FILE="data/normalized/history.txt"

if [[ ! -f "$HISTORY_FILE" ]]; then
  touch "$HISTORY_FILE"
fi

HISTORY_SNIPPET=$(tail -n 400 "$HISTORY_FILE")

read -r -d '' PROMPT <<EOF
YOU ARE A STARTUP IDEA GENERATOR.

STRICT OUTPUT RULES (MANDATORY):
- Output VALID JSON ONLY
- NO prose
- NO markdown
- NO explanations
- ONE idea per JSON object
- Format EXACTLY:
  { "idea_text": "single sentence startup idea" }

CONTENT RULES:
- One sentence only
- Declarative
- No hype
- No naming or branding
- No emojis
- No bullet points

ANTI-REPETITION RULE:
Do NOT repeat or closely resemble any of the following ideas:
$HISTORY_SNIPPET

TASK:
Generate $IDEA_COUNT distinct startup ideas.

Output an ARRAY of JSON objects.
EOF

RESPONSE=$(curl -sS https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"max_tokens\": 2000,
    \"messages\": [
      {\"role\": \"user\", \"content\": \"$PROMPT\"}
    ]
  }")

# Extract JSON safely
IDEAS=$(echo "$RESPONSE" | jq -e '.content[0].text | fromjson')

# Schema validation + output
echo "$IDEAS" | jq -c '.[] | {idea_text: .idea_text}' \
  | while read -r line; do
      idea=$(echo "$line" | jq -r '.idea_text')
      [[ -z "$idea" ]] && exit 1
      echo "$line"
    done

