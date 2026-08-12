import xml.etree.ElementTree as ET
import re
import urllib.request

LETTERBOXD_USERNAME = "cshields_"
GOODREADS_USER_ID = "106016596"
LETTERBOXD_RSS = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
LETTERBOXD_PROFILE = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
GOODREADS_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=read"
GOODREADS_CURRENTLY_READING_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=currently-reading"
SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}

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

BOOK_STARS = {
    1: "&#9733;", 2: "&#9733;&#9733;", 3: "&#9733;&#9733;&#9733;",
    4: "&#9733;&#9733;&#9733;&#9733;", 5: "&#9733;&#9733;&#9733;&#9733;&#9733;",
}


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


def get_books():
    data = fetch_url(GOODREADS_RSS)
    root = ET.fromstring(data)
    books = []
    for item in root.findall(".//item"):
        title = item.find("title").text.strip() if item.find("title") is not None else ""
        author = item.find("author_name").text.strip() if item.find("author_name") is not None else ""
        rating_el = item.find("user_rating")
        rating = int(rating_el.text) if rating_el is not None and rating_el.text else 0
        cover_el = item.find("book_large_image_url")
        cover = cover_el.text.strip() if cover_el is not None and cover_el.text else ""
        if "nophoto" in cover:
            cover = ""
        books.append({
            "title": title,
            "author": author,
            "rating": rating,
            "stars_html": BOOK_STARS.get(rating, ""),
            "cover": cover,
        })
        if len(books) == 6:
            break
    return books


def get_currently_reading(limit=3):
    data = fetch_url(GOODREADS_CURRENTLY_READING_RSS)
    root = ET.fromstring(data)
    books = []
    for item in root.findall(".//item"):
        title = item.find("title").text.strip() if item.find("title") is not None else ""
        author = item.find("author_name").text.strip() if item.find("author_name") is not None else ""
        cover_el = item.find("book_large_image_url")
        cover = cover_el.text.strip() if cover_el is not None and cover_el.text else ""
        if "nophoto" in cover:
            cover = ""
        books.append({
            "title": title,
            "author": author,
            "rating": 0,
            "stars_html": "",
            "cover": cover,
        })
        if len(books) == limit:
            break
    return books


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
    for f in films:
        if f["review"]:
            cards.append(
                f'                    <div class="film-card film-card-flippable">\n'
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
                f'                    <a href="{f["link"]}" class="film-card" target="_blank" rel="noopener">\n'
                f'                        <div class="film-poster">\n'
                f'                            <img src="{f["poster"]}" alt="{f["title"]}" loading="lazy">\n'
                f'                        </div>\n'
                f'                        <span class="film-title">{f["title"]}</span>\n'
                f'                        <span class="film-rating">{f["stars_html"]}</span>\n'
                f'                    </a>'
            )
    return "\n".join(cards)


def render_books(books):
    items = []
    for b in books:
        cover_html = ""
        if b["cover"]:
            cover_html = f'<img class="book-cover" src="{b["cover"]}" alt="{b["title"]}" loading="lazy">'
        items.append(
            f'                <div class="book-item">\n'
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
    items_html = render_books(books)
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
    books = get_books()
    currently_reading = get_currently_reading()

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
            books_html = render_books(books)
            html = re.sub(
                r"<!-- SITE-BOOKS:START -->.*?<!-- SITE-BOOKS:END -->",
                f"<!-- SITE-BOOKS:START -->\n{books_html}\n                <!-- SITE-BOOKS:END -->",
                html, flags=re.DOTALL,
            )

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

    fav_count = len(favourites) if favourites is not None else "unchanged"
    print(f"Updated {len(SITE_PATHS)} site file(s): {fav_count} favourites, {len(watched)} watched, {len(books)} books, {len(currently_reading)} currently reading.")


if __name__ == "__main__":
    main()
