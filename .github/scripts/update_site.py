import html
import json
import os
import xml.etree.ElementTree as ET
import re
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime

LETTERBOXD_USERNAME = "cshields_"
LETTERBOXD_RSS = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
LETTERBOXD_PROFILE = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
HARDCOVER_API = "https://api.hardcover.app/v1/graphql"
HARDCOVER_STATUS_READING = 2
HARDCOVER_STATUS_READ = 3
# Goodreads imports often lack a finish date, which Hardcover sorts last, so
# fetch the whole read shelf and sort on the date_added fallback locally.
HARDCOVER_READ_FETCH = 1000
SITE_BOOK_COUNT = 6
README_BOOK_COUNT = 10
SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}
README_PATH = "README.md"

STRINGS = {
    "en": {"currently_reading": "Currently Reading", "view_on_letterboxd": "View on Letterboxd →"},
    "es": {"currently_reading": "Actualmente Leyendo", "view_on_letterboxd": "Ver en Letterboxd →"},
}

STAR_MAP = {
    "0.5": "&#9733;&#189;", "1.0": "&#9733;", "1.5": "&#9733;&#189;",
    "2.0": "&#9733;&#9733;", "2.5": "&#9733;&#9733;&#189;",
    "3.0": "&#9733;&#9733;&#9733;", "3.5": "&#9733;&#9733;&#9733;&#189;",
    "4.0": "&#9733;&#9733;&#9733;&#9733;", "4.5": "&#9733;&#9733;&#9733;&#9733;&#189;",
    "5.0": "&#9733;&#9733;&#9733;&#9733;&#9733;",
}

def rfc822_to_iso(value):
    """Goodreads dates arrive RFC-822 ('Tue, 28 Jul 2026 00:00:00 +0000')."""
    if not value or not value.strip():
        return None
    try:
        return parsedate_to_datetime(value.strip()).date().isoformat()
    except (TypeError, ValueError):
        return None


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "item"


def unique_id(prefix, slug, seen):
    """Two books can share a title; ids must stay unique within a page."""
    candidate = f"{prefix}-{slug}"
    n = 1
    while candidate in seen:
        n += 1
        candidate = f"{prefix}-{slug}-{n}"
    seen.add(candidate)
    return candidate


def reel_attrs(item_id, kind, date, title, sub, detail):
    """The contract update_reel.py reads. Without a date the item is not
    Reel-eligible, so only the id is emitted.

    title/sub are escaped since they interpolate directly into HTML
    attributes; detail is pre-rendered star entities (e.g. &#9733;) and
    must not be double-escaped.
    """
    attrs = f' id="{item_id}"'
    if not date:
        return attrs
    safe_title = html.escape(str(title), quote=True)
    safe_sub = html.escape(str(sub), quote=True)
    return (
        f'{attrs} data-reel-date="{date}" data-reel-kind="{kind}"'
        f' data-reel-title="{safe_title}" data-reel-sub="{safe_sub}"'
        f' data-reel-detail="{detail}"'
    )


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def get_recent_watched(limit=15):
    data = fetch_url(LETTERBOXD_RSS)
    root = ET.fromstring(data)
    ns = {"letterboxd": "https://letterboxd.com", "tmdb": "https://themoviedb.org"}
    films = []
    for item in root.findall(".//item"):
        title_el = item.find("letterboxd:filmTitle", ns)
        if title_el is None:
            continue
        year = item.find("letterboxd:filmYear", ns).text
        rating_el = item.find("letterboxd:memberRating", ns)
        rating = rating_el.text if rating_el is not None else None
        link = item.find("link").text
        desc = item.find("description").text or ""
        poster_match = re.search(r'<img src="([^"]+)"', desc)
        poster = poster_match.group(1) if poster_match else ""

        watched_el = item.find("letterboxd:watchedDate", ns)
        watched_date = watched_el.text.strip() if watched_el is not None and watched_el.text else None
        slug_match = re.search(r"/film/([^/]+)/", link)
        film_slug = slug_match.group(1) if slug_match else slugify(title_el.text)

        # A plain watch-log entry's guid starts with "letterboxd-watch-" and
        # its description is always the auto-generated "Watched on <date>."
        # An entry with an actual written review has a guid starting with
        # "letterboxd-review-", and the paragraph after the poster image is
        # the real review text — verified against the live feed.
        guid_el = item.find("guid")
        guid = guid_el.text if guid_el is not None and guid_el.text else ""
        review = ""
        if guid.startswith("letterboxd-review-"):
            paragraphs = re.findall(r'<p>(.*?)</p>', desc, re.DOTALL)
            if len(paragraphs) > 1:
                joined = "<br />".join(p.strip() for p in paragraphs[1:])
                review = re.sub(r'</?(?!br\s*/?>)[a-zA-Z][^>]*>', '', joined).strip()

        films.append({
            "title": title_el.text,
            "year": year,
            "rating": rating,
            "stars_html": STAR_MAP.get(rating, ""),
            "link": link,
            "poster": poster,
            "review": review,
            "date": watched_date,
            "slug": film_slug,
        })
        if len(films) == limit:
            break
    return films


