#!/usr/bin/env python3
import json
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import fetch, ensure_output, log_event, log_failure

START_URLS = [
    "https://www.revisor.mn.gov/index/statute/",
    "https://www.revisor.mn.gov/index/rule/",
]

LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

QUEUE_FILE = Path("output/crawl_queue.json")
URL_FILE = Path("output/topic_urls.jsonl")
BATCH_LIMIT = 10


def get_links(url):
    soup = BeautifulSoup(fetch(url, stage="crawl"), "html.parser")
    links = set()

    for anchor in soup.select("a[href]"):
        absolute = urljoin(url, anchor.get("href", "")).split("#")[0]

        if "/index/statute/topic/" in absolute:
            links.add(absolute)

        if "/index/rule/topic/" in absolute:
            links.add(absolute)

    return links


def seed_letter_pages():
    statute_letters = [
        f"https://www.revisor.mn.gov/index/statute/topics/{letter}?year=2025&year2=2025"
        for letter in LETTERS
    ]

    rules_letters = [
        f"https://www.revisor.mn.gov/index/rule/topics/{letter}"
        for letter in LETTERS
    ]

    return statute_letters + rules_letters


def main():
    ensure_output()

    state = {
        "visited": [],
        "queue": START_URLS + seed_letter_pages(),
    }

    visited = set(state["visited"])
    queue = list(dict.fromkeys(state["queue"]))
    processed = 0
    failed = 0

    with URL_FILE.open("a", encoding="utf-8") as out:
        while queue and processed < BATCH_LIMIT:
            url = queue.pop(0)

            if url in visited:
                continue

            print(f"Crawling: {url}")

            try:
                links = get_links(url)

                for link in sorted(links - visited):
                    if link not in queue:
                        queue.append(link)
                        out.write(json.dumps({"url": link}) + "\n")
                        out.flush()

                visited.add(url)
                processed += 1
                log_event(
                    "crawl_success",
                    url=url,
                    message=f"Discovered {len(links)} topic links",
                )

            except Exception as error:
                failed += 1
                log_failure(url, "crawl", error)
                print(f"Failed: {url}: {error}")

            QUEUE_FILE.write_text(json.dumps({
                "visited": sorted(visited),
                "queue": queue,
            }, indent=2))

    print(f"Processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Remaining queue: {len(queue)}")

    if failed:
        raise SystemExit(30)


if __name__ == "__main__":
    main()
