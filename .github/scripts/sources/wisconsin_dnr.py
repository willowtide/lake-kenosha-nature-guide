"""Wisconsin DNR events calendar scraper — filter to Kenosha County area."""
import logging
from dateutil import parser as dp
from .utils import get, slug, normalize_cost, clean_text

logger = logging.getLogger(__name__)
SOURCE = "Wisconsin DNR"
BASE   = "https://dnr.wisconsin.gov"

KENOSHA_KEYWORDS = [
    "kenosha", "bristol", "pleasant prairie", "somers", "silver lake",
    "petrifying springs", "bong", "richard bong", "geneva lake",
    "kettle moraine", "pike lake",
]


def scrape():
    events = []
    url = f"{BASE}/topic/parks/activities/events"
    try:
        soup = get(url)
        if soup is None:
            return events

        items = soup.select(".event-item, .views-row, article, tr.event-row")
        logger.info(f"WI DNR: found {len(items)} items")

        for item in items[:60]:
            try:
                ev = _parse_item(item)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"WI DNR parse error: {e}")
    except Exception as e:
        logger.warning(f"WI DNR scrape failed: {e}")
    return events


def _parse_item(item):
    title_el = item.select_one("h2 a, h3 a, a.event-title, td.title a, a")
    if not title_el:
        return None
    title = clean_text(title_el.get_text())
    if not title:
        return None

    link = title_el.get("href", "")
    if link and not link.startswith("http"):
        link = BASE + link

    loc_el = item.select_one(".location, .views-field-field-location, td.location")
    loc = clean_text(loc_el.get_text()) if loc_el else ""

    # Only keep Kenosha-area events
    loc_lower = (loc + " " + title).lower()
    if not any(kw in loc_lower for kw in KENOSHA_KEYWORDS):
        return None

    date_el = item.select_one("time, .date, .event-date")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    desc_el = item.select_one(".description, p, .views-field-body")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    cost_el = item.select_one(".cost, .fee")
    cost, cost_detail = normalize_cost(clean_text(cost_el.get_text()) if cost_el else "")

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link,
        "date":                 parsed_date,
        "time":                 "",
        "end_time":             "",
        "location_name":        loc or "Kenosha County",
        "address":              "",
        "county":               "kenosha-wi",
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
    if any(w in text for w in ["hike", "trail", "walk"]): cats.append("hiking")
    if any(w in text for w in ["natur", "wildlife", "bird", "plant"]): cats.append("nature")
    if any(w in text for w in ["fish"]): cats.append("fishing")
    if not cats:
        cats.append("nature")
    return cats
