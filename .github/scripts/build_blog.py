"""Builds the blog from posts/<slug>/index.md into docs/blog/, plus the RSS
feed and the Writing section on both home pages. docs/blog/ is regenerated
from scratch each run, so deleting a post folder unpublishes it."""
import html
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

import markdown
from PIL import Image, ImageOps

from update_site import LETTERBOXD_RSS, STAR_MAP, fetch_url

ROOT = Path(__file__).resolve().parents[2]
POSTS_DIR = ROOT / "posts"
OUT_DIR = ROOT / "docs" / "blog"
HOME_PAGES = {"en": ROOT / "docs" / "index.html", "es": ROOT / "docs" / "es" / "index.html"}
SITE_URL = "https://conorshields.ie"
HOME_POST_COUNT = 3
MAX_IMAGE_WIDTH = 1600
JPEG_QUALITY = 82
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
LB_NS = {"letterboxd": "https://letterboxd.com"}

HOME_STRINGS = {
    "en": {"nav": "Writing", "label": "Director's Commentary", "title": "Writing", "all": "All posts", "lang_note": ""},
    "es": {"nav": "Escritos", "label": "Comentario del director", "title": "Escritos", "all": "Todos los escritos",
           "lang_note": "en inglés"},
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]


def fmt_date(d, lang="en"):
    if lang == "es":
        return f"{d.day} {MONTHS_ES[d.month - 1]} {d.year}"
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


# ─── Posts ───

