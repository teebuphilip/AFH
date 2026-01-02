============================================================
MASTER CONTEXT (MC) — v2.2 CANONICAL / LOCKED
============================================================

OWNER
-----
Teebu

PURPOSE
-------
Authoritative definition of the AutoFounder ecosystem:
- AFH (idea pipeline, catalog, monetization)
- AF (future build-and-run engine)
- FO (human execution & consulting)
- TM (holding company)
- All pipeline decisions, guarantees, and constraints

This document defines SYSTEM BEHAVIOR.
Implementation details live elsewhere.

============================================================
SYSTEM DEFINITIONS
============================================================

AFH — AutoFounder Hub
--------------------
- Automated startup idea generation and evaluation
- Public-facing
- Monetizes ideas and evaluations
- NO product builds
- NO consulting by default
- Designed for operator absence
- Launch: June

AF — AutoFounder
----------------
- Builds and runs boring, simple KEEPs
- Private
- Headless
- Frozen until FO is stable and AFH is cash-flow positive

FO — FounderOps
---------------
- Human-facing intake, build, consulting
- Builds AFH website
- Only execution path for sold ideas
- Only escalation path for customer ideas

TM — Teebu Movil
----------------
- Holding company
- Owns AF-built assets only
- Portfolio governance, not operations

============================================================
PORTFOLIOS (HARD SEPARATION)
============================================================

PUBLIC IDEA CATALOG (AFH)
------------------------
- AFH-generated ideas only
- Contains ONLY:
  • HOLD
  • EXCLUDE
- KEEPs are NEVER public

PRIVATE AF BUILD QUEUE
---------------------
- Final KEEPs only
- Never public
- Never sold

PRIVATE CUSTOMER IDEA PORTFOLIO
-------------------------------
- Customer-submitted ideas only
- Never public
- Never resold
- Routed to FO only

SOLD IDEA ARCHIVE
-----------------
- Purchased HOLD / EXCLUDE ideas
- Removed from public catalog
- Archived permanently
- Never reused or resold

============================================================
AFH PIPELINE (FULL)
============================================================

0) Scheduler
------------
- GitHub Actions (daily)
- Failure → alert
- Success → silence

1) Idea Ingestion
-----------------
- Sources:
  • ChatGPT
  • Claude
  • Internal prompts
- ~50 ideas/day TOTAL
- One-line declarative sentences
- No hype, no naming

2) Normalization
----------------
- AI-based judgment
- Neutral, boring phrasing
- Removes ambition, roadmap language

3) Deduplication & Merge
------------------------
- Occurs AFTER normalization, BEFORE scoring
- Outcomes:
  • PASS
  • DISCARD
  • MERGE
- Preference: fewer, cleaner ideas

4) Classification (Tagging)
----------------------------
- 0–3 flat tags per idea
- Descriptive only
- NEVER affects decisions

5) Internal Scoring (Hidden)
----------------------------
- Lightweight scoring only
- Dimensions:
  • Economic viability
  • Operational simplicity
- NOT FO intake
- Scores never exposed publicly

6) Verdict Assignment
---------------------
- Deterministic thresholds
- Exactly one verdict:
  • KEEP
  • HOLD
  • EXCLUDE
- No human override

7) Perplexity Downgrade Check
-----------------------------
- Applies ONLY to provisional KEEPs
- May downgrade:
  • KEEP → HOLD
  • KEEP → EXCLUDE
- May NEVER upgrade

8) Routing
-----------
- KEEP → AF private queue
- HOLD / EXCLUDE → public catalog
- Customer ideas → FO path

9) Integrity Checks
-------------------
- No KEEP in public catalog
- No customer ideas in public catalog
- Unique idea_id
- Cap enforcement
- Failure aborts commit

10) Storage & Logging
--------------------
- GitHub repo is system of record
- Append-only data
- One commit per successful run

============================================================
DECISION FINALITY
============================================================

- All pipeline decisions are final per run
- No interactive reconsideration
- Re-evaluation ONLY via explicit triggers

============================================================
HOLD RE-EVALUATION RULES
============================================================

Valid triggers ONLY:
1) FO Intake purchase
2) Formal MC rule change
3) Systemic infra / cost shift

No time-based review.
No curiosity review.

============================================================
PURCHASE, REMOVAL & REFUND POLICY
============================================================

GLOBAL RULE
-----------
ALL SALES FINAL. NO REFUNDS.

When an idea is purchased:
- Removed from public catalog
- Archived under sold/
- Buyer email recorded

EDGE CASE
---------
- HOLD purchased → later qualifies as KEEP:
  • Buyer retains full rights
  • Idea flagged SOLD_CONFLICT_KEEP
  • AF / TM permanently excluded

============================================================
CLASSIFICATION / TAGGING POLICY
============================================================

- Tags are descriptive only
- No hierarchies
- No routing or scoring impact
- Used for browsing, deduplication, FO context

============================================================
REVENUE COMMUNICATION (PUBLIC)
============================================================

AFH may state it focuses on ideas that *could*
support approximately $300–$1,000/month
for a solo operator, depending on execution
and market conditions.

No targets. No guarantees.

============================================================
GLOBAL RULES
============================================================

- KEEPs never public
- Customer ideas never resold
- Scores never disclosed
- No refunds
- Discipline > optimization
- Operator absence is required

============================================================
END MASTER CONTEXT v2.2
============================================================

