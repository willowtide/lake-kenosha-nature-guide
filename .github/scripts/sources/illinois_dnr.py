"""Illinois DNR events calendar scraper."""
import logging
import re
from datetime import datetime
from .utils import get, slug, normalize_cost, clean_text
from dateutil import parser as dp

logger = logging.getLogger(__name__)
SOURCE = "Illinois DNR"
BASE   = "https://dnr.illinois.gov"


def scrape():
    events = []
    # IL DNR events calendar — filter to Lake County region
    url = f"{BASE}/education/events.html"
    try:
        soup = get(url)
        if soup is None:
            return events

        # DNR events page uses a table or list format
        rows = soup.select("table.views-table tbody tr, .view-content .views-row")
        logger.info(f"IL DNR: found {len(rows)} rows")

        for row in rows:
            try:
                ev = _parse_row(row)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"IL DNR row parse error: {e}")
    except Exception as e:
        logger.warning(f"IL DNR scrape failed: {e}")
    return events


def _parse_row(row):
    # Title / link
    title_el = row.select_one("td.views-field-title a, .views-field-title a, h3 a, h2 a")
    if not title_el:
        return None
    title = clean_text(title_el.get_text())
    link  = title_el.get("href", "")
    if link and not link.startswith("http"):
        link = BASE + link

    # Date
    date_el = row.select_one(".date-display-single, .views-field-field-event-date, time")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or clean_text(date_el.get_text())
    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    # Location — filter to IL Beach State Park or Lake County locations
    loc_el = row.select_one(".views-field-field-location, .views-field-field-park")
    loc = clean_text(loc_el.get_text()) if loc_el else ""

    # Only keep events in Lake County area
    lake_county_keywords = [
        "lake county", "zion", "waukegan", "libertyville", "gurnee", "wauconda",
        "grayslake", "antioch", "illinois beach", "chain o' lakes", "chain o lakes",
        "des plaines", "ryerson", "independence grove", "lakewood"
    ]
    loc_lower = loc.lower()
    if loc and not any(kw in loc_lower for kw in lake_county_keywords):
        return None  # Skip non-Lake-County events

    desc_el = row.select_one(".views-field-body, .field-content p")
    desc = clean_text(desc_el.get_text()) if desc_el else ""

    cost_el = row.select_one(".views-field-field-cost, .field-cost")
    cost, cost_detail = normalize_cost(clean_text(cost_el.get_text()) if cost_el else "")

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link,
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
    s = s.strip()
    try:
        return dp.parse(s).strftime("%Y-%m-%d")
    except Exception:
        return None


def _guess_categories(title, desc):
    text = (title + " " + desc).lower()
    cats = []
    if any(w in text for w in ["hike", "trail", "walk"]): cats.append("hiking")
    if any(w in text for w in ["natur", "wildlife", "bird", "plant"]): cats.append("nature")
    if any(w in text for w in ["fish"]): cats.append("fishing")
    if any(w in text for w in ["scienc", "stem"]): cats.append("science")
    if not cats:
        cats.append("nature")
    return cats
