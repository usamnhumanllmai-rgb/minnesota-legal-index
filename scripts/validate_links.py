#!/usr/bin/env python3
import csv
import json
from pathlib import Path

import requests

from common import SESSION, read_jsonl, ensure_output

INPUT = Path("output/minnesota_legal_index.jsonl")
OUTPUT = Path("output/link_validation.csv")


def check(url: str):
    try:
        response = SESSION.head(url, allow_redirects=True, timeout=20)

        if response.status_code >= 400:
            response = SESSION.get(url, allow_redirects=True, timeout=30)

        return {
            "url": url,
            "status": response.status_code,
            "final_url": response.url,
            "valid": response.status_code < 400,
            "redirected": response.url.rstrip("/") != url.rstrip("/"),
            "error": "",
        }

    except requests.RequestException as error:
        return {
            "url": url,
            "status": None,
            "final_url": None,
            "valid": False,
            "redirected": False,
            "error": str(error),
        }


def main():
    ensure_output()
    urls = sorted({
        row["url"]
        for row in read_jsonl(INPUT)
        if row.get("url")
    })

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["url", "status", "final_url", "valid", "redirected", "error"],
        )
        writer.writeheader()

        for url in urls:
            result = check(url)
            writer.writerow(result)
            handle.flush()
            print(f"{result['status']}: {url}")

    print(f"Validated {len(urls)} URLs: {OUTPUT}")


if __name__ == "__main__":
    main()
