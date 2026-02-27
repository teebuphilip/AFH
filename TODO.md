# AFH Pipeline TODO

## Status Update (2026-02-27)

Recent fixes are on branch `fix/pipeline-run-paths` (PR #8):
- Step 5 ARR scoring now uses run-specific paths and aligns with Step 3 output schema
- Step 7 AF gate HOLD outputs are run-specific
- Step 4.2 verdict routing preserves scored artifacts for auditability
- Metrics rollup now counts raw JSONL and supports forced refresh

Pending merge to `main`.

## Priority Issues

### 1. Scoring Algorithm Too Conservative ⚠️ HIGH PRIORITY

**Problem:**
- Current scoring produces very low scores (40-62 range)
- Highest observed: Overlay=61, ARR=62
- Current KEEP thresholds: Overlay>=65, ARR>=70
- Result: NO ideas make it to KEEP stage

**Root Cause:**
The keyword matching in `claude_created_3.0_score_overlay_and_arr.py` is either:
1. Not matching keywords properly (case sensitivity, exact match vs. partial?)
2. Default scores too low (currently 40)
3. Keyword lists incomplete

**Example Issue:**
Idea: "Tool that automatically generates weekly invoice summaries for freelancers"
- Should score HIGH on automation (has "automatically generates")
- Should score HIGH on market_clarity (has "invoice")
- Actually scored: overlay=48, arr=49 (all dimensions got ~40)

**Temporary Fix Applied:**
Lowered thresholds to get pipeline working:
- OVERLAY_KEEP_THRESHOLD = 50 (was 65, originally 80)
- ARR_KEEP_THRESHOLD = 55 (was 70, originally 90)

**Permanent Fix Options:**

#### Option A: Fix Keyword Matching
```python
# Current (strict):
if any(k in text for k in ["automated", "scheduled"]):
    return 90

# Better (flexible):
if any(k in text for k in ["automat", "schedul", "batch", "pipeline"]):
    return 90
```

#### Option B: Raise Default Scores
```python
def score_dimension(text: str, rubric) -> int:
    # ... keyword matching ...
    return 60  # Was: 40 (too conservative)
```

#### Option C: Add More Keywords
Review the rubrics in lines 60-96 of `claude_created_3.0_score_overlay_and_arr.py` and add:
- More variations (automate/automated/automation)
- Partial word matching (invoice/invoicing/invoices)
- Industry-specific terms

**Action Items:**
- [ ] Audit scoring output for 10-20 ideas
- [ ] Compare expected vs actual scores
- [ ] Identify missing keywords
- [ ] Test with more lenient matching
- [ ] Adjust default scores or keyword lists
- [ ] Re-test and adjust thresholds back up

---

### 2. Missing Dependencies

**Problem:**
Step 6 (FO Intake Enrichment) fails with:
```
ModuleNotFoundError: No module named 'openai'
```

**Fix:**
```bash
source ~/venvs/cd39/bin/activate
pip install openai
```

**Action Items:**
- [ ] Install openai module
- [ ] Test Step 6 completes successfully
- [ ] Consider adding requirements.txt

---

### 3. Alternative Scripts Not Integrated

**Files:**
- `claude_created_3.1_overlay_scoring.py` (simpler overlay-only scorer)
- `claude_created_4.1_route_verdict.py` (alternative routing logic)

**Status:** Created but not used in main pipeline

**Action Items:**
- [ ] Decide if these should be removed or documented as alternatives
- [ ] If keeping, add usage examples to documentation

---

## Enhancement Ideas (Low Priority)

### 4. Add Deduplication History Across Runs

**Current:** Each run deduplicates only within itself
**Enhancement:** Check against global history to avoid generating same ideas daily

**Implementation:**
- Maintain `data/normalized/history.txt` with all idea_text
- Check new ideas against history during Step 2
- Append new unique ideas to history

---

### 5. Add Configurable Idea Count

**Current:** Hardcoded 25 ideas per generator
**Enhancement:** Make configurable via environment variable or CLI arg

```python
IDEA_COUNT = int(os.getenv("IDEA_COUNT", "25"))
```

---

### 6. Email Notifications for High-Value Ideas

**Enhancement:** Send email when ideas score > 80 or reach catalog

---

### 7. Web Dashboard for Catalog Browsing

**Enhancement:** Simple Flask/FastAPI app to browse:
- Today's run results
- Catalog entries
- Metrics over time

---

## Completed ✅

- [x] Restructured for run-specific directories
- [x] Created comprehensive documentation (AFH_PIPELINE_GUIDE.md)
- [x] Made verdict thresholds configurable
- [x] Added verbose output to orchestrator
- [x] Fixed cross-references between scripts

---

## Notes

**Current Verdict Distribution (2026-02-15):**
- KEEP: 0
- HOLD: 13
- EXCLUDE: 37

**Score Ranges Observed:**
- Overlay: 40-61
- ARR: 40-62

**Thresholds Applied:**
- OVERLAY_KEEP: 50 (temporary)
- ARR_KEEP: 55 (temporary)
- Need to raise these back to 65/70 after fixing scoring
