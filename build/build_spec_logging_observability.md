============================================================
AFH — BUILD SPEC ADDENDUM
LOGGING & OBSERVABILITY (v0.6)
============================================================

PURPOSE
-------
Define deterministic, low-noise logging suitable for a
headless, batch-oriented system.

============================================================
LOGGING PRINCIPLES
============================================================

- Logs are write-only
- Logs are partitioned by DATE
- No log rotation required
- No centralized logging system required

============================================================
LOG DIRECTORY STRUCTURE
============================================================

logs/
└── YYYY-MM-DD/
    ├── pipeline.log
    ├── integrity.log
    ├── errors.log

============================================================
LOG FILE DEFINITIONS
============================================================

pipeline.log
------------
- High-level pipeline steps
- Start / end timestamps
- Step success markers
- Counts only (ideas_ingested, discarded, merged, etc.)

integrity.log
-------------
- Invariant checks
- Schema validation failures
- Deduplication outcomes (counts only)
- Public/private separation checks

errors.log
----------
- Fatal errors only
- Stack traces (if applicable)
- External API failures
- Abort reasons

============================================================
LOGGING RULES
============================================================

- One directory per pipeline run date
- Logs are appended within the run
- Partial runs still write logs
- Successful runs do NOT require review

============================================================
ALERTING POLICY
============================================================

- Alerts fire ONLY on:
  • pipeline abort
  • integrity failure
- Alert channel is implementation-specific
- No alerts on success

============================================================
NON-GOALS
============================================================

- No per-idea verbose logs
- No user-facing logs
- No real-time monitoring dashboards

============================================================
END LOGGING & OBSERVABILITY ADDENDUM
============================================================

