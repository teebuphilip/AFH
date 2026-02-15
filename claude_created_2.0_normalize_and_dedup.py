#!/usr/bin/env python3
import sys
import json
import re
from pathlib import Path
from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SIM_THRESHOLD = 0.85

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def load_ideas(input_dir: Path):
    ideas = []

    for path in sorted(input_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix != ".jsonl":
            continue

        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if "idea_text" in obj:
                    ideas.append(obj["idea_text"])

    return ideas

def dedup(ideas):
    normalized = [normalize(i) for i in ideas]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1
    )

    tfidf = vectorizer.fit_transform(normalized)

    keep_indices = []

    for i in range(tfidf.shape[0]):
        if not keep_indices:
            keep_indices.append(i)
            continue

        sims = cosine_similarity(
            tfidf[i],
            tfidf[keep_indices]
        )[0]

        if sims.max() < SIM_THRESHOLD:
            keep_indices.append(i)

    return [ideas[i] for i in keep_indices]

def main():
    # Determine today's run date
    run_date = date.today().isoformat()

    # Use run-specific directory structure
    input_dir = Path("data") / "runs" / run_date / "raw"
    output_dir = Path("data") / "runs" / run_date / "normalized"

    if not input_dir.exists():
        print(f"No input directory found: {input_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    ideas = load_ideas(input_dir)
    deduped = dedup(ideas)

    # Write to output directory as individual JSON files
    for idx, idea in enumerate(deduped, start=1):
        out_file = output_dir / f"idea_{idx:04d}.json"
        with open(out_file, "w") as f:
            json.dump({"idea_text": idea}, f, ensure_ascii=False, indent=2)

    print(f"✅ Normalized and deduped {len(deduped)} ideas to {output_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
