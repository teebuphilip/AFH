#!/usr/bin/env python3
"""
AFH — FO Intake Enrichment (v1.3 LOCKED)

Purpose:
--------
For KEEP ideas with arr_score >= 90, call ChatGPT once
to answer Q1–Q10 and produce FO build-ready constraints.

Input:
------
data/verdicts/keep/*.json

Output:
-------
data/fo_intake/*.json

Failure:
--------
Moves idea to HOLD with hold_reason = intake_failure
"""

import json
import time
import re
from pathlib import Path
from datetime import datetime, date
from typing import Dict

from openai import OpenAI

# ------------------------------------------------------------------
# Config (ENV)
# ------------------------------------------------------------------

MODEL = "gpt-4o"
MAX_RETRIES = 3
TIMEOUT_SEC = 60

client = OpenAI()

# ------------------------------------------------------------------
# Paths (AUTO - reads from today's run, writes to accumulated)
# ------------------------------------------------------------------

run_date = date.today().isoformat()
RUN_BASE = Path("data") / "runs" / run_date

KEEP_DIR = RUN_BASE / "verdicts" / "keep"
HOLD_DIR = RUN_BASE / "verdicts" / "hold"
FO_DIR = Path("data") / "fo_intake"  # Accumulated across all runs

for d in [HOLD_DIR, FO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# SYSTEM PROMPT (LOCKED)
# ------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a startup build advisor.

Your job is to answer 10 questions about a startup idea to
produce BUILD-READY CONSTRAINTS for an automated build system.

CRITICAL RULES:
- Focus on BUILD CONSTRAINTS, not business strategy
- Be concrete and specific
- No vague language or hype
- Each answer MUST be <=120 words
- Respond ONLY in valid JSON
- No markdown, no preamble, no explanation
- If uncertain, state assumptions explicitly

Output schema:
{
  "Q1": "string",
  "Q2": "string",
  ...
  "Q10": "string"
}
"""

# ------------------------------------------------------------------
# USER PROMPT TEMPLATE (LOCKED)
# ------------------------------------------------------------------

USER_PROMPT_TEMPLATE = """
Startup Idea:
{idea_text}

Scores:
- Overlay Score: {overlay_score}/100
- ARR Score: {arr_score}/100

Answer the following questions to prepare this idea for
automated build. Focus on constraints, not strategy.
Each answer MUST be <=120 words.

Q1. CORE USER & PAIN
Who is the exact primary user, and what single job or pain
does this product exist to solve?

Q2. NON-GOALS (SCOPE BOUNDARY)
What is explicitly OUT OF SCOPE for v1? List things that
must NOT be built.

Q3. SUCCESS CRITERIA
What single measurable signal determines success after
first build?

Q4. USER INTERACTION SURFACE
How does the user interact with the system?
(UI, automation, reports, notifications, etc.)

Q5. DATA INPUT ASSUMPTIONS
What data is assumed to already exist, and what data
must the system generate?

Q6. DECISION AUTHORITY
Are decisions automated, advisory, or human-approved?

Q7. FAILURE TOLERANCE
What failures are acceptable vs unacceptable?

Q8. TIME HORIZON & CADENCE
Real-time, batch, daily, one-off? Does latency matter?

Q9. EVOLUTION BOUNDARY
What is the NEXT thing this product will NOT do?

Q10. KILL CONDITION
What outcome means this idea should be abandoned?

Respond ONLY in valid JSON with keys Q1–Q10.
"""

# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

WORD_LIMIT = 120
WORD_RE = re.compile(r"\b\w+\b")

def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))

def validate_response(obj: Dict) -> None:
    if not isinstance(obj, dict):
        raise ValueError("Response is not JSON object")

    expected_keys = [f"Q{i}" for i in range(1, 11)]
    if sorted(obj.keys()) != expected_keys:
        raise ValueError("JSON keys must be Q1–Q10 exactly")

    for k, v in obj.items():
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{k} is empty or not string")
        if word_count(v) > WORD_LIMIT:
            raise ValueError(f"{k} exceeds {WORD_LIMIT} words")

# ------------------------------------------------------------------
# Chat Call
# ------------------------------------------------------------------

def call_chat(system_prompt: str, user_prompt: str) -> Dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        timeout=TIMEOUT_SEC,
    )

    text = resp.choices[0].message.content
    return json.loads(text)

# ------------------------------------------------------------------
# Main Processing
# ------------------------------------------------------------------

def process_idea(path: Path):
    with open(path) as f:
        idea = json.load(f)

    if idea.get("arr_score", 0) < 90:
        return  # safety guard

    prompt = USER_PROMPT_TEMPLATE.format(
        idea_text=idea["idea_text"],
        overlay_score=idea["overlay_score"],
        arr_score=idea["arr_score"],
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = call_chat(SYSTEM_PROMPT, prompt)
            validate_response(result)

            out = {
                "idea_id": idea.get("idea_id", path.stem),
                "idea_text": idea["idea_text"],
                "overlay_score": idea["overlay_score"],
                "arr_score": idea["arr_score"],
                "intake_answers": result,
                "intake_timestamp": datetime.utcnow().isoformat() + "Z",
                "model": MODEL,
            }

            out_path = FO_DIR / path.name
            with open(out_path, "w") as f:
                json.dump(out, f, indent=2)

            path.unlink()  # remove from KEEP
            return

        except Exception as e:
            last_error = str(e)
            time.sleep(2 ** attempt)

    # ---- Failure → HOLD ----
    idea["verdict"] = "HOLD"
    idea["hold_reason"] = "intake_failure"
    idea["intake_error"] = last_error
    idea["verdict_timestamp"] = datetime.utcnow().isoformat() + "Z"

    hold_path = HOLD_DIR / path.name
    with open(hold_path, "w") as f:
        json.dump(idea, f, indent=2)

    path.unlink()

# ------------------------------------------------------------------

def main():
    for path in KEEP_DIR.glob("*.json"):
        process_idea(path)

if __name__ == "__main__":
    main()
