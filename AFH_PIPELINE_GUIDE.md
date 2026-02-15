# AFH Pipeline Guide
**Automated Founder Helper - Idea Generation & Validation Pipeline**

Version: 2.0 (Run-Specific Architecture)
Last Updated: 2026-02-15

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Pipeline Stages](#pipeline-stages)
5. [Running the Pipeline](#running-the-pipeline)
6. [Scripts Reference](#scripts-reference)
7. [Data Flow](#data-flow)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The AFH Pipeline is a 10-stage automated system that generates, scores, validates, and catalogs startup ideas. It uses AI (ChatGPT + Claude) to generate ideas, then applies deterministic scoring and gating to identify high-potential, automatable startup concepts.

### Key Features
- **Daily Run Isolation**: Each day's processing is in its own directory
- **Incremental Processing**: Only new ideas are processed each run
- **Deterministic Scoring**: No LLM calls in scoring stages (keyword-based)
- **Multi-Stage Gating**: Ideas pass through validation gates before catalog
- **Audit Trail**: All moves are logged with timestamps

### Design Principles
- **Filesystem as State Machine**: File locations indicate processing stage
- **Idempotent Operations**: Safe to re-run without duplicating work
- **Conservative Scoring**: Ambiguity defaults to lower scores
- **Separation of Concerns**: Daily runs vs. accumulated catalog

---

## Architecture

### Run-Specific Architecture (v2.0)

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY RUN (Isolated)                     │
├─────────────────────────────────────────────────────────────┤
│  data/runs/YYYY-MM-DD/                                      │
│    ├── raw/              ← Step 1: Generate ideas           │
│    ├── normalized/       ← Step 2: Deduplicate             │
│    ├── scored/           ← Step 3: Score (Overlay + ARR)   │
│    └── verdicts/         ← Step 4: Route (KEEP/HOLD/EXCL)  │
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
│    ├── fo_intake/        ← Step 6: FO Enrichment (Q1-Q10)  │
│    ├── af_bucket/        ← Step 7: AF Gate (6 checks)      │
│    └── catalog/          ← Step 8: Final Catalog           │
│        ├── ideas/                                           │
│        └── index.json                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AFHSCRIPTS/
├── claude_created_0.0_run_pipeline.sh           # Simple orchestrator (Steps 1-2)
├── claude_created_0.0_run_afh_pipeline.py       # Full orchestrator (All steps)
│
├── claude_created_1.0_generate_ideas.py         # Step 1: Idea Generation
├── claude_created_1.1_generate_chatgpt.sh       # ChatGPT API helper
├── claude_created_1.2_generate_claude_afh.sh    # Claude API helper
│
├── claude_created_2.0_normalize_and_dedup.py    # Step 2: Deduplication
├── claude_created_3.0_score_overlay_and_arr.py  # Step 3: Scoring
├── claude_created_4.0_verdict_routing.py        # Step 4: Verdict Routing
├── claude_created_5.0_arr_scoring.py            # Step 5: Secondary ARR
├── claude_created_6.0_fo_intake_enrich.py       # Step 6: FO Enrichment
├── claude_created_7.0_af_gate.py                # Step 7: AF Gate
├── claude_created_8.0_promote_to_catalog.py     # Step 8: Catalog Promotion
├── claude_created_9.0_tag_holding.py            # Step 9: Tag Ideas
├── claude_created_10.0_daily_metrics_rollup.py  # Step 10: Metrics
│
├── claude_created_3.1_overlay_scoring.py        # Alternative: Overlay only
├── claude_created_4.1_route_verdict.py          # Alternative: Simple routing
│
└── data/
    ├── runs/
    │   ├── 2026-02-15/
    │   │   ├── raw/
    │   │   ├── normalized/
    │   │   ├── scored/
    │   │   └── verdicts/
    │   └── 2026-02-16/
    │       └── ...
    ├── fo_intake/
    ├── af_bucket/
    ├── catalog/
    │   ├── ideas/
    │   └── index.json
    ├── logs/
    └── metrics/
        └── daily_metrics.jsonl
```

---

## Pipeline Stages

### Stage 1: Idea Generation
**Script:** `claude_created_1.0_generate_ideas.py`
**Input:** None
**Output:** `data/runs/YYYY-MM-DD/raw/*.jsonl`

Generates 25 ideas each from ChatGPT and Claude using carefully crafted prompts focused on:
- Boring, paid utilities
- Single primary user
- Automatable features
- $300-$1,000/month revenue potential

**Key Features:**
- JSONL validation (ensures valid JSON per line)
- Empty output detection (fails fast if no ideas generated)
- Date-stamped output files

---

### Stage 2: Normalize & Deduplicate
**Script:** `claude_created_2.0_normalize_and_dedup.py`
**Input:** `data/runs/YYYY-MM-DD/raw/*.jsonl`
**Output:** `data/runs/YYYY-MM-DD/normalized/*.json`

Uses TF-IDF cosine similarity (threshold 0.85) to remove duplicates within today's batch.

**Algorithm:**
1. Normalize text (lowercase, remove punctuation, collapse whitespace)
2. Compute TF-IDF vectors with bigrams
3. Compare each new idea against kept ideas
4. Keep only if similarity < 0.85

---

### Stage 3: Overlay + ARR Scoring
**Script:** `claude_created_3.0_score_overlay_and_arr.py`
**Input:** `data/runs/YYYY-MM-DD/normalized/*.json`
**Output:** `data/runs/YYYY-MM-DD/scored/*.json`

**Deterministic keyword-based scoring** across 5 dimensions:

| Dimension | Weight (Overlay) | Weight (ARR) | Scoring Bands |
|-----------|------------------|--------------|---------------|
| Pricing Power | 30% | 35% | 90: B2B/SaaS, 70: Freemium, 50: Ads, 30: Community |
| User Count | 25% | 30% | 90: Businesses, 70: Professionals, 50: Consumers |
| Automation | 25% | 20% | 90: Automated, 70: Assisted, 50: Manual |
| Market Clarity | 10% | 10% | 90: Clear pain, 70: Productivity, 50: Analytics |
| Competition | 10% | 5% | 90: Niche, 70: Vertical, 50: General |

**Formulas:**
- **Overlay Score** = Economic + Operational viability (0-100)
- **ARR Score** = Revenue feasibility (0-100)

---

### Stage 4: Verdict Routing
**Script:** `claude_created_4.0_verdict_routing.py`
**Input:** `data/runs/YYYY-MM-DD/scored/*.json`
**Output:** `data/runs/YYYY-MM-DD/verdicts/{keep,hold,exclude}/*.json`

Routes ideas based on score thresholds:

| Verdict | Criteria | Next Step |
|---------|----------|-----------|
| **KEEP** | overlay > 80 OR arr >= 90 | → FO Intake Enrichment |
| **HOLD** | 65 ≤ overlay ≤ 80 OR 70 ≤ arr < 90 | → Manual review |
| **EXCLUDE** | Below both thresholds | → Archive |

**Metadata Added:**
- `verdict`: KEEP/HOLD/EXCLUDE
- `verdict_timestamp`: UTC ISO timestamp
- `verdict_source`: "overlay_score"

---

### Stage 5: ARR Scoring (Optional)
**Script:** `claude_created_5.0_arr_scoring.py`
**Input:** `data/runs/YYYY-MM-DD/verdicts/keep/*.json`
**Output:** `data/ready/fo_intake/*.json`

Secondary ARR qualification for KEEP ideas. Routes to:
- **FO_INTAKE** if arr_score >= 90
- **HOLD** if 70 ≤ arr_score < 90
- **EXCLUDE** if arr_score < 70

---

### Stage 6: FO Intake Enrichment
**Script:** `claude_created_6.0_fo_intake_enrich.py`
**Input:** `data/runs/YYYY-MM-DD/verdicts/keep/*.json` (arr_score >= 90)
**Output:** `data/fo_intake/*.json` (accumulated)

**ChatGPT call** to answer Q1-Q10 build constraints:

| Question | Purpose |
|----------|---------|
| Q1 | Core user & pain point |
| Q2 | Non-goals (scope boundary) |
| Q3 | Success criteria |
| Q4 | User interaction surface |
| Q5 | Data input assumptions |
| Q6 | Decision authority (automated/advisory/human) |
| Q7 | Failure tolerance |
| Q8 | Time horizon & cadence |
| Q9 | Evolution boundary |
| Q10 | Kill condition |

**Constraints:**
- Model: GPT-4o
- Max 120 words per answer
- 3 retries with exponential backoff
- 60-second timeout
- **Failure → HOLD** with `hold_reason: intake_failure`

---

### Stage 7: AF Gate
**Script:** `claude_created_7.0_af_gate.py`
**Input:** `data/fo_intake/*.json`
**Output:** `data/af_bucket/*.json` (PASS) or `data/verdicts/hold/*.json` (FAIL)

**6 Deterministic Gate Checks:**

1. **Legal Risk**: Blocks gambling, adult content, medical/financial advice
2. **Dependencies**: Blocks partnerships, approvals, invite-only models
3. **Build Surface**: Blocks real-time, dashboards, multi-role complexity
4. **Cost Ceiling**: Blocks streaming, GPU, video/audio processing
5. **Autonomy**: Blocks features requiring login, auth, human review
6. **Internal Conflict**: TF-IDF similarity >= 0.85 with existing AF bucket ideas

**PASS** → `data/af_bucket/`
**FAIL** → `data/verdicts/hold/` with `gate_failed_check` reason

---

### Stage 8: Promote to Catalog
**Script:** `claude_created_8.0_promote_to_catalog.py`
**Input:** `data/af_bucket/*.json`
**Output:** `data/catalog/ideas/{catalog_id}.json`, `data/catalog/index.json`

**Materializes AF-ready ideas into durable catalog:**

- **Stable IDs**: SHA256(idea_text)[:12] → `cat_<12chars>`
- **Idempotent**: Re-running updates metadata, doesn't duplicate
- **Audit Log**: `logs/catalog_moves_{YYYY-MM-DD}.jsonl`

**Index Structure:**
```json
[
  {
    "catalog_id": "cat_a1b2c3d4e5f6",
    "idea_text": "...",
    "overlay_score": 85,
    "arr_score": 92,
    "catalog_added_at": "2026-02-15T10:30:00Z",
    "catalog_updated_at": "2026-02-15T10:30:00Z"
  }
]
```

---

### Stage 9: Tag Holding Ideas
**Script:** `claude_created_9.0_tag_holding.py`
**Input:** `data/runs/*/verdicts/{hold,exclude}/*.json` (all runs)
**Output:** `data/catalog/catalog.json`

**Aggregates rejected ideas from ALL runs** with keyword-based tags:

- **Category**: marketing, finance, hr, operations, productivity, education, health, legal
- **Complexity**: low, medium, high
- **Monetization Model**: subscription, freemium, ads, commission

**Use Case:** Public-facing browsable catalog of "not quite ready" ideas

---

### Stage 10: Daily Metrics Rollup
**Script:** `claude_created_10.0_daily_metrics_rollup.py`
**Input:** All data directories (read-only)
**Output:** `metrics/daily_metrics.jsonl` (append-only)

**Captures daily snapshot:**
- Counts across all runs (total_raw, total_normalized, total_keep, etc.)
- Today's specific counts (today_raw, today_keep, etc.)
- Conversion ratios (keep_rate, fo_intake_to_af, af_to_catalog)

**Idempotent:** One entry per UTC date (won't double-write same day)

---

## Running the Pipeline

### Prerequisites

1. **Python Environment**
```bash
source ~/venvs/cd39/bin/activate
```

2. **Required Python Packages**
```bash
pip install openai anthropic scikit-learn
```

3. **Environment Variables**
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Daily Run (Full Pipeline)

```bash
cd /Users/teebuphilip/Downloads/AFHSCRIPTS
source ~/venvs/cd39/bin/activate
python3 claude_created_0.0_run_afh_pipeline.py
```

This will:
1. Generate ideas → `data/runs/2026-02-15/raw/`
2. Normalize & dedup → `data/runs/2026-02-15/normalized/`
3. Score → `data/runs/2026-02-15/scored/`
4. Route → `data/runs/2026-02-15/verdicts/`
5. Enrich → `data/fo_intake/`
6. Gate → `data/af_bucket/`
7. Catalog → `data/catalog/`
8. Tag → `data/catalog/catalog.json`
9. Metrics → `metrics/daily_metrics.jsonl`

### Partial Run (Steps 1-2 Only)

```bash
./claude_created_0.0_run_pipeline.sh
```

### Manual Step-by-Step

```bash
# Step 1
python3 claude_created_1.0_generate_ideas.py

# Step 2
python3 claude_created_2.0_normalize_and_dedup.py

# Step 3
python3 claude_created_3.0_score_overlay_and_arr.py

# Step 4
python3 claude_created_4.0_verdict_routing.py

# Step 6
python3 claude_created_6.0_fo_intake_enrich.py

# Step 7
python3 claude_created_7.0_af_gate.py

# Step 8
python3 claude_created_8.0_promote_to_catalog.py

# Step 9
python3 claude_created_9.0_tag_holding.py

# Step 10
python3 claude_created_10.0_daily_metrics_rollup.py
```

---

## Scripts Reference

### Orchestrators

#### `claude_created_0.0_run_pipeline.sh`
Simple bash orchestrator running Steps 1-2 only.

**Usage:**
```bash
./claude_created_0.0_run_pipeline.sh
```

#### `claude_created_0.0_run_afh_pipeline.py`
Full Python orchestrator running all 10 steps with error logging.

**Features:**
- Silent execution (stdout/stderr suppressed)
- Failure logging to `logs/failures_{DATE}.jsonl`
- Non-blocking for optional steps (Step 5, 9)

**Usage:**
```bash
python3 claude_created_0.0_run_afh_pipeline.py
```

### Core Pipeline Scripts

| Script | Stage | Input | Output | Blocking |
|--------|-------|-------|--------|----------|
| `claude_created_1.0_generate_ideas.py` | 1 | None | `runs/DATE/raw/*.jsonl` | YES |
| `claude_created_2.0_normalize_and_dedup.py` | 2 | `runs/DATE/raw/` | `runs/DATE/normalized/` | YES |
| `claude_created_3.0_score_overlay_and_arr.py` | 3 | `runs/DATE/normalized/` | `runs/DATE/scored/` | YES |
| `claude_created_4.0_verdict_routing.py` | 4 | `runs/DATE/scored/` | `runs/DATE/verdicts/` | YES |
| `claude_created_5.0_arr_scoring.py` | 5 | `runs/DATE/verdicts/keep/` | `data/ready/fo_intake/` | NO |
| `claude_created_6.0_fo_intake_enrich.py` | 6 | `runs/DATE/verdicts/keep/` | `data/fo_intake/` | YES |
| `claude_created_7.0_af_gate.py` | 7 | `data/fo_intake/` | `data/af_bucket/` | YES |
| `claude_created_8.0_promote_to_catalog.py` | 8 | `data/af_bucket/` | `data/catalog/` | YES |
| `claude_created_9.0_tag_holding.py` | 9 | `runs/*/verdicts/hold,exclude/` | `data/catalog/catalog.json` | NO |
| `claude_created_10.0_daily_metrics_rollup.py` | 10 | All directories | `metrics/daily_metrics.jsonl` | NO |

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  DAILY RUN: data/runs/2026-02-15/                              │
└─────────────────────────────────────────────────────────────────┘
                               │
  Step 1: Generate Ideas       │
  (ChatGPT + Claude)          ↓
                          raw/chatgpt_2026-02-15.jsonl
                          raw/claude_2026-02-15.jsonl
                               │
  Step 2: Normalize & Dedup   ↓
  (TF-IDF similarity 0.85)
                          normalized/idea_0001.json
                          normalized/idea_0002.json
                               │
  Step 3: Score               ↓
  (Overlay + ARR)
                          scored/idea_0001.json  (with scores)
                               │
  Step 4: Route               ↓
  (Threshold-based)
                          verdicts/keep/idea_0001.json
                          verdicts/hold/idea_0002.json
                          verdicts/exclude/idea_0003.json
                               │
┌──────────────────────────────┴──────────────────────────────────┐
│  ACCUMULATED: data/                                             │
└─────────────────────────────────────────────────────────────────┘
                               │
  Step 6: FO Intake           ↓
  (ChatGPT Q1-Q10)
                          fo_intake/idea_0001.json (with Q&A)
                               │
  Step 7: AF Gate             ↓
  (6 deterministic checks)
                          af_bucket/idea_0001.json  (PASS)
                          verdicts/hold/idea_XXXX.json (FAIL)
                               │
  Step 8: Promote             ↓
  (Stable SHA256 IDs)
                          catalog/ideas/cat_a1b2c3d4e5f6.json
                          catalog/index.json
                               │
  Step 9: Tag                 ↓
  (All runs aggregated)
                          catalog/catalog.json (HOLD+EXCLUDE)
                               │
  Step 10: Metrics            ↓
  (Daily snapshot)
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
- API key not set or invalid
- API rate limit exceeded
- Network connectivity issue

**Solutions:**
```bash
# Check API keys
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# Test API directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

---

### Issue: Python import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'sklearn'
```

**Solution:**
```bash
source ~/venvs/cd39/bin/activate
pip install scikit-learn openai anthropic
```

---

### Issue: Dedup finds no ideas

**Symptoms:**
```
No input directory found: data/runs/2026-02-15/raw
```

**Cause:** Step 1 (generate_ideas) didn't complete successfully

**Solution:**
1. Check `data/runs/YYYY-MM-DD/raw/` exists
2. Verify JSONL files have content
3. Re-run Step 1

---

### Issue: FO Intake fails

**Symptoms:**
```
hold_reason: intake_failure
```

**Causes:**
- ChatGPT API timeout
- Invalid JSON response
- Answer exceeds 120 words

**Solution:**
- Check `logs/failures_{DATE}.jsonl` for details
- Ideas are moved to HOLD (safe, can be retried)
- Adjust MAX_RETRIES or TIMEOUT_SEC if needed

---

### Issue: AF Gate rejects all ideas

**Symptoms:**
All ideas go to HOLD with `gate_failed_check`

**Causes:**
- Ideas contain blocked keywords
- Internal conflict with existing AF bucket ideas

**Solution:**
1. Review `data/verdicts/hold/*.json` for `gate_failed_check` field
2. Adjust gate keyword lists if too aggressive
3. Check similarity threshold (currently 0.85)

---

### Issue: Catalog not updating

**Symptoms:**
`data/catalog/index.json` shows old date

**Cause:** No ideas passed AF Gate

**Solution:**
```bash
# Check AF bucket
ls -la data/af_bucket/

# If empty, check previous stages
ls -la data/fo_intake/
ls -la data/runs/*/verdicts/keep/
```

---

### Issue: Metrics showing zero

**Symptoms:**
```json
{"counts": {"today_raw": 0, ...}}
```

**Cause:** Idempotency check (metrics already recorded for today)

**Solution:**
- Metrics run once per UTC date
- Check `metrics/daily_metrics.jsonl` for existing entry
- Safe to ignore if entry exists

---

## Best Practices

### 1. Daily Cron Schedule
```bash
# Run at 2 AM daily
0 2 * * * cd /path/to/AFHSCRIPTS && source ~/venvs/cd39/bin/activate && python3 claude_created_0.0_run_afh_pipeline.py >> logs/cron_$(date +\%Y-\%m-\%d).log 2>&1
```

### 2. Disk Space Management
```bash
# Archive old runs (older than 30 days)
find data/runs/ -type d -mtime +30 -exec mv {} archive/ \;
```

### 3. Backup Strategy
```bash
# Backup catalog and accumulated data weekly
tar -czf backup_$(date +%Y%m%d).tar.gz data/catalog/ data/fo_intake/ data/af_bucket/
```

### 4. Monitoring
```bash
# Check today's run status
ls -lh data/runs/$(date +%Y-%m-%d)/

# Check catalog growth
wc -l data/catalog/index.json

# Review failures
tail -f logs/failures_$(date +%Y-%m-%d).jsonl
```

---

## Appendix

### Scoring Rubrics (v1.3 LOCKED)

Full keyword lists available in:
- `claude_created_3.0_score_overlay_and_arr.py`

### Gate Keyword Lists

Full blocklists available in:
- `claude_created_7.0_af_gate.py`

### File Formats

**JSONL (raw ideas):**
```json
{"idea_text": "Tool that automatically generates..."}
```

**Scored idea:**
```json
{
  "idea_text": "...",
  "scores": {
    "pricing_power": 90,
    "user_count": 70,
    ...
  },
  "overlay_score": 82,
  "arr_score": 88
}
```

**Catalog entry:**
```json
{
  "catalog_id": "cat_a1b2c3d4e5f6",
  "idea_text": "...",
  "overlay_score": 85,
  "arr_score": 92,
  "verdict": "AF_READY",
  "intake_answers": { "Q1": "...", "Q2": "...", ... },
  "catalog_added_at": "2026-02-15T10:30:00Z",
  "catalog_updated_at": "2026-02-15T10:30:00Z"
}
```

---

**End of Guide**

For questions or issues, review the troubleshooting section or check the source code comments.
