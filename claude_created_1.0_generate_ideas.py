#!/usr/bin/env python3
"""
AFH — Generate Ideas (ChatGPT + Claude) -> data/raw/

WHY THIS EXISTS
---------------
Your original pipeline convention (run_pipeline.sh.org) writes to:
  data/raw/chatgpt_<RUN_DATE>.jsonl
  data/raw/claude_<RUN_DATE>.jsonl

Downstream (normalize_and_dedup.py) expects JSONL (one JSON object per line)
at those exact paths.

This script:
- Runs your two known-working shell scripts:
    scripts/generate_chatgpt.sh
    scripts/generate_claude_afh.sh
- Captures stdout from each (expected JSONL)
- Writes to the canonical data/raw filenames
- Validates that output is JSONL-ish (each non-empty line is valid JSON)

USAGE
-----
  python3 scripts/generate_ideas.py
  python3 scripts/generate_ideas.py --date 2026-01-10
  python3 scripts/generate_ideas.py --date 2026-01-10 --idea-count 25

NOTES
-----
- No output paths are accepted/needed. Paths are automatic by design.
- --idea-count is passed via env IDEA_COUNT for compatibility (shell scripts may ignore it).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path


def _today_iso() -> str:
    return dt.date.today().isoformat()


def _validate_jsonl(stdout: str, cmd: list[str]) -> None:
    # Hard fail if empty (prevents silently producing 0-byte raw files)
    if not stdout.strip():
        raise RuntimeError(f"Command produced empty output: {' '.join(cmd)}")

    # Validate JSONL: each non-empty line must be valid JSON
    bad_lines: list[tuple[int, str]] = []
    for idx, line in enumerate(stdout.splitlines(), start=1):
        s = line.strip()
        if not s:
            continue
        try:
            json.loads(s)
        except json.JSONDecodeError:
            bad_lines.append((idx, s[:200]))

    if bad_lines:
        preview = "\n".join([f"  line {n}: {frag}" for n, frag in bad_lines[:5]])
        raise RuntimeError(
            f"Output is not valid JSONL for {' '.join(cmd)}\n"
            f"First bad lines:\n{preview}\n"
            f"Hint: your generator must print one JSON object per line."
        )

def _run_cmd(cmd: list[str], env: dict[str, str]) -> str:
    # Run and capture stdout/stderr for diagnostics
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    if proc.returncode != 0:
        # Write stderr to help debugging and ensure the expected raw file is not silently empty.
        err_msg = proc.stderr.strip() or "(no stderr)"
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{err_msg}")

    stdout = proc.stdout
    _validate_jsonl(stdout, cmd)
    return stdout

def _append_output(out_path: Path, stdout: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        f.write(stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AFH ideas into data/raw/ (canonical filenames).")
    parser.add_argument("--date", default=_today_iso(), help="Run date in YYYY-MM-DD (default: today).")
    parser.add_argument("--idea-count", type=int, default=25, help="Target number of ideas per generator (default: 25).")
    parser.add_argument(
        "--prompt-files",
        default="prompts/afh_ideas_ops.txt,prompts/afh_ideas_verticals.txt",
        help="Comma-separated prompt files (default: ops + verticals).",
    )
    args = parser.parse_args()

    run_date = args.date.strip()
    # Basic date validation
    try:
        dt.date.fromisoformat(run_date)
    except ValueError:
        print(f"❌ Invalid --date '{run_date}'. Expected YYYY-MM-DD.", file=sys.stderr)
        return 2

    repo_root = Path.cwd()
#    scripts_dir = repo_root / "scripts"

    chat_script = Path("claude_created_1.1_generate_chatgpt.sh")
    claude_script = Path("claude_created_1.2_generate_claude_afh.sh")


    if not chat_script.exists():
        print(f"❌ Missing: {chat_script}", file=sys.stderr)
        return 2
    if not claude_script.exists():
        print(f"❌ Missing: {claude_script}", file=sys.stderr)
        return 2

    # Use run-specific directory structure
    raw_dir = repo_root / "data" / "runs" / run_date / "raw"
    chat_out = raw_dir / f"chatgpt_{run_date}.jsonl"
    claude_out = raw_dir / f"claude_{run_date}.jsonl"

    prompt_files = [p.strip() for p in args.prompt_files.split(",") if p.strip()]
    if not prompt_files:
        print("❌ No prompt files provided.", file=sys.stderr)
        return 2
    for p in prompt_files:
        if not Path(p).exists():
            print(f"❌ Missing prompt file: {p}", file=sys.stderr)
            return 2

    # Reset outputs for this run (avoid cross-run append)
    if chat_out.exists():
        chat_out.unlink()
    if claude_out.exists():
        claude_out.unlink()

    # Canonical env shared with shell scripts
    env = dict(os.environ)
    env["RUN_DATE"] = run_date
    env["IDEA_COUNT"] = str(args.idea_count)

    # Ensure executable bit not required (we invoke via bash explicitly)
    try:
        for prompt_file in prompt_files:
            chat_stdout = _run_cmd(["/bin/bash", str(chat_script), prompt_file], env=env)
            _append_output(chat_out, chat_stdout)
            claude_stdout = _run_cmd(["/bin/bash", str(claude_script), prompt_file], env=env)
            _append_output(claude_out, claude_stdout)
    except Exception as e:
        print(f"❌ generate_ideas.py failed:\n{e}", file=sys.stderr)
        return 1

    print(f"✅ Wrote:\n  {chat_out}\n  {claude_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
