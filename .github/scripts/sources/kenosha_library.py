"""Kenosha Public Library event calendar scraper."""
import logging
from dateutil import parser as dp
from .utils import get, slug, normalize_cost, clean_text

logger = logging.getLogger(__name__)
SOURCE = "Kenosha Public Library"
BASE   = "https://www.kenoshalibrary.org"

NATURE_KEYWORDS = [
    "nature", "outdoor", "wildlife", "bird", "plant", "garden", "hike",
    "animal", "insect", "bug", "reptile", "science", "stem", "ecology",
    "environment", "earth", "weather", "experiment", "natural", "craft", "art",
    "maker", "astronomy", "dinosaur", "fossil",
]


def scrape():
    events = []
    url = f"{BASE}/events/"
    try:
        soup = get(url)
        if soup is None:
            return events

        items = soup.select("article, .event-item, .views-row, li.event")
        logger.info(f"Kenosha Library: found {len(items)} items")

        for item in items[:50]:
            try:
                ev = _parse_item(item, url)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"Kenosha Library parse error: {e}")
    except Exception as e:
        logger.warning(f"Kenosha Library scrape failed: {e}")
    return events


def _parse_item(item, base_url):
    title_el = item.select_one("h2 a, h3 a, h4 a, .event-title a, a")
    if not title_el:
        return None
    title = clean_text(title_el.get_text())
    if not title or len(title) < 4:
        return None
    if not any(kw in title.lower() for kw in NATURE_KEYWORDS):
        return None

    link = title_el.get("href", "")
    if link and not link.startswith("http"):
        from urllib.parse import urljoin
        link = urljoin(base_url, link)

    date_el = item.select_one("time, .event-date, .date")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    desc_el = item.select_one("p, .description, .excerpt")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link or base_url,
        "date":                 parsed_date,
        "time":                 "",
        "end_time":             "",
        "location_name":        SOURCE,
        "address":              "",
        "county":               "kenosha-wi",
        "cost":                 "free",
        "cost_detail":          "",
        "ages":                 "all",
        "categories":           ["library"],
        "description":          desc[:400],
        "registration_required": False,
        "registration_url":     "",
    }


def _parse_date(s):
    try:
        return dp.parse(s.strip()).strftime("%Y-%m-%d")
    except Exception:
        return None
