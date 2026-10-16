#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

from common import ensure_output

JSONL = Path("output/minnesota_legal_index.jsonl")
DB = Path("output/legal_index.db")


def main():
    ensure_output()

    if DB.exists():
        DB.unlink()

    connection = sqlite3.connect(DB)

    connection.executescript("""
    CREATE VIRTUAL TABLE entries USING fts5(
        publication,
        topic,
        subtopic_path,
        reference_type,
        reference,
        normalized_reference,
        url,
        source_url,
        cross_reference_topic,
        raw_text,
        tokenize = 'porter unicode61'
    );
    """)

    count = 0

    with JSONL.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            connection.execute(
                """INSERT INTO entries
                   (publication, topic, subtopic_path, reference_type, reference,
                    normalized_reference, url, source_url, cross_reference_topic, raw_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row.get("publication"), row.get("topic"), row.get("subtopic_path"),
                    row.get("reference_type"), row.get("reference"),
                    row.get("normalized_reference"), row.get("url"), row.get("source_url"),
                    row.get("cross_reference_topic"), row.get("raw_text"),
                ),
            )
            count += 1

    connection.commit()
    connection.close()
    print(f"Indexed {count} records into {DB}")


if __name__ == "__main__":
    main()
