"""Lake County library event calendar scrapers.

Most Lake County libraries use either Evanced Solutions or LibCal (Springshare).
This module handles both CMS types with a unified normalizer.
"""
import logging
from dateutil import parser as dp
from .utils import get, get_json, slug, normalize_cost, clean_text

logger = logging.getLogger(__name__)

# Library definitions: (name, county, calendar_url, cms_type)
LIBRARIES = [
    ("Grayslake Area Public Library",    "lake-il",  "https://www.grayslake.info/events/",           "generic"),
    ("Warren-Newport Public Library",    "lake-il",  "https://www.wnpl.info/events/",                 "generic"),
    ("Fox Lake District Public Library", "lake-il",  "https://www.foxlake.lib.il.us/events/",         "generic"),
    ("Lake Villa District Public Library","lake-il", "https://www.lvdl.org/events/",                  "generic"),
    ("Antioch Public Library",           "lake-il",  "https://www.antioch.lib.il.us/events/",         "generic"),
    ("Round Lake Area Public Library",   "lake-il",  "https://www.rlapl.org/events/",                 "generic"),
    ("Cook Memorial Public Library",     "lake-il",  "https://www.cooklib.org/events/",               "generic"),
    ("Wauconda Area Public Library",     "lake-il",  "https://www.wauclib.org/events/",               "generic"),
]

NATURE_KEYWORDS = [
    "nature", "outdoor", "wildlife", "bird", "plant", "garden", "hike", "trail",
    "animal", "insect", "bug", "reptile", "amphibian", "fish", "ecology", "science",
    "stem", "environment", "earth", "weather", "experiment", "natural", "forest",
    "prairie", "wetland", "lake", "river", "creek", "park", "craft", "art",
    "maker", "engineer", "astronomy", "space", "dinosaur", "fossil",
]


def scrape():
    events = []
    for name, county, url, cms in LIBRARIES:
        try:
            lib_events = _scrape_library(name, county, url, cms)
            logger.info(f"{name}: {len(lib_events)} events")
            events.extend(lib_events)
        except Exception as e:
            logger.warning(f"{name} failed: {e}")
    return events


def _scrape_library(name, county, url, cms):
    soup = get(url)
    if soup is None:
        return []

    events = []
    # Try multiple selectors — library sites vary widely
    selectors = [
        ".tribe-events-loop .tribe-events-loop__event",
        "article.type-tribe_events",
        ".event-listing",
        ".event-item",
        ".views-row",
        "li.event",
        ".program-item",
        ".cal-event",
        "article",
    ]

    items = []
    for sel in selectors:
        items = soup.select(sel)
        if len(items) >= 2:
            break

    for item in items[:50]:  # cap per library
        try:
            ev = _parse_generic(item, name, county, url)
            if ev:
                events.append(ev)
        except Exception as e:
            logger.debug(f"{name} item parse error: {e}")

    return events


def _parse_generic(item, source, county, base_url):
    # Title
    title_el = item.select_one("h2 a, h3 a, h4 a, .event-title a, .tribe-event-url, a.event-title, .program-title a")
    if not title_el:
        title_el = item.select_one("h2, h3, h4, .event-title, .program-title")
    if not title_el:
        return None
    title = clean_text(title_el.get_text())
    if not title or len(title) < 4:
        return None

    # Filter to nature/science/outdoor topics
    title_lower = title.lower()
    if not any(kw in title_lower for kw in NATURE_KEYWORDS):
        return None

    link = ""
    link_el = item.select_one("a")
    if link_el:
        link = link_el.get("href", "")
        if link and not link.startswith("http"):
            from urllib.parse import urljoin
            link = urljoin(base_url, link)

    # Date
    date_el = item.select_one("time, .event-date, .date, .tribe-event-date-start, .program-date")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    # Time
    time_el = item.select_one(".event-time, .time, .tribe-events-schedule__datetime")
    time_str = clean_text(time_el.get_text()) if time_el else ""

    # Description
    desc_el = item.select_one(".event-description, .description, .tribe-excerpt, p")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    # Cost
    cost_el = item.select_one(".event-cost, .cost, .tribe-events-cost")
    cost, cost_detail = normalize_cost(clean_text(cost_el.get_text()) if cost_el else "")

    # Registration
    reg = bool(item.select_one("a[href*='register'], a[href*='signup'], .register"))
    reg_url = ""
    if reg:
        reg_el = item.select_one("a[href*='register'], a[href*='signup']")
        reg_url = reg_el.get("href", "") if reg_el else link

    return {
        "id":                   slug(source, parsed_date, title),
        "title":                title,
        "source":               source,
        "source_url":           link or base_url,
        "date":                 parsed_date,
        "time":                 time_str,
        "end_time":             "",
        "location_name":        source,
        "address":              "",
        "county":               county,
        "cost":                 cost,
        "cost_detail":          cost_detail,
        "ages":                 "all",
        "categories":           _guess_categories(title, desc),
        "description":          desc[:400],
        "registration_required": reg,
        "registration_url":     reg_url,
    }


def _parse_date(s):
    try:
        return dp.parse(s.strip()).strftime("%Y-%m-%d")
    except Exception:
        return None


def _guess_categories(title, desc):
    text = (title + " " + desc).lower()
    cats = []
    if any(w in text for w in ["natur", "wildlife", "bird", "plant", "pollinator", "wildflower", "ecology", "outdoor"]): cats.append("nature")
    if any(w in text for w in ["hike", "trail", "walk"]): cats.append("hiking")
    if any(w in text for w in ["scienc", "stem", "lab", "experiment", "engineer", "robot", "code"]): cats.append("science")
    if any(w in text for w in ["art", "craft", "draw", "paint", "creat", "make", "build"]): cats.append("art")
    if any(w in text for w in ["fish"]): cats.append("fishing")
    if not cats:
        cats.append("library")
    else:
        cats.append("library")
    return list(dict.fromkeys(cats))  # deduplicate preserving order
