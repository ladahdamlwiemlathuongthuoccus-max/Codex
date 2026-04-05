from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "mc_cid", "mc_eid", "source", "via",
}


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    hostname = parsed.hostname or ""
    hostname = hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]

    # Reddit normalization
    hostname = hostname.replace("old.reddit.com", "reddit.com")
    hostname = hostname.replace("new.reddit.com", "reddit.com")

    # Strip tracking params
    params = parse_qs(parsed.query, keep_blank_values=False)
    clean_params = {
        k: v for k, v in params.items()
        if k.lower() not in TRACKING_PARAMS
    }
    clean_query = urlencode(clean_params, doseq=True)

    # Remove trailing slash
    path = parsed.path.rstrip("/")

    # Remove fragment
    normalized = urlunparse((
        "https",
        hostname,
        path,
        "",
        clean_query,
        "",
    ))

    return normalized


def compute_content_hash(title: str, content: str) -> str:
    text = f"{title.lower().strip()}|{content[:500].lower().strip()}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def jaccard_similarity(title_a: str, title_b: str) -> float:
    words_a = set(_tokenize(title_a))
    words_b = set(_tokenize(title_b))

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [w for w in text.split() if len(w) > 2]
