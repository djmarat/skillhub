"""enrich_tags.py — add free-form tags from skill name + description.

Cheap, no LLM. Tokenizes description, picks tokens that occur > 1× across
the corpus OR appear in name, lower-cases, dedups, caps at 5 tags per skill.

Idempotent: skips records that already have non-empty tags.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "registry" / "skills.jsonl"

STOPWORDS = {
    "the", "a", "an", "of", "to", "for", "with", "and", "or", "in", "on",
    "from", "by", "is", "are", "be", "as", "at", "this", "that", "you",
    "your", "it", "its", "we", "our", "use", "using", "via", "any", "all",
    "can", "or", "no", "not", "into", "out", "more", "most", "than",
}

TOKEN = re.compile(r"[a-z][a-z0-9-]{2,}")


def _tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOPWORDS and len(t) > 2]


def _corpus_freq(records: list[dict]) -> Counter:
    c: Counter = Counter()
    for r in records:
        c.update(_tokenize(r.get("name", "") + " " + r.get("description", "")))
    return c


def _tags_for(record: dict, freq: Counter) -> list[str]:
    name = record.get("name", "").lower()
    desc = record.get("description", "")
    name_tokens = set(_tokenize(name.replace("-", " ")))
    tokens = _tokenize(desc)
    counts = Counter(tokens)
    seen: list[str] = []
    # First: tokens that appear in name (high signal)
    for t in name_tokens:
        if t not in seen and freq[t] >= 1:
            seen.append(t)
        if len(seen) >= 5:
            break
    # Then: top-frequency tokens in description
    for t, _ in counts.most_common(20):
        if t in seen:
            continue
        if freq[t] >= 2 or t in name_tokens:
            seen.append(t)
        if len(seen) >= 5:
            break
    return seen[:5]


def main() -> int:
    if not REGISTRY.exists():
        print("registry not found", file=sys.stderr)
        return 1
    records: list[dict] = []
    with REGISTRY.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    freq = _corpus_freq(records)
    enriched = 0
    skipped = 0
    for r in records:
        if r.get("tags"):
            skipped += 1
            continue
        tags = _tags_for(r, freq)
        if tags:
            r["tags"] = tags
            enriched += 1

    # Rewrite registry
    with REGISTRY.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"enriched: {enriched} | already had tags: {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
