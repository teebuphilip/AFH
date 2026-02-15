#!/usr/bin/env bash
set -euo pipefail

MODEL="gpt-4.1-mini"
IDEA_COUNT=25

OUT_DIR="./data/raw"
RUN_DATE="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/chatgpt_${RUN_DATE}.jsonl"
TMP_JSON="$(mktemp)"

mkdir -p "$OUT_DIR"

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


REQUEST_JSON=$(jq -n \
  --arg model "$MODEL" \
  --arg prompt "$PROMPT" \
  '{
    model: $model,
    temperature: 0.7,
    messages: [{ role: "user", content: $prompt }]
  }'
)

# --- CURL FIRST (BUFFER OUTPUT) ---
HTTP_CODE=$(curl -sS -w "%{http_code}" \
  -o "$TMP_JSON" \
  https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_JSON"
)

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "❌ OpenAI HTTP $HTTP_CODE"
  echo "Response body:"
  cat "$TMP_JSON"
  rm -f "$TMP_JSON"
  exit 1
fi

# --- PARSE SAFELY ---
python3 - <<'PY' "$TMP_JSON" "$OUT_FILE"
import sys, json

src, out = sys.argv[1], sys.argv[2]

with open(src) as f:
    raw = f.read().strip()

obj = json.loads(raw)
content = obj["choices"][0]["message"]["content"]
ideas = json.loads(content)

with open(out, "w") as f:
    for item in ideas:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
PY

jq -e . "$OUT_FILE" >/dev/null
rm -f "$TMP_JSON"

#echo "✅ ChatGPT ideas written to $OUT_FILE"
cat "$OUT_FILE"
