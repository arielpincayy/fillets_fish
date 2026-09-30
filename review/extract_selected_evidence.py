#!/usr/bin/env python3
"""Build a compact, auditable evidence file from OpenAlex JSONL results."""

import json
from pathlib import Path


def reconstruct_abstract(index):
    if not index:
        return ""
    words = {}
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(words[position] for position in sorted(words))


source = Path("sources/openalex_selected.jsonl")
target = Path("review/selected_evidence.json")
records = []

for line in source.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    payload = json.loads(line)
    for item in payload.get("results", [])[:1]:
        location = item.get("primary_location") or {}
        journal = (location.get("source") or {}).get("display_name", "")
        authors = [
            (authorship.get("author") or {}).get("display_name", "")
            for authorship in item.get("authorships", [])
        ]
        records.append(
            {
                "doi": (item.get("doi") or "").removeprefix("https://doi.org/"),
                "title": item.get("title", ""),
                "year": item.get("publication_year"),
                "publication_date": item.get("publication_date"),
                "journal": journal,
                "authors": authors,
                "abstract": reconstruct_abstract(item.get("abstract_inverted_index")),
                "cited_by_count": item.get("cited_by_count"),
                "type": item.get("type"),
                "is_retracted": item.get("is_retracted"),
                "open_access": item.get("open_access", {}),
                "openalex_id": item.get("id"),
            }
        )

target.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(records)} evidence records to {target}")
print(f"Records with abstracts: {sum(bool(r['abstract']) for r in records)}")