def parse_front_matter(text, path):
    """Minimal `key: value` block between --- lines; avoids a YAML dependency
    for the four fields a post needs."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        sys.exit(f"{path}: missing front matter (--- title/date/summary ---)")
    meta = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            # Only a wrapping pair is YAML-style quoting; "On 'La Haine'" keeps its quotes.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            meta[key.strip().lower()] = value
    for key in ("title", "date"):
        if not meta.get(key):
            sys.exit(f"{path}: front matter needs '{key}'")
    try:
        meta["date"] = date.fromisoformat(meta["date"])
    except ValueError:
        sys.exit(f"{path}: date must be YYYY-MM-DD, got {meta['date']!r}")
    meta["draft"] = meta.get("draft", "").lower() in ("true", "yes")
    return meta, text[match.end():]


def load_posts():
    posts = []
    if not POSTS_DIR.is_dir():
        return posts
    for folder in sorted(POSTS_DIR.iterdir()):
        # _template and other underscore folders are scaffolding, not posts.
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        source = folder / "index.md"
        if not source.is_file():
            continue
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", folder.name):
            sys.exit(f"{folder}: folder names become URLs; use lowercase-words-with-dashes")
        meta, body = parse_front_matter(source.read_text(encoding="utf-8"), source)
        if meta["draft"]:
            continue
        posts.append({"slug": folder.name, "folder": folder, "body": body, **meta})
    posts.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return posts


# ─── Embeds ───

def letterboxd_films():
    """Films in the Letterboxd feed keyed by slug, for poster and rating.
    Letterboxd blocks scraping film pages from CI, so the feed is the only
    reliable source; films outside it fall back to a plain link card."""
    try:
        root = ET.fromstring(fetch_url(LETTERBOXD_RSS))
    except Exception as e:
        print(f"::warning::Letterboxd feed unavailable, film cards will have no posters: {e}")
        return {}
    films = {}
    for item in root.findall(".//item"):
        link = item.findtext("link") or ""
        slug = re.search(r"/film/([^/]+)/", link)
        title = item.findtext("letterboxd:filmTitle", namespaces=LB_NS)
        if not slug or not title:
            continue
        poster = re.search(r'<img src="([^"]+)"', item.findtext("description") or "")
        films.setdefault(slug.group(1), {
            "title": title,
            "year": item.findtext("letterboxd:filmYear", namespaces=LB_NS) or "",
            "rating": item.findtext("letterboxd:memberRating", namespaces=LB_NS),
            "poster": poster.group(1) if poster else "",
        })
    return films


def iframe(src, title, cls, height=None):
    h = f' height="{height}"' if height else ""
    return (f'<div class="embed {cls}"><iframe src="{html.escape(src)}" title="{html.escape(title)}"{h} '
            'loading="lazy" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" '
            'allowfullscreen></iframe></div>')


def embed_for(url, films):
    u = urlparse(url)
    host = u.netloc.lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]

    if host == "open.spotify.com" and len(parts) >= 2 and parts[-2] in ("track", "album", "playlist", "episode", "show"):
        kind, item = parts[-2], parts[-1]
        return iframe(f"https://open.spotify.com/embed/{kind}/{item}", "Spotify player", "embed-spotify",
                      152 if kind in ("track", "episode") else 352)

    if host == "music.apple.com" and parts:
        is_song = "i" in parse_qs(u.query) or "song" in parts
        src = f"https://embed.music.apple.com{u.path}" + (f"?{u.query}" if u.query else "")
        return iframe(src, "Apple Music player", "embed-apple", 175 if is_song else 450)

    video = None
    if host in ("youtube.com", "m.youtube.com") and u.path == "/watch":
        video = parse_qs(u.query).get("v", [None])[0]
    elif host == "youtu.be" and parts:
        video = parts[0]
    if video and re.fullmatch(r"[\w-]{6,20}", video):
        return iframe(f"https://www.youtube-nocookie.com/embed/{video}", "YouTube video", "embed-video")

    if host == "letterboxd.com" and "film" in parts and parts.index("film") + 1 < len(parts):
        slug = parts[parts.index("film") + 1]
        film = films.get(slug, {})
        title = film.get("title") or slug.replace("-", " ").title()
        year = f' <span class="film-embed-year">{html.escape(film["year"])}</span>' if film.get("year") else ""
        stars = STAR_MAP.get(film.get("rating") or "", "")
        poster = (f'<img class="film-embed-poster" src="{html.escape(film["poster"])}" alt="" loading="lazy">'
                  if film.get("poster") else '<span class="film-embed-poster film-embed-blank" aria-hidden="true"></span>')
        stars_html = f'<span class="film-embed-stars">{stars}</span>' if stars else ""
        return (f'<a class="film-embed" href="https://letterboxd.com/film/{html.escape(slug)}/" target="_blank" rel="noopener">'
                f'{poster}<span class="film-embed-body"><span class="film-embed-kind">Letterboxd</span>'
                f'<span class="film-embed-title">{html.escape(title)}{year}</span>{stars_html}</span></a>')

    if host.endswith("bandcamp.com"):
        # Bandcamp's player needs a numeric album id the URL doesn't carry.
        name = parts[-1].replace("-", " ").title() if parts else host.split(".")[0]
        return (f'<a class="link-embed" href="{html.escape(url)}" target="_blank" rel="noopener">'
                f'<span class="film-embed-kind">Bandcamp</span><span class="link-embed-title">{html.escape(name)}</span></a>')
    return None


BARE_URL_LINE = re.compile(r"^(https?://\S+)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")


def expand_embeds(body, films):
    """A URL alone on its own line becomes an embed; Markdown passes the
    resulting HTML block through untouched because it's separated by blank
    lines. URLs inside fenced code stay as written."""
    lines, fence = [], None
    for line in body.split("\n"):
        f = FENCE.match(line)
        if f and fence is None:
            fence = f.group(1)
        elif f and f.group(1) == fence and not f.group(2).strip():
            # Only the identical delimiter closes a block, as in Python-Markdown,
            # so a ``` example inside a ```` block doesn't end it early.
            fence = None
            lines.append(line)
            continue
        match = None if fence else BARE_URL_LINE.match(line)
        embed = embed_for(match.group(1), films) if match else None
        lines.append(f"\n{embed}\n" if embed else line)
    return "\n".join(lines)


# ─── Images ───

def publish_image(src, dest):
    """Resize and strip metadata: phone photos carry GPS in EXIF."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        # Writers fall back to im.info for EXIF/XMP; keep only what affects rendering.
        im.info = {k: v for k, v in im.info.items() if k in ("icc_profile", "transparency")}
        if im.width > MAX_IMAGE_WIDTH:
            im = im.resize((MAX_IMAGE_WIDTH, round(im.height * MAX_IMAGE_WIDTH / im.width)), Image.LANCZOS)
        if src.suffix.lower() in (".jpg", ".jpeg"):
            im.convert("RGB").save(dest, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
        else:
            im.save(dest, optimize=True)
        return im.size


IMG_TAG = re.compile(r"<img\b[^>]*>")
# Raw HTML in a post can single-quote attributes; Markdown's own output never does.
TAG_ATTR = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)=(?:"([^"]*)"|'([^']*)')""")


def tag_attrs(tag):
    """Attribute values ready to re-serialise inside double quotes."""
    return {name: dq if dq or not sq else sq.replace('"', "&quot;")
            for name, dq, sq in TAG_ATTR.findall(tag)}


