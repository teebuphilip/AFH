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

## High-Level Pipeline

1. Scheduled run (GitHub Actions)
2. Idea ingestion (ChatGPT / Claude)
3. Normalization (AI-based)
4. Deduplication & merge
5. Tagging
6. Lightweight scoring (internal only)
7. Verdict assignment (KEEP / HOLD / EXCLUDE)
8. Perplexity downgrade (KEEPS only)
9. Routing and storage
10. Commit results or abort on failure

All steps are deterministic per run.

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
- FounderOps intake routing
- Teebu Movil portfolio operations

No external guarantees are made.

---

End of README
