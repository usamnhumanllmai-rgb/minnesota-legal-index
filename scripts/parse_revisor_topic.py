#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from common import fetch, clean, build_url, ensure_output

STATUTE_RE = re.compile(
    r"Minn\.\s*Statutes(?:\s+\d{4})?\s+[0-9]+(?:\.[0-9]+)?(?:\s+subd\.\s+\d+)?",
    re.I,
)

RULE_RE = re.compile(
    r"Minn\.\s*Rules(?:\s+\d{4})?\s+[0-9]+(?:\.[0-9]+)?",
    re.I,
)

SEE_RE = re.compile(
    r"\bsee(?:\s+also)?\s+(.+)$",
    re.I,
)


def normalize_cross_reference(value: str) -> str:
    value = clean(value)
    value = re.sub(r"^(?:also\s+|under\s+)", "", value, flags=re.I)
    return value.upper()




def derive_topic(url: str, soup: BeautifulSoup) -> str:
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]

    if "/topic/" not in parsed.path:
        heading = soup.find("h1")
        if heading:
            return clean(heading.get_text(" ", strip=True)).upper()

        return slug.replace("_", " ").upper()

    return slug.replace("_", " ").upper()



def ancestor_path(node) -> str:
    parts = []

    parent = node.parent
    while parent:
        if parent.name == "li":
            own_text = clean(parent.find(string=True, recursive=False) or "")
            if own_text:
                parts.append(own_text)
        parent = parent.parent

    parts.reverse()
    return " > ".join(parts)


def extract_rows(soup: BeautifulSoup, url: str, publication: str, topic: str):
    rows = []
    seen = set()

    nodes = soup.select("main li, main p, article li, article p, #content li, #content p")

    for node in nodes:
        text = clean(node.get_text(" ", strip=True))

        if not text or text in seen:
            continue

        seen.add(text)
        path = ancestor_path(node)

        citation_match = STATUTE_RE.search(text) or RULE_RE.search(text)
        see_match = SEE_RE.search(text)

        if citation_match:
            citation = clean(citation_match.group(0))
            rows.append({
                "publication": publication,
                "topic": topic,
                "subtopic_path": path,
                "reference_type": "citation",
                "reference": citation,
                "normalized_reference": build_url(publication, citation).split("/")[-1] if build_url(publication, citation) else "",
                "url": build_url(publication, citation),
                "source_url": url,
                "cross_reference_topic": None,
                "raw_text": text,
            })

        elif see_match:
            target = normalize_cross_reference(see_match.group(1))
            rows.append({
                "publication": publication,
                "topic": topic,
                "subtopic_path": path,
                "reference_type": "see_topic",
                "reference": f"see {target}",
                "normalized_reference": target.upper(),
                "url": None,
                "source_url": url,
                "cross_reference_topic": target.upper(),
                "raw_text": text,
            })

    return rows


def write_outputs(rows, basename: str):
    ensure_output()
    json_path = Path(f"{basename}.json")
    csv_path = Path(f"{basename}.csv")

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)

    fields = [
        "publication", "topic", "subtopic_path", "reference_type",
        "reference", "normalized_reference", "url", "source_url",
        "cross_reference_topic", "raw_text",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--publication", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    html = fetch(args.url)
    soup = BeautifulSoup(html, "html.parser")
    topic = derive_topic(args.url, soup)
    rows = extract_rows(soup, args.url, args.publication, topic)

    if not rows:
        print(f"No citations or cross-references found: {args.url}", file=sys.stderr)
        sys.exit(2)

    write_outputs(rows, args.out)
    print(f"Wrote {len(rows)} records: {args.out}.json")


if __name__ == "__main__":
    main()
