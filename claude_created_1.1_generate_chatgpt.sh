#!/usr/bin/env bash
set -euo pipefail

MODEL="gpt-4.1-mini"
IDEA_COUNT=25

OUT_DIR="./data/raw"
RUN_DATE="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${OUT_DIR}/chatgpt_${RUN_DATE}.jsonl"
TMP_JSON="$(mktemp)"
PROMPT_FILE="prompts/afh_ideas_default.txt"

if [[ -n "${1-}" ]]; then
  PROMPT_FILE="$1"
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "❌ Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

PROMPT="$(cat "$PROMPT_FILE")"


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
