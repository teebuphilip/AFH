# AFH Pipeline Guide
**AutoFounder Hub - Idea Generation & Validation Pipeline**

Version: 2.1 (Run-Specific Architecture)
Last Updated: 2026-03-27

---

## Table of Contents
1. [Overview](#overview)
2. [GitHub Actions](#github-actions)
3. [Architecture](#architecture)
4. [Directory Structure](#directory-structure)
5. [Pipeline Stages](#pipeline-stages)
6. [Running the Pipeline](#running-the-pipeline)
7. [Scripts Reference](#scripts-reference)
8. [Data Flow](#data-flow)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The AFH pipeline is a 10-stage automated system that generates, scores, validates, and catalogs startup ideas. It uses LLMs (ChatGPT + Claude) only for idea generation and FO intake enrichment. Scoring and gating are deterministic keyword heuristics.

### Key Features
- **Daily Run Isolation**: Each run writes to `data/runs/YYYY-MM-DD/`
- **Deterministic Scoring**: No LLM calls in scoring stages
- **Filesystem as State Machine**: File locations indicate processing stage
- **Idempotent Operations**: Safe to re-run without duplicating catalog entries
- **Audit Trail**: Failures and catalog moves are logged

---

## GitHub Actions

### AFH Daily Pipeline
- Workflow: `.github/workflows/afh_pipeline.yml`
- Schedule: Daily at `09:00 UTC`
- Entrypoint: `claude_created_0.0_run_afh_pipeline.py`
- Commits: `data/`, `catalogs/`, `metrics/`, `logs/YYYY-MM-DD/`
- Daily stats email: `codex_created_11.0_daily_stats_email.py` (sent to `ALERT_EMAIL_TO`)

### AFH Auto GTM
- Workflow: `.github/workflows/auto_gtm.yml`
- Schedule: Monthly on the 3rd at `09:00 UTC`
- Entrypoint: `scripts/auto_gtm_from_keeps.py`
- Commits: `gtm/`, `scripts/ai_costs.csv`

---

## Architecture

### Run-Specific Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY RUN (Isolated)                     │
├─────────────────────────────────────────────────────────────┤
│  data/runs/YYYY-MM-DD/                                      │
│    ├── raw/              ← Step 1: Generate ideas           │
│    ├── normalized/       ← Step 2: Deduplicate              │
│    ├── scored/           ← Step 3: Score (Overlay + ARR)    │
│    └── verdicts/         ← Step 4: Route (KEEP/HOLD/EXCL)   │
│        ├── keep/                                            │
│        ├── hold/                                            │
│        └── exclude/                                         │
└─────────────────────────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────┐
│               ACCUMULATED (Across All Runs)                 │
├─────────────────────────────────────────────────────────────┤
│  data/                                                      │
│    ├── fo_intake/        ← Step 6: FO Enrichment (Q1-Q10)   │
│    ├── af_bucket/        ← Step 7: AF Gate (6 checks)       │
│    └── catalog/          ← Step 8: Final Catalog            │
│        ├── ideas/                                           │
│        └── index.json                                       │
│  metrics/               ← Step 10: daily_metrics.jsonl      │
│  logs/                  ← failures_YYYY-MM-DD.jsonl         │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AFH/
├── .github/workflows/
│   ├── afh_pipeline.yml
│   └── auto_gtm.yml
├── claude_created_0.0_run_afh_pipeline.py       # Full orchestrator (Steps 1-10)
├── claude_created_0.0_run_pipeline.sh           # Simple orchestrator (Steps 1-2)
│
├── claude_created_1.0_generate_ideas.py          # Step 1: Idea Generation
├── claude_created_1.1_generate_chatgpt.sh        # ChatGPT API helper
├── claude_created_1.2_generate_claude_afh.sh     # Claude API helper
│
├── claude_created_2.0_normalize_and_dedup.py     # Step 2: Deduplication
├── claude_created_3.0_score_overlay_and_arr.py   # Step 3: Scoring
├── claude_created_4.2_verdict_routing.py         # Step 4: Verdict Routing
├── claude_created_5.0_arr_scoring.py             # Step 5: Secondary ARR
├── claude_created_6.0_fo_intake_enrich.py        # Step 6: FO Enrichment
├── claude_created_7.0_af_gate.py                 # Step 7: AF Gate
├── claude_created_8.0_promote_to_catalog.py      # Step 8: Catalog Promotion
├── claude_created_9.0_tag_holding.py             # Step 9: Tag Ideas
├── claude_created_10.0_daily_metrics_rollup.py   # Step 10: Metrics
│
├── claude_created_3.1_overlay_scoring.py         # Legacy overlay-only scorer
├── claude_created_4.1_route_verdict.py           # Legacy simple routing
│
└── data/
    ├── runs/
    ├── fo_intake/
    ├── af_bucket/
    └── catalog/
        ├── ideas/
        └── index.json
```

---

## Pipeline Stages

### Stage 1: Idea Generation
**Script:** `claude_created_1.0_generate_ideas.py`
**Input:** None
**Output:** `data/runs/YYYY-MM-DD/raw/*.jsonl`

Generates ideas from ChatGPT and Claude. Writes JSONL to run-specific raw files.

---

### Stage 2: Normalize & Deduplicate
**Script:** `claude_created_2.0_normalize_and_dedup.py`
**Input:** `data/runs/YYYY-MM-DD/raw/*.jsonl`
**Output:** `data/runs/YYYY-MM-DD/normalized/*.json`

Uses TF-IDF cosine similarity (threshold 0.85) to remove duplicates within the run.

---

### Stage 3: Overlay + ARR Scoring
**Script:** `claude_created_3.0_score_overlay_and_arr.py`
**Input:** `data/runs/YYYY-MM-DD/normalized/*.json`
**Output:** `data/runs/YYYY-MM-DD/scored/*.json`

Deterministic keyword-based scoring across five dimensions:
- pricing_power
- user_count
- automation
- market_clarity
- competition_inverse

Overlay and ARR scores are computed with fixed weights (see script for rubric).

---

### Stage 3.5: Enrich Scored Ideas
**Script:** `codex_created_12.0_enrich_scored_ideas.py`
**Input:** `data/runs/YYYY-MM-DD/scored/*.json`
**Output:** `data/runs/YYYY-MM-DD/enriched/<idea_id>/`

Generates per-idea artifacts:
- business brief
- one-liner
- SEO config
- marketing copy
- GTM plan

---

### Stage 3.6: Static HTML Pages
**Script:** `codex_created_14.0_generate_static_idea_pages.py`
**Input:** `data/runs/YYYY-MM-DD/scored/*.json` + `data/runs/YYYY-MM-DD/enriched/<idea_id>/`
**Output:** `static/ideas/<slug>.html`

Renders a static HTML page per idea using the enrichment artifacts.

---

### Stage 4: Verdict Routing (v4.2)
**Script:** `claude_created_4.2_verdict_routing.py`
**Input:** `data/runs/YYYY-MM-DD/scored/*.json`
**Output:** `data/runs/YYYY-MM-DD/verdicts/{keep,hold,exclude}/*.json`

Thresholds:
- KEEP if `overlay_score >= 65` OR `arr_score >= 70`
- HOLD if `overlay_score >= 55` OR `arr_score >= 60`
- EXCLUDE otherwise

Adds verdict metadata fields.

---

### Stage 4.5: Perplexity Keep Review
**Script:** `codex_created_13.0_perplexity_keep_review.py`
**Input:** `data/runs/YYYY-MM-DD/verdicts/keep/*.json`
**Output:** Updates KEEP files with Perplexity score + status.

Rules:
- Score >= 65: build-ready KEEP
- Score < 65: queued for monthly re-run
- 3 failed months: demote to HOLD

---

### Stage 5: ARR Scoring (Secondary, Optional)
**Script:** `claude_created_5.0_arr_scoring.py`
**Input:** `data/runs/YYYY-MM-DD/verdicts/keep/*.json`
**Output:** `data/ready/fo_intake/*.json` or `data/runs/YYYY-MM-DD/verdicts/{hold,exclude}/*.json`

Routes KEEP ideas by ARR score:
- FO_INTAKE if `arr_score >= 90`
- HOLD if `arr_score >= 70`
- EXCLUDE otherwise

Note: This step writes to `data/ready/fo_intake` (legacy path) and removes KEEP files.

---

### Stage 6: FO Intake Enrichment (Legacy)
**Script:** `claude_created_6.0_fo_intake_enrich.py`
**Status:** Not used in the daily pipeline.
**Input:** `data/runs/YYYY-MM-DD/verdicts/keep/*.json` (arr_score >= 90)
**Output:** `data/fo_intake/*.json`

---

### Stage 7: AF Gate
**Script:** `claude_created_7.0_af_gate.py`
**Input:** `data/fo_intake/*.json`
**Output:** PASS -> `data/af_bucket/*.json`, FAIL -> `data/runs/YYYY-MM-DD/verdicts/hold/*.json`

Deterministic checks:
- Legal risk
- External dependency
- Build surface
- Cost ceiling
- Autonomy
- Internal conflict (TF-IDF similarity >= 0.85)

---

### Stage 8: Promote to Catalog
**Script:** `claude_created_8.0_promote_to_catalog.py`
**Input:** `data/af_bucket/*.json`
**Output:** `data/catalog/ideas/{catalog_id}.json`, `data/catalog/index.json`

Stable IDs are SHA256 of idea text. Promotions are logged to `logs/catalog_moves_YYYY-MM-DD.jsonl`.

---

### Stage 9: Tag Holding Ideas
**Script:** `claude_created_9.0_tag_holding.py`
**Input:** `data/runs/*/verdicts/{hold,exclude}/*.json`
**Output:** `data/catalog/catalog.json`

Aggregates HOLD/EXCLUDE ideas across all runs with keyword tags.

---

### Stage 10: Daily Metrics Rollup
**Script:** `claude_created_10.0_daily_metrics_rollup.py`
**Input:** All pipeline data (read-only)
**Output:** `metrics/daily_metrics.jsonl`

Appends a daily snapshot of counts and conversion ratios. Idempotent per UTC day.

---

### Stage 11: Daily Stats Email (workflow-only)
**Script:** `codex_created_11.0_daily_stats_email.py`
**Input:** `data/runs/YYYY-MM-DD/*` and `metrics/daily_metrics.jsonl`
**Output:** Plain-text email body via GitHub Actions

Summarizes daily ChatGPT/Claude idea counts, daily KEEP/HOLD/EXCLUDE, and total metrics across all runs. Sent by the workflow using SMTP credentials in `ALERT_EMAIL_USER` and `ALERT_EMAIL_PASS`.

---

## Running the Pipeline

### Prerequisites

1. **Python Environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Variables**
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Full Pipeline

```bash
python3 claude_created_0.0_run_afh_pipeline.py
```

### Steps 1-2 Only

```bash
./claude_created_0.0_run_pipeline.sh
```

---

## Scripts Reference

| Script | Stage | Input | Output | Blocking |
|--------|-------|-------|--------|----------|
| `claude_created_1.0_generate_ideas.py` | 1 | None | `runs/DATE/raw/*.jsonl` | YES |
| `claude_created_2.0_normalize_and_dedup.py` | 2 | `runs/DATE/raw/` | `runs/DATE/normalized/` | YES |
| `claude_created_3.0_score_overlay_and_arr.py` | 3 | `runs/DATE/normalized/` | `runs/DATE/scored/` | YES |
| `claude_created_4.2_verdict_routing.py` | 4 | `runs/DATE/scored/` | `runs/DATE/verdicts/` | YES |
| `claude_created_5.0_arr_scoring.py` | 5 | `runs/DATE/verdicts/keep/` | `data/ready/fo_intake/` or HOLD/EXCLUDE | NO |
| `claude_created_6.0_fo_intake_enrich.py` | 6 | `runs/DATE/verdicts/keep/` | `data/fo_intake/` | YES |
| `claude_created_7.0_af_gate.py` | 7 | `data/fo_intake/` | `data/af_bucket/` or HOLD | YES |
| `claude_created_8.0_promote_to_catalog.py` | 8 | `data/af_bucket/` | `data/catalog/` | YES |
| `claude_created_9.0_tag_holding.py` | 9 | `runs/*/verdicts/hold,exclude/` | `data/catalog/catalog.json` | NO |
| `claude_created_10.0_daily_metrics_rollup.py` | 10 | All directories | `metrics/daily_metrics.jsonl` | NO |
| `codex_created_11.0_daily_stats_email.py` | 11 | `runs/DATE/` + `metrics/` | Email body | NO |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  DAILY RUN: data/runs/YYYY-MM-DD/                               │
└─────────────────────────────────────────────────────────────────┘
                               │
  Step 1: Generate Ideas       │
  (ChatGPT + Claude)           ↓
                          raw/chatgpt_YYYY-MM-DD.jsonl
                          raw/claude_YYYY-MM-DD.jsonl
                               │
  Step 2: Normalize & Dedup    ↓
                          normalized/idea_0001.json
                          normalized/idea_0002.json
                               │
  Step 3: Score                ↓
                          scored/idea_0001.json
                               │
  Step 4: Route                ↓
                          verdicts/keep/idea_0001.json
                          verdicts/hold/idea_0002.json
                          verdicts/exclude/idea_0003.json
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│  ACCUMULATED: data/                                             │
└─────────────────────────────────────────────────────────────────┘
                               │
  Step 6: AF Gate              ↓
                          af_bucket/idea_0001.json
                               │
  Step 7: Promote              ↓
                          catalog/ideas/cat_a1b2c3d4e5f6.json
                          catalog/index.json
                               │
  Step 8: Tag                  ↓
                          catalog/catalog.json
                               │
  Step 9: Metrics              ↓
                          metrics/daily_metrics.jsonl
```

---

## Troubleshooting

### Issue: No ideas generated

**Symptoms:**
```
❌ Command produced empty output
```

**Causes:**
- Missing API key
- API rate limit
- Network issues

**Solutions:**
```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

---

### Issue: Dedup finds no input

**Symptoms:**
```
No input directory found: data/runs/YYYY-MM-DD/raw
```

**Cause:** Step 1 failed.

**Solution:** Verify raw JSONL files exist and have content.

---

### Issue: FO Intake fails (Legacy)

**Symptoms:**
```
hold_reason: intake_failure
```

**Causes:**
- ChatGPT timeout
- Invalid JSON response
- Word-limit violation

**Solution:** Check `logs/failures_YYYY-MM-DD.jsonl`. Re-run after fixing.

---

### Issue: AF Gate rejects all ideas

**Symptoms:**
All ideas go to HOLD with `gate_failed_check`.

**Causes:**
- Ideas contain blocked keywords
- Internal conflict with existing AF ideas

**Solution:** Review `data/runs/YYYY-MM-DD/verdicts/hold/*.json` and adjust keyword lists if needed.

---

### Issue: Catalog not updating

**Symptoms:** `data/catalog/index.json` not changing

**Cause:** No ideas passed AF Gate.

**Solution:** Check `data/af_bucket/` and upstream outputs.

---

**End of Guide**
