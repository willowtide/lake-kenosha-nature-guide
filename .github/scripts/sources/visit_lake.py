"""Visit Lake County events aggregator scraper — visitlakecounty.org"""
import logging
from dateutil import parser as dp
from .utils import get, slug, normalize_cost, clean_text

logger = logging.getLogger(__name__)
SOURCE = "Visit Lake County"
BASE   = "https://www.visitlakecounty.org"

NATURE_KEYWORDS = [
    "nature", "outdoor", "wildlife", "bird", "hike", "trail", "walk", "park",
    "forest", "garden", "animal", "insect", "science", "ecology", "lake",
    "river", "beach", "paddl", "kayak", "canoe", "fish", "farm", "harvest",
    "festival", "fair", "family", "kids", "children",
]


def scrape():
    events = []
    url = f"{BASE}/events/"
    try:
        soup = get(url)
        if soup is None:
            return events

        items = soup.select("article, .event-item, .tribe-events-loop__event, .views-row")
        logger.info(f"Visit Lake County: found {len(items)} items")

        for item in items[:60]:
            try:
                ev = _parse_item(item, url)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"Visit Lake County parse error: {e}")
    except Exception as e:
        logger.warning(f"Visit Lake County scrape failed: {e}")
    return events


def _parse_item(item, base_url):
    title_el = item.select_one("h2 a, h3 a, .event-title a, .tribe-event-url")
    if not title_el:
        return None
    title = clean_text(title_el.get_text())
    if not title:
        return None

    # Filter to family/nature-relevant events
    if not any(kw in title.lower() for kw in NATURE_KEYWORDS):
        desc_el = item.select_one("p, .description, .excerpt")
        desc_text = clean_text(desc_el.get_text()).lower() if desc_el else ""
        if not any(kw in desc_text for kw in NATURE_KEYWORDS):
            return None

    link = title_el.get("href", "")
    if link and not link.startswith("http"):
        from urllib.parse import urljoin
        link = urljoin(base_url, link)

    date_el = item.select_one("time, .event-date, .tribe-event-date-start")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    loc_el = item.select_one(".venue, .location, .tribe-venue")
    loc = clean_text(loc_el.get_text()) if loc_el else ""

    desc_el = item.select_one("p, .description, .excerpt")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    cost_el = item.select_one(".cost, .tribe-events-cost")
    cost, cost_detail = normalize_cost(clean_text(cost_el.get_text()) if cost_el else "")

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link or base_url,
        "date":                 parsed_date,
        "time":                 "",
        "end_time":             "",
        "location_name":        loc,
        "address":              "",
        "county":               "lake-il",
        "cost":                 cost,
        "cost_detail":          cost_detail,
        "ages":                 "all",
        "categories":           _guess_categories(title, desc),
        "description":          desc[:400],
        "registration_required": False,
        "registration_url":     "",
    }


def _parse_date(s):
    try:
        return dp.parse(s.strip()).strftime("%Y-%m-%d")
    except Exception:
        return None


def _guess_categories(title, desc):
    text = (title + " " + desc).lower()
    cats = []
    if any(w in text for w in ["natur", "wildlife", "bird", "plant"]): cats.append("nature")
    if any(w in text for w in ["hike", "trail", "walk"]): cats.append("hiking")
    if any(w in text for w in ["festival", "fair", "fest"]): cats.append("festival")
    if any(w in text for w in ["farm", "harvest", "orchard", "pumpkin"]): cats.append("farm")
    if any(w in text for w in ["scienc", "stem"]): cats.append("science")
    if not cats:
        cats.append("nature")
    return cats
