# AutoFounder Hub (AFH)

## Purpose

This repository is the **system of record** for AutoFounder Hub (AFH).

AFH is an automated pipeline that:
- generates startup ideas
- normalizes and deduplicates them
- evaluates them for economic viability and operational simplicity
- categorizes them into KEEP, HOLD, or EXCLUDE
- publishes a public catalog (HOLD / EXCLUDE only)
- routes private KEEPs to a separate build queue
- archives sold ideas permanently

AFH is designed to run **headless**, **deterministically**, and with **minimal human involvement**.

---

## What This Repo Is

- A **batch-oriented idea pipeline**
- A **catalog and audit trail**
- A **policy-driven system** governed by the Master Context (MC)
- The authoritative storage layer for:
  - generated ideas
  - normalized ideas
  - scoring results
  - verdicts
  - public catalogs
  - sold idea archives

GitHub is the system of record.
There is no database.

---

## What This Repo Is NOT

- Not a SaaS application
- Not a consulting platform
- Not a marketplace engine
- Not a real-time system
- Not a product builder

AFH does **not**:
- build startups
- guarantee outcomes
- provide interactive consulting
- expose internal scoring
- offer refunds

---

## Governing Documents

All behavior is defined by two documents:

- `mc/master_context_v2.2.md`
  - Defines **what the system does**
  - Defines decision rules, guarantees, and boundaries

- `build/afh_build_spec_v0.5.md`
  - Defines **how the system is built**
  - Contains implementation guidance only

If there is a conflict:
**Master Context always wins.**

---

## GitHub Actions

- `AFH Daily Pipeline` (`.github/workflows/afh_pipeline.yml`)
  - Schedule: daily at `09:00 UTC`
  - Entrypoint: `claude_created_0.0_run_afh_pipeline.py`
  - Commits: `data/`, `catalogs/`, `metrics/`, and `logs/YYYY-MM-DD/`
- `AFH Auto GTM` (`.github/workflows/auto_gtm.yml`)
  - Schedule: monthly on the 3rd at `09:00 UTC`
  - Entrypoint: `scripts/auto_gtm_from_keeps.py`
  - Commits: `gtm/` and `scripts/ai_costs.csv`

All steps are deterministic per run.

---

## Pipeline Steps (0.0 → 10.0)

0. `claude_created_0.0_run_afh_pipeline.py`
Runs the full pipeline in order and writes failures to `logs/failures_YYYY-MM-DD.jsonl`.

1. `claude_created_1.0_generate_ideas.py`
Calls `claude_created_1.1_generate_chatgpt.sh` and `claude_created_1.2_generate_claude_afh.sh` and writes JSONL to:
`data/runs/YYYY-MM-DD/raw/chatgpt_YYYY-MM-DD.jsonl` and `data/runs/YYYY-MM-DD/raw/claude_YYYY-MM-DD.jsonl`.

2. `claude_created_2.0_normalize_and_dedup.py`
Normalizes text, TF‑IDF dedups, and writes individual JSON files to:
`data/runs/YYYY-MM-DD/normalized/idea_####.json`.

3. `claude_created_3.0_score_overlay_and_arr.py`
Deterministic keyword heuristic scoring, writes scored ideas to:
`data/runs/YYYY-MM-DD/scored/`.

3.1 `claude_created_3.1_overlay_scoring.py`
Legacy/standalone overlay scorer for JSONL input. Not used by the daily pipeline.

4. `claude_created_4.2_verdict_routing.py`
Routes each scored idea into:
`data/runs/YYYY-MM-DD/verdicts/keep|hold|exclude/` and stamps verdict metadata.

5. `claude_created_5.0_arr_scoring.py`
Secondary ARR routing for KEEPs only. Promotes to FO intake or moves to HOLD/EXCLUDE.

6. `claude_created_6.0_fo_intake_enrich.py`
ChatGPT Q1–Q10 intake enrichment for high‑ARR KEEPs. Writes to `data/fo_intake/`.
Failures are moved to HOLD.

7. `claude_created_7.0_af_gate.py`
Build readiness gate over FO intake. PASS -> `data/af_bucket/`, FAIL -> HOLD.

8. `claude_created_8.0_promote_to_catalog.py`
Promotes AF‑ready ideas to `data/catalog/ideas/` and updates `data/catalog/index.json`.

9. `claude_created_9.0_tag_holding.py`
Builds a public catalog of HOLD/EXCLUDE ideas across all runs at `data/catalog/catalog.json`.

10. `claude_created_10.0_daily_metrics_rollup.py`
Appends a daily snapshot to `metrics/daily_metrics.jsonl`.

---

## Scoring System

**Overlay + ARR (deterministic heuristics, no LLM calls)**
- Dimensions:
  - `pricing_power`
  - `user_count`
  - `automation`
  - `market_clarity`
  - `competition_inverse`
- Overlay score weights:
  - `0.30 * pricing_power`
  - `0.25 * user_count`
  - `0.25 * automation`
  - `0.10 * market_clarity`
  - `0.10 * competition_inverse`
- ARR score weights:
  - `0.35 * pricing_power`
  - `0.30 * user_count`
  - `0.20 * automation`
  - `0.10 * market_clarity`
  - `0.05 * competition_inverse`

**Verdict Routing (4.2 thresholds)**
- KEEP if `overlay_score >= 65` OR `arr_score >= 70`
- HOLD if mid‑range on either score (`overlay_score >= 55` or `arr_score >= 60`)
- EXCLUDE otherwise

**ARR Secondary Routing (5.0)**
- FO intake if `arr_score >= 90`
- HOLD if `arr_score >= 70`
- EXCLUDE otherwise

---

## GTM

`scripts/auto_gtm_from_keeps.py` (run by `AFH Auto GTM`) ranks KEEP ideas and generates GTM one‑pagers.

- Inputs: `data/runs/*/verdicts/keep/*.json`
- Scoring: ChatGPT by default; optional Claude with `--use-claude`
- Outputs:
  - `gtm/auto/idea_01.md` ... for the top ideas
  - `gtm/auto/gtm_summary_YYYYMMDD_HHMMSS.json`
  - `scripts/ai_costs.csv` for token/cost logging

---

## Directory Structure (Summary)

- `mc/`  
  Authoritative system policy

- `build/`  
  Build specifications and implementation notes

- `data/`  
  Pipeline artifacts (raw → normalized → scored → verdicts)

- `catalogs/`  
  Public, private, and sold idea catalogs

- `logs/`  
  Pipeline, integrity, and error logs

- `scripts/`  
  Pipeline runners and verification utilities

---

## Operating Principles

- **Discipline over optimization**
- **Absence-tolerant by design**
- **Fewer, cleaner ideas beat volume**
- **No manual overrides**
- **All sales final**
- **No refunds**

AFH is intentionally boring.

---

## Change Policy

- Changes that affect:
  - decisions
  - rights
  - guarantees
  - customer expectations

  require a **Master Context version bump**.

- Changes that affect:
  - prompts
  - scripts
  - tooling
  - storage mechanics

  belong in the **Build Spec**.

---

## Status

- AFH is under active development
- Master Context v2.2 is considered **structurally complete**
- Build Spec v0.5 is sufficient for initial implementation
- AF (AutoFounder build-and-run engine) is out of scope for this repo

---

## License & Usage

Internal use only.

This repository exists to support:
- AutoFounder Hub

No external guarantees are made.

---

End of README
