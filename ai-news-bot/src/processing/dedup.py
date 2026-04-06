from __future__ import annotations

import hashlib
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
