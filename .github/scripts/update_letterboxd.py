import xml.etree.ElementTree as ET
import re
import urllib.request

LETTERBOXD_USERNAME = "cshields_"
RSS_URL = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
PROFILE_URL = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
README_PATH = "README.md"

STAR_MAP = {
    "0.5": "½", "1.0": "★", "1.5": "★½", "2.0": "★★",
    "2.5": "★★½", "3.0": "★★★", "3.5": "★★★½", "4.0": "★★★★",
    "4.5": "★★★★½", "5.0": "★★★★★",
}


def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def get_last_4_watched():
    data = fetch_url(RSS_URL)
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
        poster = poster_match.group(1) if poster_match else None
        films.append({
            "title": title_el.text,
            "year": year,
            "rating": rating,
            "stars": STAR_MAP.get(rating, ""),
            "link": link,
            "poster": poster,
        })
        if len(films) == 4:
            break
    return films


def get_favourites():
    html = fetch_url(PROFILE_URL)
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
        poster = None
        if poster_match:
            poster = poster_match.group(0).replace("0-230-0-345", "0-150-0-225")
        films.append({"name": name, "slug": slug, "link": link, "poster": poster})
        if len(films) == 4:
            break
    return films


def render_film_table(films, is_favourites=False):
    lines = []
    lines.append("<table>")
    lines.append("  <tr>")
    for f in films:
        poster = f.get("poster") or ""
        if is_favourites:
            link = f"https://letterboxd.com{f['link']}"
            lines.append(
                f'    <td align="center" width="150">'
                f'<a href="{link}">'
                f'<img src="{poster}" width="150" alt="{f["name"]}"/>'
                f"</a></td>"
            )
        else:
            lines.append(
                f'    <td align="center" width="150">'
                f'<a href="{f["link"]}">'
                f'<img src="{poster}" width="150" alt="{f["title"]}"/>'
                f"</a></td>"
            )
    lines.append("  </tr>")
    lines.append("  <tr>")
    for f in films:
        if is_favourites:
            lines.append(f'    <td align="center"><b>{f["name"]}</b></td>')
        else:
            stars = f["stars"]
            lines.append(
                f'    <td align="center">'
                f'<b>{f["title"]}</b><br/>{stars}</td>'
            )
    lines.append("  </tr>")
    lines.append("</table>")
    return "\n".join(lines)


def main():
    watched = get_last_4_watched()
    favourites = get_favourites()

    watched_md = render_film_table(watched, is_favourites=False)
    favourites_md = render_film_table(favourites, is_favourites=True)

    with open(README_PATH, "r") as f:
        readme = f.read()

    readme = re.sub(
        r"<!-- LETTERBOXD-FAVOURITES:START -->.*?<!-- LETTERBOXD-FAVOURITES:END -->",
        f"<!-- LETTERBOXD-FAVOURITES:START -->\n{favourites_md}\n<!-- LETTERBOXD-FAVOURITES:END -->",
        readme,
        flags=re.DOTALL,
    )
    readme = re.sub(
        r"<!-- LETTERBOXD-WATCHED:START -->.*?<!-- LETTERBOXD-WATCHED:END -->",
        f"<!-- LETTERBOXD-WATCHED:START -->\n{watched_md}\n<!-- LETTERBOXD-WATCHED:END -->",
        readme,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w") as f:
        f.write(readme)

    print(f"Updated README with {len(favourites)} favourites and {len(watched)} recently watched films.")


if __name__ == "__main__":
    main()