def process_images(content, post, out_dir):
    first_image = None

    def repl(match):
        nonlocal first_image
        # attr_list ({: .wide}) can add attributes in any order, so parse them
        # rather than matching a fixed alt/src/title layout.
        attrs = tag_attrs(match.group(0))
        src = attrs.get("src", "")
        title = attrs.pop("title", None)
        if src and not re.match(r"^(https?:)?//", src):
            source = (post["folder"] / unquote(html.unescape(src))).resolve()
            if post["folder"].resolve() not in source.parents or not source.is_file():
                sys.exit(f"{post['folder']}/index.md: image not found: {src}")
            if source.suffix.lower() not in IMAGE_EXTS:
                sys.exit(f"{post['folder']}/index.md: unsupported image type: {src} "
                         f"(use {', '.join(sorted(IMAGE_EXTS))})")
            rel = source.relative_to(post["folder"].resolve()).as_posix()
            width, height = publish_image(source, out_dir / rel)
            first_image = first_image or rel
            attrs.update(src=quote(rel), width=str(width), height=str(height))
        attrs.setdefault("alt", "")
        attrs["loading"] = "lazy"
        tag = "<img " + " ".join(f'{k}="{v}"' for k, v in attrs.items()) + ">"
        if title:
            return f'<figure>{tag}<figcaption>{title}</figcaption></figure>'
        return tag

    content = IMG_TAG.sub(repl, content)
    # An image alone in a paragraph is a figure, not inline text.
    content = re.sub(r"<p>(<figure>.*?</figure>)</p>", r"\1", content)
    content = re.sub(r"<p>(<img [^>]+>)</p>", r"<figure>\1</figure>", content)
    return content, first_image


def render_markdown(body):
    md = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"], output_format="html")
    content = md.convert(body)
    # Links leaving the site open in a new tab, like the rest of the site's outbound links.
    return re.sub(r'<a href="(https?://(?!conorshields\.ie)[^"]+)"',
                  r'<a href="\1" target="_blank" rel="noopener"', content)


# ─── Pages ───

def head(title, description, canonical, og_image=None, og_type="article"):
    image = f'\n<meta property="og:image" content="{og_image}"/>' if og_image else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}"/>
<meta property="og:title" content="{html.escape(title)}"/>
<meta property="og:description" content="{html.escape(description)}"/>
<meta property="og:type" content="{og_type}"/>
<meta property="og:url" content="{canonical}"/>{image}
<link rel="canonical" href="{canonical}"/>
<link rel="alternate" type="application/rss+xml" title="Conor Shields — Writing" href="/blog/feed.xml"/>
<link href="data:image/svg+xml,&lt;svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22&gt;&lt;text y=%22.9em%22 font-size=%2290%22&gt;%F0%9F%8E%AC&lt;/text&gt;&lt;/svg&gt;" rel="icon"/>
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@800&amp;family=Newsreader:ital,wght@0,400;0,500;1,400&amp;family=Space+Mono:wght@400;700&amp;display=swap" rel="stylesheet"/>
<link href="/style.css" rel="stylesheet"/>
<script src="/theme.js"></script>
</head>
<body class="blog-page">
<nav class="nav nav-simple scrolled" id="nav">
<div class="nav-inner">
<a class="nav-logo" href="/">CS</a>
<div class="nav-links">
<a href="/">Home</a>
<a href="/blog/">Writing</a>
<span data-theme-slot></span>
</div>
</div>
</nav>
"""


FOOT = """<footer class="footer">
<div class="container">
<p>Conor Shields © {year} · <a href="/blog/feed.xml">RSS</a></p>
</div>
</footer>
</body>
</html>
"""


def post_meta_line(post, lang="en"):
    return f'<time datetime="{post["date"].isoformat()}">{fmt_date(post["date"], lang)}</time>'


def render_post(post, content, og_image):
    url = f"{SITE_URL}/blog/{post['slug']}/"
    summary = post.get("summary", "")
    lede = f'<p class="post-summary">{html.escape(summary)}</p>' if summary else ""
    return (head(f"{post['title']} — Conor Shields", summary or post["title"], url,
                 f"{url}{quote(og_image)}" if og_image else None)
            + f"""<main class="post">
<article class="container post-container">
<header class="post-header">
<span class="section-label">{post_meta_line(post)}</span>
<h1 class="post-title">{html.escape(post['title'])}</h1>
{lede}
</header>
<div class="post-body">
{content}
</div>
<p class="post-back"><a class="section-link" href="/blog/">&larr; All writing</a></p>
</article>
</main>
""" + FOOT.format(year=post["date"].year))


def post_list_items(posts, lang="en"):
    return "\n".join(
        f'<li class="post-item"><a href="/blog/{p["slug"]}/">'
        f'<span class="post-item-date">{post_meta_line(p, lang)}</span>'
        f'<span class="post-item-title">{html.escape(p["title"])}</span>'
        + (f'<span class="post-item-summary">{html.escape(p["summary"])}</span>' if p.get("summary") else "")
        + "</a></li>"
        for p in posts
    )


def render_index(posts):
    return (head("Writing — Conor Shields", "Notes on films, books, music, running and code.",
                 f"{SITE_URL}/blog/", og_type="website")
            + f"""<main class="post">
