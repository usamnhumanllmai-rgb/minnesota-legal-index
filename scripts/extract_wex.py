#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import fetch, clean, ensure_output

USC_RE = re.compile(r"\b(\d{1,3})\s+U\.S\.C\.(?:\s+§+\s*([0-9]+))?", re.I)
CFR_RE = re.compile(r"\b(\d{1,3})\s+C\.F\.R\.(?:\s+§+\s*([0-9]+(?:\.[0-9]+)?))?", re.I)
UCC_RE = re.compile(r"\bUCC\s+Article\s+([0-9]+)", re.I)


def classify(text: str):
    if USC_RE.search(text):
        return "usc"
    if CFR_RE.search(text):
        return "cfr"
    if UCC_RE.search(text):
        return "uniform_law"
    if re.search(r"\bMinn\.\s*Stat", text, re.I):
        return "minnesota_statute"
    if re.search(r"\bMinn\.\s*R\.?", text, re.I):
        return "minnesota_rule"
    return "secondary_source"


def resolve_url(authority_type: str, text: str):
    if authority_type == "usc":
        match = USC_RE.search(text)
        title = match.group(1)
        section = match.group(2)
        return f"https://www.law.cornell.edu/uscode/text/{title}" + (f"/{section}" if section else "")

    if authority_type == "cfr":
        match = CFR_RE.search(text)
        title = match.group(1)
        part = match.group(2)
        return f"https://www.law.cornell.edu/cfr/text/{title}" + (f"/{part}" if part else "")

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--concept", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    html = fetch(args.url)
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    seen = set()

    for anchor in soup.select("a[href]"):
        text = clean(anchor.get_text(" ", strip=True))
        href = urljoin(args.url, anchor.get("href", ""))

        if not text or (text, href) in seen:
            continue

        seen.add((text, href))
        authority_type = classify(text)

        rows.append({
            "concept": args.concept,
            "concept_source": "Cornell Wex",
            "source_url": args.url,
            "authority_type": authority_type,
            "jurisdiction": "United States" if authority_type in {"usc", "cfr"} else "unspecified",
            "authority_name": text,
            "citation": text,
            "normalized_citation": text,
            "source_hyperlink": href,
            "resolved_url": resolve_url(authority_type, text),
            "context": clean(anchor.find_parent().get_text(" ", strip=True)) if anchor.parent else "",
            "match_status": "explicit",
        })

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(rows)} Wex authority records: {output}")


if __name__ == "__main__":
    main()
