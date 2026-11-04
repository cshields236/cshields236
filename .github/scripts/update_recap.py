"""Monthly recap card: last full calendar month of films, books, runs and
commits. Runs daily and always targets the previous month, so a failed run
self-heals the next day and an unchanged month produces no diff."""
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

from update_reel import fetch_commit_counts
from update_site import LETTERBOXD_RSS, STAR_MAP, fetch_url, get_hardcover_shelves

SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}
STRAVA_PAGE_SIZE = 200
LB_NS = {"letterboxd": "https://letterboxd.com"}

STRINGS = {
    "en": {
        "eyebrow": "Monthly Box Office",
        "months": ["January", "February", "March", "April", "May", "June", "July",
                   "August", "September", "October", "November", "December"],
        "films": "films watched", "books": "books finished", "km": "km run",
        "commits": "commits", "avg": "avg", "runs": lambda n: f"{n} run" + ("" if n == 1 else "s"),
        "pick": "Pick of the month", "longest": "Longest run",
    },
    "es": {
        "eyebrow": "Taquilla del mes",
        "months": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                   "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
        "films": "películas vistas", "books": "libros terminados", "km": "km corridos",
        "commits": "commits", "avg": "media", "runs": lambda n: f"{n} carrera" + ("" if n == 1 else "s"),
        "pick": "Lo mejor del mes", "longest": "Carrera más larga",
    },
}


class SourceUnavailable(Exception):
    pass


def previous_month(today):
    last = today.replace(day=1) - timedelta(days=1)
    return last.replace(day=1), last


def in_month(value, first, last):
    try:
        return first <= date.fromisoformat((value or "")[:10]) <= last
    except ValueError:
        return False


def film_stats(first, last):
    try:
        root = ET.fromstring(fetch_url(LETTERBOXD_RSS))
    except Exception as e:
        raise SourceUnavailable(f"Letterboxd: {e}")
    watched, oldest = [], None
    for item in root.findall(".//item"):
        title = item.findtext("letterboxd:filmTitle", namespaces=LB_NS)
        when = item.findtext("letterboxd:watchedDate", namespaces=LB_NS)
        if not title or not when:
            continue
        oldest = min(oldest or when, when)
        if not in_month(when, first, last):
            continue
        rating = item.findtext("letterboxd:memberRating", namespaces=LB_NS)
        watched.append({
            "title": title.strip(),
            "year": item.findtext("letterboxd:filmYear", namespaces=LB_NS) or "",
            "rating": float(rating) if rating else None,
            "date": when,
        })
    if not oldest or oldest > last.isoformat():
        # The feed has rolled past this month entirely; an empty result here
        # means missing history, not a month without films.
        raise SourceUnavailable("Letterboxd feed no longer reaches this month")
    rated = [f for f in watched if f["rating"] is not None]
    pick = max(rated, key=lambda f: (f["rating"], f["date"])) if rated else None
    return {
        "count": len(watched),
        # The feed only carries recent entries; if it doesn't reach back to the
        # 1st, the month's count is a lower bound.
        "truncated": bool(oldest) and oldest > first.isoformat() and bool(watched),
        "avg": sum(f["rating"] for f in rated) / len(rated) if rated else None,
        "pick": pick,
    }


def book_stats(first, last):
    read, _ = get_hardcover_shelves()
    if read is None:
        raise SourceUnavailable("Hardcover")
    return {"count": sum(1 for b in read if in_month(b["finished"], first, last))}


