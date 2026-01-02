#!/usr/bin/env bash
set -euo pipefail

HISTORY_FILE="data/normalized/history.txt"

cat <<EOF | curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d @-
{
  "model": "gpt-4.1-mini",
  "messages": [
    {
      "role": "system",
      "content": "You generate startup ideas. Output JSON only. No prose."
    },
    {
      "role": "user",
      "content": "Generate 25 one-line startup ideas. Avoid repeating or resembling any of the following ideas:\n$(tail -n 400 ${HISTORY_FILE})"
    }
  ],
  "temperature": 0.7
}
EOF

