"""Kenosha County Parks event calendar scraper."""
import logging
from dateutil import parser as dp
from .utils import get, slug, normalize_cost, clean_text

logger = logging.getLogger(__name__)
SOURCE = "Kenosha County Parks"
BASE   = "https://www.kenoshacounty.org"


def scrape():
    events = []
    url = f"{BASE}/calendar.aspx?CID=17"  # Parks & Recreation calendar
    try:
        soup = get(url)
        if soup is None:
            return events

        items = soup.select(".fc-event, .calendar-item, .event-item, tr.listItem")
        # Fallback: look for event links on the page
        if not items:
            items = soup.select("a[href*='event'], a[href*='calendar']")
        logger.info(f"Kenosha Parks: found {len(items)} items")

        for item in items:
            try:
                ev = _parse_item(item)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"Kenosha Parks parse error: {e}")
    except Exception as e:
        logger.warning(f"Kenosha Parks scrape failed: {e}")
    return events


def _parse_item(item):
    title_el = item.select_one("a, .fc-title, .event-title, td.title")
    if not title_el:
        title_text = clean_text(item.get_text())
        if not title_text:
            return None
        title = title_text[:80]
        link  = ""
    else:
        title = clean_text(title_el.get_text())
        link  = title_el.get("href", "")
        if link and not link.startswith("http"):
            link = BASE + link

    date_el = item.select_one("time, .fc-time, .event-date, td.date")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())

    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    desc_el = item.select_one(".event-description, .fc-description, td.description")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link or f"{BASE}/calendar.aspx",
        "date":                 parsed_date,
        "time":                 "",
        "end_time":             "",
        "location_name":        "Kenosha County Parks",
        "address":              "",
        "county":               "kenosha-wi",
        "cost":                 "free",
        "cost_detail":          "",
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
    if any(w in text for w in ["natur", "wildlife", "bird"]): cats.append("nature")
    if any(w in text for w in ["scienc", "stem"]): cats.append("science")
    if any(w in text for w in ["fish"]): cats.append("fishing")
    if not cats:
        cats.append("nature")
    return cats
