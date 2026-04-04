#!/usr/bin/env python3
"""
AFH v1.4 — Enrich scored ideas with business brief + SEO + marketing + GTM.

Outputs per idea:
- business_brief.json
- one_liner.txt
- seo.json
- marketing_copy.json
- gtm_plan.json

Default input: data/runs/YYYY-MM-DD/scored/*.json
Default output: data/runs/YYYY-MM-DD/enriched/<idea_id>/
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pass0_gap_check as pass0
import seo_generator as seo_gen
import base_marketing_copy as marketing
import base_gtm_plan as gtm


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _idea_id_from_path(path: Path) -> str:
    return path.stem


def _build_business_brief(
    idea: Dict[str, Any],
    run_date: str,
    idea_id: str,
    provider: str,
    model: str | None,
) -> Tuple[Dict[str, Any], str]:
    deterministic = pass0.run_deterministic_checks(idea)
    research = None
    if provider:
        try:
            if provider == "openai":
                researcher = pass0.OpenAIResearchProvider(model=model)
            else:
                researcher = pass0.AnthropicResearchProvider(model=model)
            research = researcher.research(
                deterministic.idea_text,
                deterministic.intake_summary,
                "; ".join(deterministic.explicit_non_features),
                "; ".join(deterministic.non_goals),
                ", ".join(pass0._load_allowlist(None)),
            )
        except Exception:
            research = None

    locked_fields = pass0._build_locked_fields(deterministic, research)
    locked_fields["mvp_wedge"] = pass0._tighten_wedge_language(locked_fields.get("mvp_wedge"))

    primary_user = locked_fields.get("primary_user") or "unknown audience"
    features = locked_fields.get("must_have_features") or []
    if not features:
        features = pass0._fill_manual_features([])

    idea_text = idea.get("idea_text", "") or deterministic.idea_text or ""
    description = locked_fields.get("mvp_wedge") or idea_text
    one_liner = locked_fields.get("mvp_wedge") or idea_text

    brief = {
        "schema_version": "1.0.0",
        "name": f"{primary_user} tool",
        "description": description,
        "target_audience": primary_user,
        "problem_solved": locked_fields.get("primary_problem") or idea_text,
        "features": features,
        "pricing_model": "unknown",
        "category": "saas",
        "locked_fields": locked_fields,
        "one_liner": one_liner,
        "source": {
            "idea_id": idea_id,
            "run_date": run_date,
            "overlay_score": idea.get("overlay_score"),
            "arr_score": idea.get("arr_score"),
        },
    }
    return brief, one_liner


def _fallback_marketing(brief: Dict[str, Any]) -> Dict[str, Any]:
    persona = brief.get("target_audience") or "target users"
    problem = brief.get("problem_solved") or "a recurring workflow problem"
    features = brief.get("features") or ["manual entry", "tracking", "reminders"]

    def _items(prefix: str) -> List[str]:
        return [
            f"{prefix} for {persona}",
            f"{prefix} to reduce {problem.lower()}",
            f"{prefix} with {features[0]}",
            f"{prefix} built for {persona}",
            f"{prefix} without complex setup",
        ]

    return {
        "taglines": _items("Simple workflow"),
        "hero_headlines": _items("Manual-first tracking"),
        "hero_subheads": _items("Stay on top of work"),
        "value_props": _items("Clear visibility"),
        "feature_bullets": [
            f"{features[0]}",
            f"{features[1] if len(features) > 1 else 'basic tracking'}",
            f"{features[2] if len(features) > 2 else 'reminders'}",
            "Simple onboarding",
            "Exportable summaries",
        ],
        "cta_variants": [
            "Get started",
            "Try it now",
            "See the workflow",
            "Join early access",
            "Request a demo",
        ],
    }


def _generate_marketing_copy(brief: Dict[str, Any], seo: Dict[str, Any], provider: str, model: str | None) -> Dict[str, Any]:
    prompt = marketing._build_prompt(brief, seo)
    try:
        if provider == "openai":
            chosen = model or marketing.DEFAULT_OPENAI_MODEL
            resp = marketing._call_openai(prompt, chosen)
        else:
            chosen = model or marketing.DEFAULT_ANTHROPIC_MODEL
            resp = marketing._call_anthropic(prompt, chosen)
        data = marketing._extract_json(resp["content"])
        marketing._validate_output(data)
        log_path = Path(__file__).resolve().parent / "scripts" / "marketing_copy_ai_costs.csv"
        marketing._log_cost(provider, chosen, resp.get("usage", {}), log_path)
        return data
    except Exception:
        return _fallback_marketing(brief)


def _generate_gtm_plan(brief: Dict[str, Any], one_liner: str, provider: str, model: str | None, no_ai: bool) -> Dict[str, Any]:
    template = gtm._deterministic_template(brief, one_liner)
    if no_ai:
        return template

    prompt = gtm._build_prompt(template, brief, one_liner)
    try:
        if provider == "openai":
            chosen = model or gtm.DEFAULT_OPENAI_MODEL
            resp = gtm._call_openai(prompt, chosen)
        else:
            chosen = model or gtm.DEFAULT_ANTHROPIC_MODEL
            resp = gtm._call_anthropic(prompt, chosen)
        data = gtm._extract_json(resp["content"])
        gtm._validate_output(data, template)
        log_path = Path(__file__).resolve().parent / "scripts" / "gtm_plan_ai_costs.csv"
        gtm._log_cost(provider, chosen, resp.get("usage", {}), log_path)
        return data
    except Exception:
        return template


def _iter_scored_files(scored_dir: Path) -> List[Path]:
    if not scored_dir.exists():
        return []
    return sorted(scored_dir.glob("*.json"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich scored AFH ideas")
    parser.add_argument("--run-date", default=None, help="Run date YYYY-MM-DD (default: today or AFH_RUN_DATE)")
    parser.add_argument("--provider", choices=["openai", "anthropic"], default="openai")
    parser.add_argument("--model", default=None, help="Override model name for marketing/GTM")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI calls, use deterministic outputs")
    args = parser.parse_args()

    run_date = args.run_date or os.getenv("AFH_RUN_DATE") or date.today().isoformat()
    scored_dir = Path("data") / "runs" / run_date / "scored"
    out_dir = Path("data") / "runs" / run_date / "enriched"

    files = _iter_scored_files(scored_dir)
    if not files:
        print(f"No scored ideas found in {scored_dir}")
        return 0

    processed = 0
    failures: List[str] = []

    for path in files:
        idea_id = _idea_id_from_path(path)
        idea_out = out_dir / idea_id
        try:
            idea = _load_json(path)
            research_provider = args.provider if not args.no_ai else ""
            research_model = args.model if args.provider == "openai" else args.model
            brief, one_liner = _build_business_brief(
                idea,
                run_date,
                idea_id,
                research_provider,
                research_model,
            )

            brief_path = idea_out / "business_brief.json"
            one_liner_path = idea_out / "one_liner.txt"
            seo_path = idea_out / "seo.json"
            marketing_path = idea_out / "marketing_copy.json"
            gtm_path = idea_out / "gtm_plan.json"

            _write_json(brief_path, brief)
            _write_text(one_liner_path, one_liner)

            seo = seo_gen.generate_seo(brief)
            _write_json(seo_path, seo)

            marketing_copy = _generate_marketing_copy(brief, seo, args.provider, args.model)
            _write_json(marketing_path, marketing_copy)

            gtm_plan = _generate_gtm_plan(brief, one_liner, args.provider, args.model, args.no_ai)
            _write_json(gtm_path, gtm_plan)

            processed += 1
        except Exception as exc:
            failures.append(f"{idea_id}: {exc}")
            continue

    print(f"Enriched {processed} ideas. Failures: {len(failures)}")
    if failures:
        for entry in failures[:10]:
            print(f"- {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
