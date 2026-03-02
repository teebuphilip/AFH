#!/usr/bin/env python3
"""
Auto-rank KEEP ideas and generate GTM one-pagers.

Default: ChatGPT only. Use --use-claude to add Claude scores.
Outputs GTM files with original KEEP file paths.
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime

# Optional clients
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import anthropic
except Exception:
    anthropic = None


def load_keep_files(base: Path):
    files = sorted(base.rglob("verdicts/keep/*.json"))
    return files


def read_json(path: Path):
    return json.loads(path.read_text())


def _append_cost_row(csv_path: Path, ai: str, cost: float, in_tokens: int, out_tokens: int) -> None:
    if not csv_path.exists():
        csv_path.write_text("date,time,ai,cost,input_tokens,output_tokens\n")
    now = datetime.utcnow()
    row = f\"{now.date()},{now.strftime('%H:%M:%S')},{ai},{cost:.6f},{in_tokens},{out_tokens}\\n\"
    with open(csv_path, \"a\", encoding=\"utf-8\") as f:
        f.write(row)


def _estimate_cost(tokens_in: int, tokens_out: int, in_rate: float, out_rate: float) -> float:
    # rates are per 1K tokens
    return (tokens_in / 1000.0) * in_rate + (tokens_out / 1000.0) * out_rate


def chatgpt_score(client, idea_text: str, cost_log: Path):
    prompt = {
        "role": "user",
        "content": (
            "Score this startup idea from 1-10 on:\n"
            "1) ease_to_build\n"
            "2) ease_to_maintain\n"
            "3) chance_make_300_mrr_in_6_months\n\n"
            "Return ONLY valid JSON with keys: ease_to_build, ease_to_maintain, chance_300_mrr_6mo, notes\n"
            "notes should be <= 30 words.\n\n"
            f"Idea: {idea_text}"
        ),
    }
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[prompt],
        temperature=0.2,
    )
    data = json.loads(resp.choices[0].message.content)
    usage = getattr(resp, "usage", None)
    if usage:
        in_tokens = usage.prompt_tokens or 0
        out_tokens = usage.completion_tokens or 0
        # allow configurable cost rates
        in_rate = float(os.getenv("OPENAI_IN_COST_PER_1K", "0"))
        out_rate = float(os.getenv("OPENAI_OUT_COST_PER_1K", "0"))
        cost = _estimate_cost(in_tokens, out_tokens, in_rate, out_rate)
        _append_cost_row(cost_log, "openai", cost, in_tokens, out_tokens)
    return data


def claude_score(client, idea_text: str, cost_log: Path):
    prompt = (
        "Score this startup idea from 1-10 on:\n"
        "1) ease_to_build\n"
        "2) ease_to_maintain\n"
        "3) chance_make_300_mrr_in_6_months\n\n"
        "Return ONLY valid JSON with keys: ease_to_build, ease_to_maintain, chance_300_mrr_6mo, notes\n"
        "notes should be <= 30 words.\n\n"
        f"Idea: {idea_text}"
    )
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
        max_tokens=200,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    data = json.loads(resp.content[0].text)
    usage = getattr(resp, "usage", None)
    if usage:
        in_tokens = usage.input_tokens or 0
        out_tokens = usage.output_tokens or 0
        in_rate = float(os.getenv("ANTHROPIC_IN_COST_PER_1K", "0"))
        out_rate = float(os.getenv("ANTHROPIC_OUT_COST_PER_1K", "0"))
        cost = _estimate_cost(in_tokens, out_tokens, in_rate, out_rate)
        _append_cost_row(cost_log, "anthropic", cost, in_tokens, out_tokens)
    return data


def average_scores(scores):
    # scores: list of dicts
    keys = ["ease_to_build", "ease_to_maintain", "chance_300_mrr_6mo"]
    out = {}
    for k in keys:
        out[k] = round(sum(s[k] for s in scores) / len(scores), 2)
    return out


def total_score(avg):
    return round(avg["ease_to_build"] + avg["ease_to_maintain"] + avg["chance_300_mrr_6mo"], 2)


def gtm_prompt(idea_text: str):
    return (
        "Create a one-page GTM plan in plain language (no paid ads).\n"
        "Use exactly these 5 questions as headings and answer them with short bullets:\n"
        "1) Who are you selling to?\n"
        "2) What are you offering them?\n"
        "3) How will they hear about it? (Free channels only)\n"
        "4) How will they try it?\n"
        "5) How will they pay you?\n\n"
        "Then add two short sections:\n"
        "- Cheap execution checklist\n"
        "- Automation / simplification ideas\n\n"
        f"Idea: {idea_text}"
    )


def chatgpt_gtm(client, idea_text: str, cost_log: Path):
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": gtm_prompt(idea_text)}],
        temperature=0.2,
    )
    usage = getattr(resp, "usage", None)
    if usage:
        in_tokens = usage.prompt_tokens or 0
        out_tokens = usage.completion_tokens or 0
        in_rate = float(os.getenv("OPENAI_IN_COST_PER_1K", "0"))
        out_rate = float(os.getenv("OPENAI_OUT_COST_PER_1K", "0"))
        cost = _estimate_cost(in_tokens, out_tokens, in_rate, out_rate)
        _append_cost_row(cost_log, "openai", cost, in_tokens, out_tokens)
    return resp.choices[0].message.content.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--use-claude", action="store_true", help="Also score with Claude and average")
    ap.add_argument("--out-dir", default="gtm/auto", help="Output directory for GTM files")
    ap.add_argument("--top", type=int, default=3, help="Number of top ideas to output")
    args = ap.parse_args()

    # Fast fail on missing API keys
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY")
    if args.use_claude and not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("Missing ANTHROPIC_API_KEY (required with --use-claude)")

    base = Path("data/runs")
    keep_files = load_keep_files(base)
    if not keep_files:
        raise SystemExit("No KEEP files found under data/runs/*/verdicts/keep")

    if OpenAI is None:
        raise SystemExit("openai package not installed")
    openai_client = OpenAI()

    claude_client = None
    if args.use_claude:
        if anthropic is None:
            raise SystemExit("anthropic package not installed")
        claude_client = anthropic.Anthropic()

    cost_log = Path("scripts/ai_costs.csv")
    scored = []
    for path in keep_files:
        obj = read_json(path)
        idea_text = obj.get("idea_text", "").strip()
        if not idea_text:
            continue

        scores = []
        scores.append(chatgpt_score(openai_client, idea_text, cost_log))
        if claude_client:
            scores.append(claude_score(claude_client, idea_text, cost_log))

        avg = average_scores(scores)
        scored.append({
            "idea_text": idea_text,
            "keep_path": str(path),
            "avg": avg,
            "total": total_score(avg),
            "raw_scores": scores,
        })

    scored.sort(key=lambda x: x["total"], reverse=True)
    top = scored[: args.top]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / f"gtm_summary_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    summary_path.write_text(json.dumps({"top": top, "all": scored}, indent=2))

    for idx, item in enumerate(top, start=1):
        gtm_body = chatgpt_gtm(openai_client, item["idea_text"], cost_log)
        score_header = (
            f"AI Scores (1-10):\n"
            f"- ease_to_build: {item['avg']['ease_to_build']}\n"
            f"- ease_to_maintain: {item['avg']['ease_to_maintain']}\n"
            f"- chance_300_mrr_6mo: {item['avg']['chance_300_mrr_6mo']}\n"
            f"- notes: {item['raw_scores'][0].get('notes', '')}\n"
        )
        gtm = f"{score_header}\n{gtm_body}\n\nOriginal KEEP file: `{item['keep_path']}`\n"
        # filename
        safe_name = "idea_%02d" % idx
        (out_dir / f"{safe_name}.md").write_text(gtm)

    print(f"Wrote {len(top)} GTM files to {out_dir}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
