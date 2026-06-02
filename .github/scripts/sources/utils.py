"""Shared utilities for all scrapers."""
import re
import hashlib
import logging
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "HomeschoolNatureGuide/1.0 (educational resource aggregator; not for commercial use)"
})


def get(url, timeout=15, retries=2):
    """Fetch URL and return BeautifulSoup, or None on failure."""
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=timeout)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"GET failed {url}: {e}")
                return None


def get_json(url, timeout=15):
    """Fetch URL and return parsed JSON, or None on failure."""
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"GET JSON failed {url}: {e}")
        return None


def slug(source, date, title):
    """Generate a stable event ID."""
    raw = f"{source}-{date}-{title}".lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    # Truncate and add hash suffix for uniqueness
    short = raw[:60]
    suffix = hashlib.md5(raw.encode()).hexdigest()[:6]
    return f"{short}-{suffix}"


def normalize_cost(raw):
    """Return (cost, cost_detail) tuple from a raw cost string."""
    if not raw:
        return "free", ""
    low = raw.lower().strip()
    if not low or low in ("free", "$0", "no cost", "no charge", "complimentary"):
        return "free", ""
    if "$" in low or "fee" in low or "admission" in low or "register" in low:
        return "paid", raw.strip()
    if re.search(r"\d", low):
        return "paid", raw.strip()
    return "free", ""


def clean_text(s):
    """Strip extra whitespace from a string."""
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()