def get_favourites():
    try:
        html = fetch_url(LETTERBOXD_PROFILE)
    except urllib.error.HTTPError as e:
        print(f"Skipping favourites update: {e}")
        return None

    fav_section = re.search(r'id="favourites".*?</section>', html, re.DOTALL)
    if not fav_section:
        return []

    section = fav_section.group(0)
    films = []
    for match in re.finditer(
        r'data-item-name="([^"]+)".*?data-item-slug="([^"]+)".*?data-item-link="([^"]+)"',
        section,
    ):
        name, slug, link = match.groups()
        try:
            film_html = fetch_url(f"https://letterboxd.com/film/{slug}/")
        except urllib.error.HTTPError as e:
            print(f"Skipping favourites update: {e}")
            return None
        poster_match = re.search(
            r'https://a\.ltrbxd\.com/resized/(?:film-poster|sm/upload)/[^"]*?(0-\d+-0-\d+-crop)[^"]*',
            film_html,
        )
        poster = ""
        if poster_match:
            poster = poster_match.group(0).replace(poster_match.group(1), "0-150-0-225-crop")
        films.append({"name": name, "slug": slug, "link": link, "poster": poster})
        if len(films) == 4:
            break
    return films


HARDCOVER_QUERY = """
query Shelves($read: Int!, $reading: Int!, $limit: Int!) {
  me {
    read: user_books(where: {status_id: {_eq: $read}},
                     order_by: {last_read_date: desc_nulls_last}, limit: $limit) {
      ...shelfBook
    }
    reading: user_books(where: {status_id: {_eq: $reading}},
                        order_by: {date_added: desc}) {
      ...shelfBook
    }
  }
}
fragment shelfBook on user_books {
  rating
  last_read_date
  date_added
  book {
    title
    slug
    release_year
    image { url }
    contributions { contribution author { name } }
  }
}
"""


def book_stars(rating):
    if not rating:
        return ""
    value = float(rating)
    return "&#189;" if value == 0.5 else STAR_MAP.get(f"{value:.1f}", "")


def to_book(user_book):
    b = user_book["book"]
    contributions = b.get("contributions") or []
    # Translators, editors and introducers are listed too; Hardcover leaves
    # the role null or "Author" for the actual author.
    authors = [c for c in contributions if c.get("contribution") in (None, "Author")]
    author = (authors or contributions or [{"author": {"name": ""}}])[0]["author"]["name"]
    rating = user_book.get("rating") or 0
    return {
        "title": (b.get("title") or "").strip(),
        "author": author.strip(),
        "rating": rating,
        "stars_html": book_stars(rating),
        "cover": ((b.get("image") or {}).get("url") or "").strip(),
        "date": user_book.get("last_read_date") or user_book.get("date_added"),
        "url": f"https://hardcover.app/books/{b['slug']}" if b.get("slug") else "",
        "year": b.get("release_year"),
    }