<div class="container post-container">
<header class="post-header">
<span class="section-label">Director's Commentary</span>
<h1 class="post-title">Writing</h1>
</header>
<ul class="post-list">
{post_list_items(posts)}
</ul>
</div>
</main>
""" + FOOT.format(year=date.today().year))


START_TAG = re.compile(r"<[a-zA-Z][^<>]*>")
RELATIVE_ATTR = re.compile(r'\b(src|href)="(?![a-z][a-z0-9+.-]*:)([^"]*)"')


def absolutise_links(content, base):
    """Feed readers resolve against the feed URL, not the post's, so relative
    links and images are made absolute. Only real start tags are touched:
    code samples are entity-escaped (&lt;a ...), so they never match."""
    def fix_attr(m):
        absolute = urljoin(base, html.unescape(m.group(2)))
        return f'{m.group(1)}="{html.escape(absolute, quote=True)}"'
    return START_TAG.sub(lambda tag: RELATIVE_ATTR.sub(fix_attr, tag.group(0)), content)


def render_feed(posts, contents):
    items = []
    for p in posts:
        url = f"{SITE_URL}/blog/{p['slug']}/"
        published = datetime(p["date"].year, p["date"].month, p["date"].day, 12, tzinfo=timezone.utc)
        body = absolutise_links(contents[p["slug"]], url)
        items.append(f"""  <item>
    <title>{html.escape(p['title'])}</title>
    <link>{url}</link>
    <guid isPermaLink="true">{url}</guid>
    <pubDate>{format_datetime(published)}</pubDate>
    <description>{html.escape(body)}</description>
  </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Conor Shields — Writing</title>
  <link>{SITE_URL}/blog/</link>
  <description>Notes on films, books, music, running and code.</description>
  <language>en</language>
{chr(10).join(items)}
</channel>
</rss>
"""


# ─── Home page ───

def render_home_section(posts, lang):
    if not posts:
        return ""
    s = HOME_STRINGS[lang]
    lang_note = f'\n<p class="post-lang">{s["lang_note"].capitalize()}</p>' if s["lang_note"] else ""
    return f"""
<section class="section writing" id="writing">
<div class="container">
<div class="section-header reveal">
<span class="section-label">{s['label']}</span>
<h2 class="section-title">{s['title']}</h2>
<a class="section-link" href="/blog/">{s['all']}</a>
</div>
<ul class="post-list reveal">
{post_list_items(posts[:HOME_POST_COUNT], lang)}
</ul>{lang_note}
</div>
</section>
"""


def update_home_pages(posts):
    for lang, path in HOME_PAGES.items():
        page = path.read_text(encoding="utf-8")
        nav = f'<a href="#writing">{HOME_STRINGS[lang]["nav"]}</a>' if posts else ""
        replacements = [
            ("SITE-WRITING", render_home_section(posts, lang)),
            ("SITE-WRITING-NAV", nav),
            ("SITE-WRITING-NAV-MOBILE", nav),
        ]
        for marker, content in replacements:
            page, n = re.subn(rf"<!-- {marker}:START -->.*?<!-- {marker}:END -->",
                              lambda _: f"<!-- {marker}:START -->{content}<!-- {marker}:END -->",
                              page, flags=re.DOTALL)
            if n != 1:
                sys.exit(f"{marker} marker not found exactly once in {path}")
        path.write_text(page, encoding="utf-8")


def main():
    posts = load_posts()
    films = letterboxd_films() if posts else {}
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    contents = {}
    for post in posts:
        out = OUT_DIR / post["slug"]
        out.mkdir(parents=True)
        content = render_markdown(expand_embeds(post["body"], films))
        content, first_image = process_images(content, post, out)
        contents[post["slug"]] = content
        (out / "index.html").write_text(render_post(post, content, first_image), encoding="utf-8")

    (OUT_DIR / "index.html").write_text(render_index(posts), encoding="utf-8")
    (OUT_DIR / "feed.xml").write_text(render_feed(posts, contents), encoding="utf-8")
    update_home_pages(posts)
    print(f"Built {len(posts)} post(s) into {OUT_DIR.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
