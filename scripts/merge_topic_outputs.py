#!/usr/bin/env python3
import json
from pathlib import Path

from common import ensure_output

TOPIC_DIR = Path("output/topics")
MERGED_FILE = Path("output/minnesota_legal_index.jsonl")


def main():
    ensure_output()
    count = 0

    with MERGED_FILE.open("w", encoding="utf-8") as out:
        for path in sorted(TOPIC_DIR.glob("*.json")):
            rows = json.loads(path.read_text(encoding="utf-8"))

            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

    print(f"Merged {count} records into {MERGED_FILE}")


if __name__ == "__main__":
    main()
