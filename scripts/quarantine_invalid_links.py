#!/usr/bin/env python3
import csv
import json
from pathlib import Path

from common import ensure_output

ensure_output()

failures_path = Path("output/link_failures.csv")
source_path = Path("output/minnesota_legal_index.jsonl")
clean_path = Path("output/minnesota_legal_index_clean.jsonl")
quarantine_path = Path("output/quarantine/minnesota_legal_index_quarantined.jsonl")

quarantine_path.parent.mkdir(parents=True, exist_ok=True)

with failures_path.open(newline="", encoding="utf-8") as handle:
    invalid_urls = {
        row["url"].strip()
        for row in csv.DictReader(handle)
        if row.get("url")
    }

if not invalid_urls:
    raise SystemExit("STOP: No invalid URLs found in link_failures.csv.")

kept = 0
quarantined = 0

with source_path.open(encoding="utf-8") as source:
    with clean_path.open("w", encoding="utf-8") as clean_out:
        with quarantine_path.open("w", encoding="utf-8") as quarantine_out:
            for line in source:
                if not line.strip():
                    continue

                row = json.loads(line)
                url = row.get("url")

                if url and url.strip() in invalid_urls:
                    quarantine_out.write(
                        json.dumps(row, ensure_ascii=False) + "\n"
                    )
                    quarantined += 1
                else:
                    clean_out.write(
                        json.dumps(row, ensure_ascii=False) + "\n"
                    )
                    kept += 1

print(f"Valid records retained: {kept}")
print(f"Invalid-link records quarantined: {quarantined}")
print(f"Invalid unique URLs: {len(invalid_urls)}")

if quarantined == 0:
    raise SystemExit(
        "STOP: No records matched the invalid URLs; investigate before rebuilding."
    )
