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


COMMITS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
    }
  }
}
"""


def fetch_commit_counts(buckets, token):
    """contributionsCollection is used rather than /search/commits because
    search covers public repositories only and undercounts."""
    counts = {}
    for first, last in buckets:
        payload = json.dumps({
            "query": COMMITS_QUERY,
            "variables": {
                "login": GITHUB_USER,
                "from": f"{first.isoformat()}T00:00:00Z",
                "to": f"{last.isoformat()}T23:59:59Z",
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            GITHUB_GRAPHQL,
            data=payload,
            headers={
                "Authorization": f"bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "conorshields.ie site sync",
            },
        )
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if "errors" in body:
            raise SystemExit(f"GitHub GraphQL error for {first}: {body['errors']}")
        counts[(first.year, first.month)] = (
            body["data"]["user"]["contributionsCollection"]["totalCommitContributions"]
        )
    return counts


def commit_items(counts, buckets):
    items = []
    for first, last in buckets:
        total = counts.get((first.year, first.month))
        if total is None:
            continue
        items.append({
            "kind": "code",
            "date": last.isoformat(),
            "target": "",
            "title": "",
            "sub": "",
            "detail": str(total),
            "path_d": "",
            "viewbox": "",
        })
    return items


KIND_LABELS = {
    "en": {"film": "Now Showing", "book": "Intermission",
           "route": "On Location", "code": "Box Office"},
    "es": {"film": "En Cartelera", "book": "Intermedio",
           "route": "Exteriores", "code": "Taquilla"},
}

MONTH_ABBR = {
    "en": ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
           "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"],
    "es": ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
           "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"],
}

COMMITS_LABEL = {"en": "commits", "es": "commits"}
GITHUB_PROFILE = f"https://github.com/{GITHUB_USER}"
COMMIT_BAR_COUNT = 14


def _date_label(day, lang):
    return f"{day.day:02d} {MONTH_ABBR[lang][day.month - 1].capitalize()}"


def _commit_bars(total):
    """Deterministic heights so a rebuild with the same count produces an
    identical diff."""
    bars = []
    for i in range(COMMIT_BAR_COUNT):
        height = 18 + ((total * (i + 3)) % 82)
        bars.append(f'<span class="reel-bar" style="height:{height}%"></span>')
    return "".join(bars)


def render_frame(item, lang):
    kind = item["kind"]
    label = KIND_LABELS[lang][kind]
    date_label = _date_label(item["_d"], lang)
    month = MONTH_ABBR[lang][item["_d"].month - 1]
    href = GITHUB_PROFILE if kind == "code" else f'#{item["target"]}'
    external = ' target="_blank" rel="noopener"' if kind == "code" else ""

    if kind == "code":
        title, sub, detail = item["detail"], COMMITS_LABEL[lang], item["detail"]
        body = (
            f'<span class="reel-bars" aria-hidden="true">{_commit_bars(int(item["detail"]))}</span>'
            f'<span class="reel-body"><span class="reel-num">{item["detail"]}'
            f'<small>{COMMITS_LABEL[lang]}</small></span></span>'
        )
    elif kind == "route":
        title, sub, detail = item["title"], item["sub"], item["detail"]
        body = (
            f'<svg class="reel-route" viewBox="{item["viewbox"]}" preserveAspectRatio="xMidYMid meet"'
            f' aria-hidden="true"><path d="{item["path_d"]}" /></svg>'
            f'<span class="reel-body"><span class="reel-num">{item["detail"]}'
            f'<small>{item["title"]}</small></span></span>'
        )
    elif kind == "book":
        title, sub, detail = item["title"], item["sub"], item["detail"]
        body = (
            f'<span class="reel-inset"><span class="reel-title">{item["title"]}</span>'
            f'<span class="reel-sub">{item["sub"]}</span>'
            f'<span class="reel-stars">{item["detail"]}</span></span>'
        )
    else:
        title, sub, detail = item["title"], item["sub"], item["detail"]
        body = (
            f'<span class="reel-body"><span class="reel-title">{item["title"]}</span>'
            f'<span class="reel-sub">{item["sub"]}</span>'
            f'<span class="reel-stars">{item["detail"]}</span></span>'
        )

    return (
        f'<a class="reel-frame k-{kind}" href="{href}"{external}'
        f' data-month="{month}" data-r-date="{date_label}" data-r-kind="{label}"'
        f' data-r-title="{title}" data-r-sub="{sub}" data-r-detail="{detail}">'
        f'<span class="reel-kind"><i></i>{label}<em>{date_label}</em></span>'
        f'{body}</a>'
    )


def render_reel(items, lang):
    if len(items) < MIN_FRAMES:
        return ""
    return "\n".join(render_frame(i, lang) for i in items)


def inject(html, block, path):
    html, count = re.subn(
        r"<!-- SITE-REEL:START -->.*?<!-- SITE-REEL:END -->",
        f"<!-- SITE-REEL:START -->\n{block}\n<!-- SITE-REEL:END -->",
        html,
        flags=re.DOTALL,
    )
    if count == 0:
        raise SystemExit(f"SITE-REEL marker not found in {path}")
    return html


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required to fetch commit counts")

    today = date.today()
    with open(SOURCE_PATH, "r") as f:
        source = f.read()

    content = within_window(parse_items(source), today)
    if not content:
        raise SystemExit(
            f"No reel items found in {SOURCE_PATH} — the source sections may not "
            "yet carry data-reel-date attributes"
        )

    buckets = month_buckets(content[0]["_d"], today)
    counts = fetch_commit_counts(buckets, token)
    items = within_window(content + commit_items(counts, buckets), today)

    for lang, path in SITE_PATHS.items():
        with open(path, "r") as f:
            html = f.read()
        html = inject(html, render_reel(items, lang), path)
        with open(path, "w") as f:
            f.write(html)

    kinds = {k: sum(1 for i in items if i["kind"] == k) for k in KIND_ORDER}
    print(f"Updated {len(SITE_PATHS)} site file(s) with {len(items)} reel frames: {kinds}")


if __name__ == "__main__":
    main()
