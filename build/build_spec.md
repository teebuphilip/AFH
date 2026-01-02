============================================================
AFH — BUILD SPECIFICATION v0.5
============================================================

PURPOSE
-------
Define HOW AFH is built without redefining policy.
This document answers implementation questions only.

============================================================
ARCHITECTURE
============================================================

- Batch-oriented
- Stateless pipeline
- No database required
- GitHub as system of record

============================================================
GENERATOR CONTRACT
============================================================

- Claude and ChatGPT must emit JSON only
- Schema:
  {
    "idea_text": string
  }

- One sentence
- Declarative
- No hype
- No branding

Invalid output → batch rejected

============================================================
ANTI-REPEAT STRATEGY
============================================================

- Maintain historical corpus from normalized ideas
- Inject rolling subset into generator prompts
- Apply same rules to Claude and ChatGPT

============================================================
DEDUPLICATION LOGIC
============================================================

Checks (cheap only):
- Exact match
- High token overlap
- Structural pattern match

Outcomes:
- PASS
- DISCARD (default)
- MERGE (rare)

MERGE RULES:
- Older idea_id retained
- Text may be clarified
- Max one merge per idea lifetime

============================================================
SCORING IMPLEMENTATION
============================================================

- AI judgment allowed
- Two scores only:
  • Economic viability
  • Operational simplicity
- Integers 0–100
- Overlay = simple average

============================================================
PERPLEXITY USAGE
============================================================

- Used ONLY for provisional KEEPs
- Purpose:
  • detect incumbents
  • detect saturation
- Output is downgrade signal only

============================================================
PAYMENTS & CRM
============================================================

- Stripe for payments
- All sales final
- Buyer email captured on:
  • idea purchase
  • eval
  • FO intake
- Stored in free/freemium CRM
- ONE FO nudge allowed

============================================================
FAILURE HANDLING
============================================================

- Any invariant violation aborts run
- No partial commits
- Alert on failure only

============================================================
NON-GOALS
============================================================

- No dashboards
- No admin UI
- No refunds
- No support workflows
- No embeddings or vector DBs

============================================================
END AFH BUILD SPEC v0.5
============================================================