def strava_token():
    keys = ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")
    if not all(os.environ.get(k) for k in keys):
        raise SourceUnavailable("Strava credentials not set")
    data = urllib.parse.urlencode({
        "client_id": os.environ["STRAVA_CLIENT_ID"],
        "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
        "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://www.strava.com/oauth/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def run_stats(first, last):
    try:
        token = strava_token()
        # Pad the UTC window by a day each side; start_date_local decides.
        after = int(datetime(first.year, first.month, first.day, tzinfo=timezone.utc).timestamp()) - 86400
        before = int(datetime(last.year, last.month, last.day, tzinfo=timezone.utc).timestamp()) + 2 * 86400
        activities, page = [], 1
        while True:
            url = (f"https://www.strava.com/api/v3/athlete/activities?after={after}"
                   f"&before={before}&per_page={STRAVA_PAGE_SIZE}&page={page}")
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.load(resp)
            activities.extend(batch)
            if len(batch) < STRAVA_PAGE_SIZE:
                break
            page += 1
    except SourceUnavailable:
        raise
    except Exception as e:
        raise SourceUnavailable(f"Strava: {e}")
    # Zero-distance runs (no GPS, or auto-logged by a wearable) would inflate
    # the run count without adding any kilometres.
    runs = [a for a in activities
            if a.get("sport_type", a.get("type")) in RUN_TYPES
            and a.get("distance", 0) > 0
            and in_month(a.get("start_date_local"), first, last)]
    distances = [a.get("distance", 0) / 1000 for a in runs]
    return {"count": len(runs), "km": sum(distances), "longest": max(distances, default=0)}


def commit_stats(first, last):
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise SourceUnavailable("GITHUB_TOKEN not set")
    try:
        counts = fetch_commit_counts([(first, last)], token)
    except (Exception, SystemExit) as e:
        raise SourceUnavailable(f"GitHub: {e}")
    return {"count": counts.get((first.year, first.month), 0)}


def fmt_km(km, lang):
    text = f"{km:.1f}"
    return text.replace(".", ",") if lang == "es" else text


def stat(value, label, note=""):
    note_html = f'<span class="recap-note">{note}</span>' if note else ""
    return (
        '                <div class="recap-stat">\n'
        f'                    <span class="recap-value">{value}</span>\n'
        f'                    <span class="recap-label">{label}</span>{note_html}\n'
        '                </div>'
    )


def render(stats, first, lang):
    s = STRINGS[lang]
    films, books, runs, commits = stats["films"], stats["books"], stats["runs"], stats["commits"]
    film_value = f'{films["count"]}{"+" if films["truncated"] else ""}'
    film_note = ""
    if films["avg"] is not None:
        avg = round(films["avg"] * 2) / 2
        film_note = f'{s["avg"]} {STAR_MAP.get("%.1f" % avg, "")}'
    # A zero reads as "nothing happened"; leave quiet categories off the card.
    stat_html = "\n".join(html_ for count, html_ in [
        (films["count"], stat(film_value, s["films"], film_note)),
        (books["count"], stat(books["count"], s["books"])),
        (runs["count"], stat(fmt_km(runs["km"], lang), s["km"], s["runs"](runs["count"]))),
        (commits["count"], stat(commits["count"], s["commits"])),
    ] if count)
    highlights = []
    if films["pick"]:
        p = films["pick"]
        year = f' ({html.escape(p["year"])})' if p["year"] else ""
        stars = STAR_MAP.get("%.1f" % p["rating"], "")
        highlights.append(
            f'<span class="recap-hl-label">{s["pick"]}</span> '
            f'<span class="recap-hl-value">{html.escape(p["title"])}{year} '
            f'<span class="recap-stars">{stars}</span></span>'
        )
    if runs["count"]:
        highlights.append(
            f'<span class="recap-hl-label">{s["longest"]}</span> '
            f'<span class="recap-hl-value">{fmt_km(runs["longest"], lang)} km</span>'
        )
    hl_html = "".join(
        f'\n                <p class="recap-highlight">{h}</p>' for h in highlights
    )
    return (
        f'<div class="recap reveal" data-recap-month="{first.strftime("%Y-%m")}">\n'
        f'            <span class="recap-eyebrow">{s["eyebrow"]}</span>\n'
        f'            <h3 class="recap-title">{s["months"][first.month - 1]} {first.year}</h3>\n'
        '            <div class="recap-stats">\n'
        f'{stat_html}\n'
        '            </div>'
        f'{hl_html}\n'
        '        </div>'
    )


def main():
    first, last = previous_month(date.today())
    try:
        stats = {
            "films": film_stats(first, last),
            "books": book_stats(first, last),
            "runs": run_stats(first, last),
            "commits": commit_stats(first, last),
        }
    except SourceUnavailable as e:
        # A half-filled card would misreport the month; keep the last one.
        print(f"::warning::Recap not updated, source unavailable: {e}")
        return

    for lang, path in SITE_PATHS.items():
        with open(path) as f:
            page = f.read()
        page, n = re.subn(
            r"<!-- SITE-RECAP:START -->.*?<!-- SITE-RECAP:END -->",
            lambda _: f"<!-- SITE-RECAP:START -->\n{render(stats, first, lang)}\n        <!-- SITE-RECAP:END -->",
            page, flags=re.DOTALL,
        )
        if n == 0:
            sys.exit(f"SITE-RECAP marker not found in {path}")
        with open(path, "w") as f:
            f.write(page)

    f, r = stats["films"], stats["runs"]
    print(f"Recap for {first:%B %Y}: {f['count']} films, {stats['books']['count']} books, "
          f"{r['km']:.1f} km over {r['count']} runs, {stats['commits']['count']} commits.")


if __name__ == "__main__":
    main()
