#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

from common import (
    slug_from_url,
    publication_from_url,
    ensure_output,
    log_event,
    log_failure,
)

URL_FILE = Path("output/topic_urls.jsonl")
TOPIC_DIR = Path("output/topics")
FAILED_FILE = Path("output/failed_topics.jsonl")


def main():
    ensure_output()
    TOPIC_DIR.mkdir(parents=True, exist_ok=True)

    if not URL_FILE.exists():
        raise SystemExit(f"Missing {URL_FILE}. Run crawl_revisor_topics.py first.")

    processed = 0
    failed = 0

    with URL_FILE.open(encoding="utf-8") as source, FAILED_FILE.open("w", encoding="utf-8") as errors:
        for line in source:
            url = json.loads(line)["url"]
            slug = slug_from_url(url)
            output = TOPIC_DIR / slug
            publication = publication_from_url(url)

            command = [
                sys.executable,
                "scripts/parse_revisor_topic.py",
                "--url", url,
                "--publication", publication,
                "--out", str(output),
            ]

            result = subprocess.run(command, capture_output=True, text=True)
            processed += 1

            if result.returncode == 0:
                log_event("parse_success", url=url, message=f"Wrote {output}")
                continue

            failed += 1
            log_failure(url, "parse", result.stderr.strip())
            errors.write(json.dumps({
                "url": url,
                "returncode": result.returncode,
                "error": result.stderr.strip(),
            }) + "\n")
            errors.flush()

    print(f"Processed: {processed}")
    print(f"Failed: {failed}")

    if failed:
        raise SystemExit(31)


if __name__ == "__main__":
    main()
