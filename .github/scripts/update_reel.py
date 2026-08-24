import json
import os
import re
import urllib.request
from datetime import date, timedelta

SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}
# Both language files render from the same data, so the EN file is the
# single source scraped for items.
SOURCE_PATH = "docs/index.html"
WINDOW_DAYS = 90
MIN_FRAMES = 2
GITHUB_USER = "cshields236"
GITHUB_GRAPHQL = "https://api.github.com/graphql"

KIND_ORDER = {"film": 0, "book": 1, "route": 2, "code": 3}

# Any opening tag carrying data-reel-date is a candidate; attributes are then
# read individually so their order in the tag does not matter.
TAG_RE = re.compile(r'<[a-zA-Z][^>]*\sdata-reel-date="[^"]*"[^>]*>')
ATTR_RE = re.compile(r'([a-zA-Z][a-zA-Z0-9-]*)="([^"]*)"')


def parse_items(html):
    items = []
    for tag in TAG_RE.findall(html):
        attrs = dict(ATTR_RE.findall(tag))
        kind = attrs.get("data-reel-kind", "").strip()
        item_date = attrs.get("data-reel-date", "").strip()
        target = attrs.get("id", "").strip()
        if not item_date or not target or kind not in KIND_ORDER:
            continue
        items.append({
            "kind": kind,
            "date": item_date,
            "target": target,
            "title": attrs.get("data-reel-title", ""),
            "sub": attrs.get("data-reel-sub", ""),
            "detail": attrs.get("data-reel-detail", ""),
            "path_d": attrs.get("data-reel-path", ""),
            "viewbox": attrs.get("data-reel-viewbox", ""),
        })
    return items


def within_window(items, today, days=WINDOW_DAYS):
    cutoff = today - timedelta(days=days)
    # Letterboxd reports watched dates in +1200, so an item dated one day
    # ahead of a UTC build is legitimate rather than corrupt.
    horizon = today + timedelta(days=1)
    kept = []
    for item in items:
        try:
            parsed = date.fromisoformat(item["date"])
        except ValueError:
            continue
        if cutoff <= parsed <= horizon:
            kept.append(dict(item, _d=parsed))
    kept.sort(key=lambda i: (i["_d"], KIND_ORDER[i["kind"]]))
    return kept


def month_buckets(start, end):
    """One (first, last) pair per calendar month the window touches, clamped
    to the window at both ends."""
    buckets = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        first = date(year, month, 1)
        next_first = date(year + (month == 12), (month % 12) + 1, 1)
        buckets.append((max(first, start), min(next_first - timedelta(days=1), end)))
        year, month = next_first.year, next_first.month
    return buckets
