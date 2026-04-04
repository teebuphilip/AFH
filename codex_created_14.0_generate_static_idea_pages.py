#!/usr/bin/env python3
"""
AFH v1.4 — Generate static HTML pages for enriched ideas.

Reads:
- data/runs/YYYY-MM-DD/scored/*.json
- data/runs/YYYY-MM-DD/enriched/<idea_id>/*

Writes:
- static/ideas/<slug>.html
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Dict


def _load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def make_slug(idea_text: str) -> str:
    slug = idea_text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug[:80]


def title_case(text: str) -> str:
    words = re.split(r"\s+", text.strip())
    return " ".join(w.capitalize() if w else w for w in words)


def fill_template(template: str, seo: Dict, brief: Dict) -> str:
    primary = (seo.get("primary_keywords") or [""])[0]
    secondary = (seo.get("secondary_keywords") or [""])[0]
    audience = brief.get("target_audience") or "audience"
    alt = "spreadsheets"
    out = template
    out = out.replace("{primary_keyword}", primary)
    out = out.replace("{secondary_keyword}", secondary)
    out = out.replace("{audience}", audience)
    out = out.replace("{alt}", alt)
    return out


def clean_title(raw_title: str, brand: str = "AutoFounder Hub") -> str:
    parts = [p.strip() for p in raw_title.split("|")]
    parts = [p for p in parts if p and p.lower() != brand.lower()]
    if not parts:
        title_part = brand
    else:
        title_part = parts[0]
    return f"{title_part} | {brand}"


def strip_brand(raw_title: str, brand: str = "AutoFounder Hub") -> str:
    parts = [p.strip() for p in raw_title.split("|")]
    parts = [p for p in parts if p and p.lower() != brand.lower()]
    return parts[0] if parts else raw_title


def render_page(
    scored: Dict,
    brief: Dict,
    seo: Dict,
    marketing: Dict,
    one_liner: str,
    run_date: str,
    idea_id: str,
    base_url: str,
) -> str:
    idea_text = scored.get("idea_text", "").strip()
    slug = make_slug(idea_text)

    title_template = (seo.get("on_page_seo", {})
                      .get("title_templates", ["{primary_keyword} | AutoFounder Hub"]))[0]
    meta_template = (seo.get("on_page_seo", {})
                     .get("meta_description_templates", [""]))[0]

    raw_title = fill_template(title_template, seo, brief).strip()
    full_title = clean_title(raw_title)
    meta_description = fill_template(meta_template, seo, brief).strip()[:160]

    h1 = strip_brand(raw_title) or "Idea"
    hook = (marketing.get("taglines") or [""])[0]

    overlay = scored.get("overlay_score", 0)
    arr = scored.get("arr_score", 0)

    canonical = f"{base_url}/ideas/{slug}"

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">

  <title>{full_title}</title>
  <meta name=\"description\" content=\"{meta_description}\">
  <link rel=\"canonical\" href=\"{canonical}\">
</head>
<body>

  <h1>{h1}</h1>

  <p class=\"one-liner\">{one_liner}</p>

  <div class=\"meta\">
    <span class=\"score\">Score: {overlay}/100</span>
    <span class=\"arr\">ARR Score: {arr}</span>
    <span class=\"date\">Added: {run_date}</span>
  </div>

  <p class=\"hook\">{hook}</p>

  <div class=\"locked\">
    <p>🔒 Full analysis includes:</p>
    <ul>
      <li>Business brief + MVP wedge</li>
      <li>SEO keyword strategy + content plan</li>
      <li>Marketing copy + hero headlines</li>
      <li>GTM plan + cheap execution checklist</li>
    </ul>

    <a href=\"{base_url}/checkout/unenriched/{idea_id}\">Buy exclusively — $2.99</a>
    <a href=\"{base_url}/checkout/enriched/{idea_id}\">Buy enriched — $7.99</a>
    <a href=\"{base_url}/pricing\">Subscribe for all — $11.99/month</a>
  </div>

</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate static HTML pages for enriched ideas")
    parser.add_argument("--run-date", default=None, help="Run date YYYY-MM-DD (default: today or AFH_RUN_DATE)")
    parser.add_argument("--out-dir", default="static/ideas", help="Output directory for HTML files")
    parser.add_argument("--base-url", default="https://afh.com", help="Base URL for canonical/checkout links")
    args = parser.parse_args()

    run_date = args.run_date or os.getenv("AFH_RUN_DATE") or date.today().isoformat()
    scored_dir = Path("data") / "runs" / run_date / "scored"
    enriched_dir = Path("data") / "runs" / run_date / "enriched"
    verdict_dir = Path("data") / "runs" / run_date / "verdicts"
    hold_dir = verdict_dir / "hold"
    exclude_dir = verdict_dir / "exclude"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scored_files = sorted(scored_dir.glob("*.json")) if scored_dir.exists() else []
    if not scored_files:
        print(f"No scored ideas found in {scored_dir}")
        return 0

    written = 0
    hold_names = {p.name for p in hold_dir.glob("*.json")} if hold_dir.exists() else set()
    exclude_names = {p.name for p in exclude_dir.glob("*.json")} if exclude_dir.exists() else set()

    for scored_path in scored_files:
        idea_id = scored_path.stem
        idea_dir = enriched_dir / idea_id
        if not idea_dir.exists():
            continue
        verdict_name = f"{idea_id}.json__0001.json"
        if verdict_name not in hold_names and verdict_name not in exclude_names:
            continue

        scored = _load_json(scored_path)
        brief = _load_json(idea_dir / "business_brief.json")
        seo = _load_json(idea_dir / "seo.json")
        marketing = _load_json(idea_dir / "marketing_copy.json")
        one_liner = _read_text(idea_dir / "one_liner.txt")

        html = render_page(
            scored,
            brief,
            seo,
            marketing,
            one_liner,
            run_date,
            idea_id,
            args.base_url,
        )

        slug = make_slug(scored.get("idea_text", ""))
        out_path = out_dir / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        written += 1

    print(f"Wrote {written} static pages to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
