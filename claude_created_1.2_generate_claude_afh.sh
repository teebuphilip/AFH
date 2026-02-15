#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AFH — Claude Generator (FINAL, JSON-SAFE)
# ============================================================

MODEL="claude-3-haiku-20240307"
IDEA_COUNT=25
HISTORY_FILE="data/normalized/history.txt"

mkdir -p "$(dirname "$HISTORY_FILE")"
touch "$HISTORY_FILE"

HISTORY_SNIPPET="$(tail -n 400 "$HISTORY_FILE")"

# ------------------------------------------------------------
# Build prompt (raw text)
# ------------------------------------------------------------

PROMPT=$(cat <<'PROMPT_EOF'
YOU ARE A STARTUP IDEA GENERATOR FOR THE AFH PIPELINE.

YOUR GOAL:
Generate startup ideas that are:
- Boring
- Paid utilities
- Single primary user
- Automatable
- Capable of $300–$1,000/month revenue
- Simple enough for a small automated build system

STRICT OUTPUT RULES:
- Output VALID JSON ONLY
- Output MUST be a JSON ARRAY
- Each element MUST be:
  { "idea_text": "single sentence startup idea" }
- No extra fields
- No markdown
- No commentary
- No explanations

CONTENT RULES (MANDATORY):
Each idea MUST:
- Solve a specific, practical, recurring problem
- Have a clear paying user
- Be usable by a single person or small team
- Be automatable or mostly automated
- Sound like a small paid tool, not a platform

AVOID THESE COMPLETELY:
- Social networks
- Marketplaces
- Creator platforms
- Communities
- Wellness, habits, or lifestyle apps
- Dating, fitness, or mental health
- Consumer entertainment
- Multi-sided platforms
- Real-time collaboration tools
- "AI for everything" vague concepts
- Anything that depends on network effects

GOOD IDEA SHAPES:
- "Tool that automatically generates…"
- "Service that monitors… and sends alerts…"
- "System that converts… into…"
- "Dashboard that summarizes…"
- "Automation that processes… and outputs…"

TARGET CUSTOMER TYPES:
- Freelancers
- Small business owners
- Operations managers
- Recruiters
- Accountants
- Property managers
- Support teams
- Sales teams
- HR coordinators

TASK:
Generate 25 DISTINCT startup ideas that follow all rules above.

Return ONLY the JSON array.
PROMPT_EOF
)


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
