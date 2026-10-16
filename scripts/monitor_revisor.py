#!/usr/bin/env python3
import json
from pathlib import Path

from common import (
    fetch,
    sha256,
    ensure_output,
    log_event,
    log_failure,
    utc_now,
)

URLS = [
    "https://www.revisor.mn.gov/index/",
    "https://www.revisor.mn.gov/index/statute/",
    "https://www.revisor.mn.gov/index/rule/",
]

STATE_FILE = Path("output/revisor_fingerprints.json")
ALERT_FILE = Path("output/revisor_release_alert.json")


def main():
    ensure_output()

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    changes = []
    errors = []

    for url in URLS:
        try:
            digest = sha256(fetch(url, stage="monitor"))
        except Exception as error:
            errors.append({
                "url": url,
                "error": str(error),
            })
            continue

        previous = state.get(url)
        changed = bool(previous and previous != digest)

        log_event(
            "monitor_check",
            url=url,
            message="changed" if changed else "unchanged",
            details={
                "previous_hash": previous,
                "new_hash": digest,
            },
        )

        if changed:
            changes.append({
                "url": url,
                "previous_hash": previous,
                "new_hash": digest,
            })

        state[url] = digest

    STATE_FILE.write_text(json.dumps(state, indent=2))

    alert = {
        "alert": bool(changes),
        "checked_at": utc_now(),
        "changes": changes,
        "errors": errors,
        "site_available": not errors,
    }

    ALERT_FILE.write_text(json.dumps(alert, indent=2))
    print(json.dumps(alert, indent=2))

    if changes:
        log_event(
            "release_change_detected",
            message=f"{len(changes)} Revisor index source(s) changed",
            details={"changes": changes},
        )
        raise SystemExit(10)

    if errors:
        raise SystemExit(20)


if __name__ == "__main__":
    main()
