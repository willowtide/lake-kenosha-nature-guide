"""Lake County Forest Preserves event scraper — lcfpd.org"""
import re
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from .utils import get, slug, normalize_cost

logger = logging.getLogger(__name__)
SOURCE = "Lake County Forest Preserves"
BASE   = "https://www.lcfpd.org"


def scrape():
    events = []
    # LCFPD uses a WordPress events plugin — fetch the events list page
    url = f"{BASE}/events/"
    try:
        soup = get(url)
        if soup is None:
            return events
        # Each event is in an article.type-tribe_events or similar
        cards = soup.select("article.type-tribe_events, .tribe-events-calendar__grid-event, .tribe_events_cat")
        if not cards:
            # Fallback: look for event links in any list format
            cards = soup.select(".tribe-event, .tribe-events-loop .tribe-events-loop__event")
        logger.info(f"LCFPD: found {len(cards)} raw event elements")
        for card in cards:
            try:
                ev = _parse_card(card)
                if ev:
                    events.append(ev)
            except Exception as e:
                logger.debug(f"LCFPD card parse error: {e}")
    except Exception as e:
        logger.warning(f"LCFPD scrape failed: {e}")
    return events


def _parse_card(card):
    title_el = card.select_one(".tribe-event-url, .tribe-events-calendar__event-title a, h2 a, h3 a, .tribe-event-title a")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    link  = title_el.get("href", "")
    if link and not link.startswith("http"):
        link = BASE + link

    date_el = card.select_one(".tribe-event-date-start, time, .tribe-events-calendar__event-date-tag-datetime")
    date_str = ""
    if date_el:
        date_str = date_el.get("datetime", "") or date_el.get_text(strip=True)

    parsed_date = _parse_date(date_str)
    if not parsed_date:
        return None

    time_el = card.select_one(".tribe-events-schedule__datetime, .tribe-event-time")
    time_str = time_el.get_text(strip=True) if time_el else ""
    start_time, end_time = _parse_time(time_str)

    loc_el  = card.select_one(".tribe-venue, .tribe-events-calendar__event-venue")
    loc     = loc_el.get_text(strip=True) if loc_el else ""

    desc_el = card.select_one(".tribe-events-calendar__event-description, .tribe-events-list__event-description, .tribe-excerpt")
    desc    = desc_el.get_text(strip=True) if desc_el else ""

    cost_el = card.select_one(".tribe-events-cost, .tribe-ticket-price")
    cost_raw = cost_el.get_text(strip=True) if cost_el else "free"
    cost, cost_detail = normalize_cost(cost_raw)

    return {
        "id":                   slug(SOURCE, parsed_date, title),
        "title":                title,
        "source":               SOURCE,
        "source_url":           link or url,
        "date":                 parsed_date,
        "time":                 start_time,
        "end_time":             end_time,
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
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # Try dateutil as fallback
    try:
        from dateutil import parser as dp
        return dp.parse(s).strftime("%Y-%m-%d")
    except Exception:
        return None


def _parse_time(s):
    parts = re.split(r"\s*[-–]\s*", s)
    return (parts[0].strip() if parts else "", parts[1].strip() if len(parts) > 1 else "")


def _guess_categories(title, desc):
    text = (title + " " + desc).lower()
    cats = []
    if any(w in text for w in ["hike", "hik", "trail", "walk", "nature walk"]): cats.append("hiking")
    if any(w in text for w in ["natur", "wildlife", "bird", "plant", "pollinator", "wildflower", "ecology"]): cats.append("nature")
    if any(w in text for w in ["scienc", "stem", "lab", "microscope", "experiment"]): cats.append("science")
    if any(w in text for w in ["art", "craft", "draw", "paint", "sketch", "journal"]): cats.append("art")
    if any(w in text for w in ["fish", "fishing"]): cats.append("fishing")
    if any(w in text for w in ["farm", "garden", "harvest"]): cats.append("farm")
    if not cats:
        cats.append("nature")
    return cats