def get_hardcover_shelves():
    """Returns (read, currently_reading), or (None, None) when Hardcover is
    unreachable so the caller keeps the books already on the page rather than
    blanking them or aborting the Letterboxd updates."""
    token = os.environ.get("HARDCOVER_TOKEN", "").strip()
    if not token:
        print("::warning::HARDCOVER_TOKEN not set, keeping existing books")
        return None, None
    if not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    body = json.dumps({
        "query": HARDCOVER_QUERY,
        "variables": {
            "read": HARDCOVER_STATUS_READ,
            "reading": HARDCOVER_STATUS_READING,
            "limit": HARDCOVER_READ_FETCH,
        },
    }).encode()
    req = urllib.request.Request(HARDCOVER_API, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": token,
        "User-Agent": "cshields236-site-updater",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
        if payload.get("errors"):
            raise ValueError(payload["errors"])
        me = payload["data"]["me"][0]
    except (urllib.error.URLError, ValueError, KeyError, IndexError) as e:
        print(f"::warning::Hardcover unavailable, keeping existing books: {e}")
        return None, None

    read = sorted((to_book(ub) for ub in me["read"]),
                  key=lambda b: b["date"] or "", reverse=True)
    reading = [to_book(ub) for ub in me["reading"]]
    for b in reading:
        # Unfinished books have no read date; keep them off the Reel.
        b["date"] = None
    return read, reading


def render_readme_books(read, reading):
    reading_md = "\n".join(
        f'- [{b["title"]}]({b["url"]}) by {b["author"]} <br />' for b in reading
    )
    read_md = "\n".join(
        f'- [{b["title"]}]({b["url"]}) by {b["author"]}'
        + (f' ({b["year"]})' if b["year"] else "")
        + (f' {"⭐" * int(b["rating"])}' if b["rating"] else "")
        + " <br />"
        for b in read[:README_BOOK_COUNT]
    )
    return reading_md, read_md


def update_readme(read, reading):
    with open(README_PATH, "r") as f:
        readme = f.read()
    reading_md, read_md = render_readme_books(read, reading)
    for marker, content in (("CURRENTLY-READING", reading_md), ("BOOK-LIST", read_md)):
        readme, n = re.subn(
            rf"<!-- {marker}:START -->.*?<!-- {marker}:END -->",
            f"<!-- {marker}:START -->\n{content}\n<!-- {marker}:END -->",
            readme, flags=re.DOTALL,
        )
        if n == 0:
            raise SystemExit(f"{marker} marker not found in {README_PATH}")
    with open(README_PATH, "w") as f:
        f.write(readme)


def render_favourites(films):
    cards = []
    for f in films:
        cards.append(
            f'                    <a href="https://letterboxd.com{f["link"]}" class="film-card" target="_blank" rel="noopener">\n'
            f'                        <div class="film-poster">\n'
            f'                            <img src="{f["poster"]}" alt="{f["name"]}" loading="lazy">\n'
            f'                        </div>\n'
            f'                        <span class="film-title">{f["name"]}</span>\n'
            f'                    </a>'
        )
    return "\n".join(cards)


REVIEW_ICON = (
    '<svg class="review-icon" viewBox="0 0 24 24" fill="none" stroke-width="2">'
    '<path d="M7 7h4v6H7a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z"/>'
    '<path d="M15 7h4v6h-4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z"/></svg>'
)


def render_watched(films, view_on_letterboxd_text):
    cards = []
    seen = set()
    for f in films:
        slug = f.get("slug")
        if not slug:
            slug_match = re.search(r"/film/([^/]+)/", f["link"])
            slug = slug_match.group(1) if slug_match else slugify(f["title"])
        attrs = reel_attrs(
            unique_id("film", slug, seen), "film", f.get("date"),
            f["title"], f["year"], f["stars_html"],
        )
        if f["review"]:
            cards.append(
                f'                    <div class="film-card film-card-flippable"{attrs}>\n'
                f'                        <div class="film-flip">\n'
                f'                            <div class="film-flip-front">\n'
                f'                                <div class="film-poster">\n'
                f'                                    <img src="{f["poster"]}" alt="{f["title"]}" loading="lazy">\n'
                f'                                </div>\n'
                f'                                <button type="button" class="film-review-toggle" aria-label="Toggle review">{REVIEW_ICON}</button>\n'
                f'                            </div>\n'
                f'                            <div class="film-flip-back">\n'
                f'                                <p class="film-review">{f["review"]}</p>\n'
                f'                                <a href="{f["link"]}" class="film-review-link" target="_blank" rel="noopener">{view_on_letterboxd_text}</a>\n'
                f'                            </div>\n'
                f'                        </div>\n'
                f'                        <span class="film-title">{f["title"]}</span>\n'
                f'                        <span class="film-rating">{f["stars_html"]}</span>\n'
                f'                    </div>'
            )
        else:
            cards.append(
                f'                    <a href="{f["link"]}" class="film-card"{attrs} target="_blank" rel="noopener">\n'
                f'                        <div class="film-poster">\n'
                f'                            <img src="{f["poster"]}" alt="{f["title"]}" loading="lazy">\n'
                f'                        </div>\n'
                f'                        <span class="film-title">{f["title"]}</span>\n'
                f'                        <span class="film-rating">{f["stars_html"]}</span>\n'
                f'                    </a>'
            )
    return "\n".join(cards)


def render_books(books, reel=False):
    items = []
    seen = set()
    for b in books:
        cover_html = ""
        if b["cover"]:
            cover_html = f'<img class="book-cover" src="{b["cover"]}" alt="{b["title"]}" loading="lazy">'
        attrs = ""
        if reel:
            attrs = reel_attrs(
                unique_id("book", slugify(b["title"]), seen), "book", b.get("date"),
                b["title"], b["author"], b["stars_html"],
            )
        items.append(
            f'                <div class="book-item"{attrs}>\n'
            f'                    {cover_html}\n'
            f'                    <div class="book-info">\n'
            f'                        <span class="book-title">{b["title"]}</span>\n'
            f'                        <span class="book-author">{b["author"]}</span>\n'
            f'                    </div>\n'
            f'                    <span class="book-rating">{b["stars_html"]}</span>\n'
            f'                </div>'
        )
    return "\n".join(items)


def render_currently_reading_block(books, heading):
    if not books:
        return ""
    items_html = render_books(books, reel=False)
    return (
        '<div class="books-block reveal">\n'
        f'                <h3 class="books-subtitle">{heading}</h3>\n'
        '                <div class="books-list">\n'
        f'{items_html}\n'
        '                </div>\n'
        '            </div>'
    )


def main():
    favourites = get_favourites()
    watched = get_recent_watched()
    read, currently_reading = get_hardcover_shelves()
    books = read[:SITE_BOOK_COUNT] if read is not None else None

    for lang, site_path in SITE_PATHS.items():
        with open(site_path, "r") as f:
            html = f.read()

        if favourites:
            favourites_html = render_favourites(favourites)
            html = re.sub(
                r"<!-- SITE-FAVOURITES:START -->.*?<!-- SITE-FAVOURITES:END -->",
                f"<!-- SITE-FAVOURITES:START -->\n{favourites_html}\n                    <!-- SITE-FAVOURITES:END -->",
                html, flags=re.DOTALL,
            )

        if watched:
            watched_html = render_watched(watched, STRINGS[lang]["view_on_letterboxd"])
            html = re.sub(
                r"<!-- SITE-WATCHED:START -->.*?<!-- SITE-WATCHED:END -->",
                f"<!-- SITE-WATCHED:START -->\n{watched_html}\n                    <!-- SITE-WATCHED:END -->",
                html, flags=re.DOTALL,
            )

        if books:
            books_html = render_books(books, reel=True)
            html = re.sub(
                r"<!-- SITE-BOOKS:START -->.*?<!-- SITE-BOOKS:END -->",
                f"<!-- SITE-BOOKS:START -->\n{books_html}\n                <!-- SITE-BOOKS:END -->",
                html, flags=re.DOTALL,
            )

        # An empty list means the shelf is genuinely empty and the block should
        # clear; None means the feed was unreachable, so leave it as it is.
        if currently_reading is not None:
            currently_reading_html = render_currently_reading_block(currently_reading, STRINGS[lang]["currently_reading"])
            html, n = re.subn(
                r"<!-- SITE-CURRENTLY-READING:START -->.*?<!-- SITE-CURRENTLY-READING:END -->",
                f"<!-- SITE-CURRENTLY-READING:START -->{currently_reading_html}<!-- SITE-CURRENTLY-READING:END -->",
                html, flags=re.DOTALL,
            )
            if n == 0:
                raise SystemExit(f"SITE-CURRENTLY-READING marker not found in {site_path}")

        with open(site_path, "w") as f:
            f.write(html)

    if read is not None:
        update_readme(read, currently_reading)

    fav_count = len(favourites) if favourites is not None else "unchanged"
    book_count = len(books) if books is not None else "unchanged"
    reading_count = len(currently_reading) if currently_reading is not None else "unchanged"
    print(f"Updated {len(SITE_PATHS)} site file(s): {fav_count} favourites, {len(watched)} watched, {book_count} books, {reading_count} currently reading.")


if __name__ == "__main__":
    main()
