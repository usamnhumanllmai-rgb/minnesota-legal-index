import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OUTPUT = Path("output")
HISTORY_FILE = OUTPUT / "change_history.jsonl"
FAILURE_FILE = OUTPUT / "failures.jsonl"

RETRY_STRATEGY = Retry(
    total=5,
    connect=5,
    read=5,
    status=5,
    backoff_factor=2,
    status_forcelist=[408, 429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    respect_retry_after_header=True,
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "MN-Legal-Index-Pipeline/1.0"})
SESSION.mount("https://", HTTPAdapter(max_retries=RETRY_STRATEGY))
SESSION.mount("http://", HTTPAdapter(max_retries=RETRY_STRATEGY))


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_output():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    return OUTPUT


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path):
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def log_event(event_type, url=None, message="", details=None):
    row = {
        "timestamp": utc_now(),
        "event_type": event_type,
        "url": url,
        "message": message,
        "details": details or {},
    }
    append_jsonl(HISTORY_FILE, row)
    return row


def log_failure(url, stage, error, details=None):
    row = {
        "timestamp": utc_now(),
        "stage": stage,
        "url": url,
        "error": str(error),
        "details": details or {},
    }
    append_jsonl(FAILURE_FILE, row)
    return row


def fetch(url, stage="fetch"):
    try:
        response = SESSION.get(url, timeout=30)
        response.raise_for_status()
        log_event("fetch_success", url=url, message=f"HTTP {response.status_code}")
        return response.text

    except requests.RequestException as error:
        log_failure(url, stage, error)
        raise


def sleep_politely(seconds=1.0):
    time.sleep(seconds)


def slug_from_url(url):
    parsed = urlparse(url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    year = parse_qs(parsed.query).get("year", [""])[0]
    publication = "statutes" if "/index/statute/" in parsed.path else "rules"
    suffix = f"_{year}" if year else ""
    return f"{publication}_{slug}{suffix}"


def publication_from_url(url):
    if "/index/statute/" in url:
        return "Minnesota Statutes"
    if "/index/rule/" in url:
        return "Minnesota Rules"
    raise ValueError(f"Unknown Revisor publication: {url}")


def normalize_citation(citation):
    value = clean(citation)
    value = re.sub(
        r"^Minn\.\s*(?:Statutes|Rules)\s+",
        "",
        value,
        flags=re.I,
    )
    value = re.sub(r"^\d{4}\s+(?=\d)", "", value)
    return value



def build_url(publication, citation):
    normalized = normalize_citation(citation)
    section = normalized.split()[0] if normalized else ""

    if not section:
        return None

    if "statute" in publication.lower():
        return f"https://www.revisor.mn.gov/statutes/cite/{section}"

    if "rule" in publication.lower():
        return f"https://www.revisor.mn.gov/rules/cite/{section}"

    return None
