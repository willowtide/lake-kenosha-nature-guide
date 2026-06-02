#!/usr/bin/env python3
"""
Main event scraper — runs all source modules and writes data/events.json.
Run from the repo root: python .github/scripts/scraper.py
"""
import json
import logging
import sys
import os
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure sources package is importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent))

from sources import lcfpd, illinois_dnr, kenosha_parks, libraries, kenosha_library, wisconsin_dnr, visit_lake

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scraper")

OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "events.json"

SOURCES = [
    ("LCFPD",            lcfpd.scrape),
    ("IL DNR",           illinois_dnr.scrape),
    ("Kenosha Parks",    kenosha_parks.scrape),
    ("Libraries",        libraries.scrape),
    ("Kenosha Library",  kenosha_library.scrape),
    ("WI DNR",           wisconsin_dnr.scrape),
    ("Visit Lake County",visit_lake.scrape),
]


def run_all():
    all_events = []
    errors = []

    logger.info(f"Starting scrape of {len(SOURCES)} sources…")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): name for name, fn in SOURCES}
        for future in as_completed(futures):
            name = futures[future]
            try:
                events = future.result()
                logger.info(f"  ✓ {name}: {len(events)} events")
                all_events.extend(events)
            except Exception as e:
                logger.error(f"  ✗ {name}: {e}")
                errors.append(name)

    logger.info(f"Raw total: {len(all_events)} events from {len(SOURCES) - len(errors)} sources")

    # Deduplicate by ID (keep first occurrence)
    seen = set()
    unique = []
    for ev in all_events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            unique.append(ev)

    # Drop past events
    today = date.today().isoformat()
    future_events = [e for e in unique if e.get("date", "") >= today]

    # Sort by date ascending
    future_events.sort(key=lambda e: e.get("date", ""))

    logger.info(f"After dedup + filter: {len(future_events)} upcoming events")

    return future_events, errors


def load_existing():
    """Load existing events.json so we can merge (preserving manual entries)."""
    if OUTPUT_PATH.exists():
        try:
            with open(OUTPUT_PATH) as f:
                data = json.load(f)
            return data.get("events", [])
        except Exception:
            pass
    return []


def merge(existing, scraped):
    """
    Merge scraped events with existing.
    - Scraped events overwrite existing ones with the same ID.
    - Existing events with no matching scraped ID are kept if they're future events
      AND have a source_url (manual entries have empty source_url or are from known sources).
    """
    today = date.today().isoformat()
    scraped_ids = {e["id"] for e in scraped}

    # Keep existing manual entries (those not replaced by scraper)
    manual = [
        e for e in existing
        if e["id"] not in scraped_ids and e.get("date", "") >= today
    ]

    merged = scraped + manual
    merged.sort(key=lambda e: e.get("date", ""))
    return merged


def main():
    scraped, errors = run_all()
    existing = load_existing()
    merged = merge(existing, scraped)

    output = {
        "scraped_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event_count": len(merged),
        "errors": errors,
        "events": merged,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(merged)} events to {OUTPUT_PATH}")

    if errors:
        logger.warning(f"Sources with errors: {', '.join(errors)}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
