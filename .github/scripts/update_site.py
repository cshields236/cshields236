import xml.etree.ElementTree as ET
import re
import urllib.request

LETTERBOXD_USERNAME = "cshields_"
GOODREADS_USER_ID = "106016596"
LETTERBOXD_RSS = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
LETTERBOXD_PROFILE = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
GOODREADS_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=read"
SITE_PATH = "docs/index.html"

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


def get_last_4_watched():
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
        films.append({
            "title": title_el.text,
            "year": year,
            "rating": rating,
            "stars_html": STAR_MAP.get(rating, ""),
            "link": link,
            "poster": poster,
        })
        if len(films) == 4:
            break
    return films


def get_favourites():
    html = fetch_url(LETTERBOXD_PROFILE)
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
        film_html = fetch_url(f"https://letterboxd.com/film/{slug}/")
        poster_match = re.search(
            r'https://a\.ltrbxd\.com/resized/(?:film-poster|sm/upload)/[^"]*0-230-0-345-crop[^"]*',
            film_html,
        )
        poster = ""
        if poster_match:
            poster = poster_match.group(0).replace("0-230-0-345", "0-150-0-225")
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


def render_watched(films):
    cards = []
    for f in films:
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


def main():
    favourites = get_favourites()
    watched = get_last_4_watched()
    books = get_books()

    with open(SITE_PATH, "r") as f:
        html = f.read()

    if favourites:
        favourites_html = render_favourites(favourites)
        html = re.sub(
            r"<!-- SITE-FAVOURITES:START -->.*?<!-- SITE-FAVOURITES:END -->",
            f"<!-- SITE-FAVOURITES:START -->\n{favourites_html}\n                    <!-- SITE-FAVOURITES:END -->",
            html, flags=re.DOTALL,
        )

    if watched:
        watched_html = render_watched(watched)
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

    with open(SITE_PATH, "w") as f:
        f.write(html)

    print(f"Updated site: {len(favourites)} favourites, {len(watched)} watched, {len(books)} books.")


if __name__ == "__main__":
    main()
