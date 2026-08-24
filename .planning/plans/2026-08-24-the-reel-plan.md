# The Reel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-bleed "The Reel" section to `conorshields.ie` — a horizontal, scrubbable film strip showing the last 90 days of films watched, books finished, runs logged and monthly commit counts in date order, where clicking a frame scrolls to that item in its own section.

**Architecture:** The site is a static bilingual site (`docs/index.html` EN, `docs/es/index.html` ES) kept fresh by Python scripts run on GitHub Actions schedules; each rewrites content between `<!-- MARKER:START -->...<!-- MARKER:END -->` comment pairs. The Reel is built by **reading the site's own rendered output** rather than re-fetching the three source feeds: the existing scripts start emitting `id` and `data-reel-*` attributes on the items they already render, and a new `update_reel.py` scrapes those attributes, merges them into one date-sorted list, and writes the strip. Only commit counts need a live API call. Frames are `<a>` anchors, so scrolling and arrival highlighting are handled by the browser (`scroll-behavior: smooth` + `:target`) with no JavaScript in the navigation path.

**Tech Stack:** Static HTML/CSS/vanilla JS, Python 3.12 (stdlib only — `urllib`, `re`, `json`, `datetime`, `email.utils`), GitHub Actions (`schedule` + `workflow_dispatch`), GitHub GraphQL API.

**Spec:** `.planning/specs/2026-08-24-the-reel-design.md`

**Deliberate refinement of the spec:** Spec §3 says the display fields are "scraped from the item's existing child elements". This plan instead has the source scripts emit the display fields as explicit `data-reel-title` / `data-reel-sub` / `data-reel-detail` attributes on the same element that carries `data-reel-date`. Scraping inner text would couple `update_reel.py` to the nested markup of three other renderers; reading attributes off a single opening tag makes the contract explicit and order-independent. Everything else follows the spec as written.

## Global Constraints

- Every content change to `docs/index.html` must have a matching change in `docs/es/index.html` — the site is bilingual and the two files are structurally identical except for copy.
- Injected content uses the existing `<!-- MARKER:START -->...<!-- MARKER:END -->` convention, substituted with `re.sub(..., flags=re.DOTALL)`, and the script raises `SystemExit` when a marker is missing (see `update_site.py`'s `SITE-CURRENTLY-READING` handling).
- Python is **stdlib only**. No new dependencies, no `pip install` step in any workflow.
- Reuse existing CSS custom properties (`--display`, `--serif`, `--mono`, `--crimson`, `--crimson-soft`, `--paper`, `--paper-dim`, `--ink`, `--text`, `--text-muted`, `--text-dim`, `--line`, `--line-strong`, `--ease-smooth`). The only new token permitted is `--emulsion: #081310`.
- No client-side data fetching. All content is written at build time.
- Cron schedules use a 5am UTC base with the existing stagger preserved; no two workflows that write the same files share a minute.
- The Reel section must be added to the `@media print` hide-list in `docs/style.css` alongside `.section.films, .section.routes, .section.books`.
- Reel window is **90 days**; frame kind order for tie-breaking is `film, book, route, code`.
- Attribute values emitted by the Python scripts are already HTML-escaped via each script's `esc()`/entity helpers. `update_reel.py` must pass scraped values through **without re-escaping** them.

---

### Task 1: Emit dates and reel attributes from `update_site.py`

**Files:**
- Modify: `.github/scripts/update_site.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `.film-card` elements (watched films only) and `.book-item` elements (read books only) in both site files, each carrying `id`, `data-reel-date="YYYY-MM-DD"`, `data-reel-kind`, `data-reel-title`, `data-reel-sub`, `data-reel-detail`. Also produces module-level helpers `rfc822_to_iso(value) -> str | None`, `slugify(text) -> str`, `unique_id(prefix, slug, seen) -> str`, and `reel_attrs(item_id, kind, date, title, sub, detail) -> str`.

**Critical trap:** `render_books()` is called for **both** the "Read" list and the "Currently Reading" block. Currently-reading books have no finish date and must not enter the Reel. `render_books()` therefore takes a `reel` flag, and `render_currently_reading_block()` calls it with `reel=False`.

- [ ] **Step 1: Write the failing test**

Create `/tmp/test_reel_attrs.py`:

```python
import sys
sys.path.insert(0, ".github/scripts")
import update_site as u

# Date normalisation: Goodreads RFC-822 -> ISO
assert u.rfc822_to_iso("Tue, 28 Jul 2026 00:00:00 +0000") == "2026-07-28"
assert u.rfc822_to_iso("") is None
assert u.rfc822_to_iso(None) is None
assert u.rfc822_to_iso("not a date") is None

# Slugs
assert u.slugify("The Brothers Karamazov") == "the-brothers-karamazov"
assert u.slugify("Capitalist Realism: Is There No Alternative?") == "capitalist-realism-is-there-no-alternative"
assert u.slugify("Elevator in Sài Gòn") == "elevator-in-s-i-g-n"

# Collision handling
seen = set()
assert u.unique_id("book", "the-trial", seen) == "book-the-trial"
assert u.unique_id("book", "the-trial", seen) == "book-the-trial-2"
assert u.unique_id("book", "the-trial", seen) == "book-the-trial-3"

# Attribute rendering
attrs = u.reel_attrs("film-la-haine", "film", "2026-08-11", "La Haine", "1995", "&#9733;&#9733;")
for expected in ['id="film-la-haine"', 'data-reel-date="2026-08-11"',
                 'data-reel-kind="film"', 'data-reel-title="La Haine"',
                 'data-reel-sub="1995"', 'data-reel-detail="&#9733;&#9733;"']:
    assert expected in attrs, expected

# No date -> id only, no reel attributes (item stays out of the Reel)
attrs_no_date = u.reel_attrs("book-x", "book", None, "X", "Y", "")
assert 'id="book-x"' in attrs_no_date
assert "data-reel-date" not in attrs_no_date
assert "data-reel-kind" not in attrs_no_date

# Watched films carry a date and an id
films = [{"title": "The Invite", "year": "2026", "rating": "4.5",
          "stars_html": "&#9733;", "link": "https://letterboxd.com/cshields_/film/the-invite-2026/",
          "poster": "p.jpg", "review": "", "date": "2026-08-11"}]
html = u.render_watched(films, "View on Letterboxd")
assert 'id="film-the-invite-2026"' in html, html
assert 'data-reel-date="2026-08-11"' in html
assert 'data-reel-kind="film"' in html

# Read books carry reel attributes
books = [{"title": "The Metamorphosis", "author": "Franz Kafka", "rating": 4,
          "stars_html": "&#9733;", "cover": "c.jpg", "date": "2026-07-18"}]
read_html = u.render_books(books, reel=True)
assert 'id="book-the-metamorphosis"' in read_html
assert 'data-reel-date="2026-07-18"' in read_html
assert 'data-reel-kind="book"' in read_html

# Currently-reading books carry NO reel attributes
cr = [{"title": "The Brothers Karamazov", "author": "Fyodor Dostoevsky", "rating": 0,
       "stars_html": "", "cover": "c.jpg", "date": None}]
cr_html = u.render_currently_reading_block(cr, "Currently Reading")
assert "data-reel-date" not in cr_html, cr_html
assert "data-reel-kind" not in cr_html

print("OK: all update_site.py reel-attribute tests passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 /tmp/test_reel_attrs.py`
Expected: FAIL with `AttributeError: module 'update_site' has no attribute 'rfc822_to_iso'`.

- [ ] **Step 3: Add the helper functions**

In `.github/scripts/update_site.py`, add `from email.utils import parsedate_to_datetime` to the imports, then add these helpers directly after the `BOOK_STARS` dict:

```python
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
    Reel-eligible, so only the id is emitted."""
    attrs = f' id="{item_id}"'
    if not date:
        return attrs
    return (
        f'{attrs} data-reel-date="{date}" data-reel-kind="{kind}"'
        f' data-reel-title="{title}" data-reel-sub="{sub}"'
        f' data-reel-detail="{detail}"'
    )
```

- [ ] **Step 4: Extract the watched-film date and slug**

In `get_recent_watched()`, immediately after the `poster` assignment, add:

```python
        watched_el = item.find("letterboxd:watchedDate", ns)
        watched_date = watched_el.text.strip() if watched_el is not None and watched_el.text else None
        slug_match = re.search(r"/film/([^/]+)/", link)
        film_slug = slug_match.group(1) if slug_match else slugify(title_el.text)
```

Then add these two keys to the dict appended to `films`:

```python
            "date": watched_date,
            "slug": film_slug,
```

- [ ] **Step 5: Extract the book date**

In `get_books()`, immediately after the `cover` handling, add:

```python
        read_at = item.findtext("user_read_at")
        added_at = item.findtext("user_date_added")
        # user_read_at is empty on ~5% of shelf entries; user_date_added is
        # always present and matches it wherever both exist.
        book_date = rfc822_to_iso(read_at) or rfc822_to_iso(added_at)
```

Add `"date": book_date,` to the dict appended to `books`.

In `get_currently_reading()`, add `"date": None,` to the dict appended to `books` — currently-reading entries are not dated events.

- [ ] **Step 6: Emit the attributes from `render_watched()`**

Replace the body of `render_watched()` with:

```python
def render_watched(films, view_on_letterboxd_text):
    cards = []
    seen = set()
    for f in films:
        attrs = reel_attrs(
            unique_id("film", f["slug"], seen), "film", f.get("date"),
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
```

- [ ] **Step 7: Emit the attributes from `render_books()`**

Replace `render_books()` with:

```python
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
```

In `render_currently_reading_block()`, change `items_html = render_books(books)` to `items_html = render_books(books, reel=False)`.

In `main()`, change `books_html = render_books(books)` to `books_html = render_books(books, reel=True)`.

- [ ] **Step 8: Run the test to verify it passes**

Run: `python3 /tmp/test_reel_attrs.py`
Expected: `OK: all update_site.py reel-attribute tests passed`

- [ ] **Step 9: Verify the change is output-neutral apart from the new attributes**

Run:
```bash
cp docs/index.html /tmp/before-en.html
cp docs/es/index.html /tmp/before-es.html
python .github/scripts/update_site.py
diff /tmp/before-en.html docs/index.html | grep -E "^[<>]" | grep -vE "data-reel-|id=\"(film|book)-" | head
```
Expected: no output, or only genuine content drift from the live feed (a newly-watched film). Any structural change to the markup that is not a new `id`/`data-reel-*` attribute is a bug — fix it before continuing.

- [ ] **Step 10: Commit**

```bash
git add .github/scripts/update_site.py docs/index.html docs/es/index.html
git commit -m "Emit reel date and identity attributes from update_site.py"
```

---

### Task 2: Emit dates and reel attributes from `update_strava.py`

**Files:**
- Modify: `.github/scripts/update_strava.py`

**Interfaces:**
- Consumes: the `reel_attrs` contract shape from Task 1 (same attribute names; this script has its own local copy because the two scripts do not import each other).
- Produces: `.route-item` buttons carrying `id="route-<activity-id>"`, `data-reel-date`, `data-reel-kind="route"`, `data-reel-title`, `data-reel-sub`, `data-reel-detail`, plus `data-reel-path` (the SVG path) and `data-reel-viewbox="0 0 400 300"` so the Reel can redraw the trace.

- [ ] **Step 1: Write the failing test**

Create `/tmp/test_strava_reel.py`:

```python
import sys
sys.path.insert(0, ".github/scripts")
import os
os.environ.setdefault("STRAVA_CLIENT_ID", "x")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "x")
os.environ.setdefault("STRAVA_REFRESH_TOKEN", "x")
import update_strava as u

routes = [{
    "id": 987654321, "name": "Holloway Loop", "type": "Run",
    "distance_km": 5.1, "meta": "32:49 · 6:27 /km", "weekday": 2,
    "location": "Holloway, London, UK", "path_d": "M10 20 L30 40",
    "start_xy": (10, 20), "photos": [], "date": "2026-08-12",
}]
html = u.render_routes_html(routes, "en")

for expected in ['id="route-987654321"', 'data-reel-date="2026-08-12"',
                 'data-reel-kind="route"', 'data-reel-title="Holloway Loop"',
                 'data-reel-detail="5.1 km"', 'data-reel-path="M10 20 L30 40"',
                 'data-reel-viewbox="0 0 400 300"']:
    assert expected in html, expected

# The route item is the element carrying them, not the SVG marker
item_tag = html[html.index('<button class="route-item'):]
item_tag = item_tag[:item_tag.index(">") + 1]
assert 'data-reel-date="2026-08-12"' in item_tag, item_tag

print("OK: all update_strava.py reel-attribute tests passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 /tmp/test_strava_reel.py`
Expected: FAIL with `AssertionError: id="route-987654321"`.

- [ ] **Step 3: Keep the ISO date and activity id**

In `get_activities()`, the `datetime` import and `dt` assignment already exist at lines 216-217. Add these two keys to the dict appended to `routes`:

```python
            "id": act["id"],
            "date": dt.date().isoformat(),
```

- [ ] **Step 4: Add the local `reel_attrs` helper**

Add directly above `render_routes_html()`:

```python
def reel_attrs(item_id, kind, date, title, sub, detail, extra=""):
    """Mirrors the contract in update_site.py; update_reel.py reads these."""
    attrs = f' id="{item_id}"'
    if not date:
        return attrs
    return (
        f'{attrs} data-reel-date="{date}" data-reel-kind="{kind}"'
        f' data-reel-title="{title}" data-reel-sub="{sub}"'
        f' data-reel-detail="{detail}"{extra}'
    )
```

- [ ] **Step 5: Emit the attributes on the route item**

In `render_routes_html()`, inside the `for i, r in enumerate(routes)` loop, add immediately before the `list_items.append(...)` call:

```python
        reel = reel_attrs(
            f"route-{r['id']}", "route", r.get("date"), esc(r["name"]), loc,
            f"{r['distance_km']} km",
            extra=f' data-reel-path="{r["path_d"]}" data-reel-viewbox="0 0 {VIEWBOX_W} {VIEWBOX_H}"',
        )
```

Then change the first line of the `list_items.append(...)` f-string from:

```python
            f'<button class="route-item{active}" data-route="{i}" data-dist="{r["distance_km"]} km" '
```

to:

```python
            f'<button class="route-item{active}"{reel} data-route="{i}" data-dist="{r["distance_km"]} km" '
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python3 /tmp/test_strava_reel.py`
Expected: `OK: all update_strava.py reel-attribute tests passed`

- [ ] **Step 7: Commit**

```bash
git add .github/scripts/update_strava.py
git commit -m "Emit reel date and identity attributes from update_strava.py"
```

Note: this script cannot be run locally without Strava secrets, so `docs/*.html` is not regenerated here. The route attributes appear on the next scheduled or dispatched `update-strava.yml` run, verified in Task 9.

---

### Task 3: Add the Reel section skeleton to both language files

**Files:**
- Modify: `docs/index.html`
- Modify: `docs/es/index.html`

**Interfaces:**
- Consumes: nothing.
- Produces: `<section id="reel">` containing `#reel-track` (the scroll container, with the `SITE-REEL` marker pair inside it), `#reel-readout`, `#reel-ruler`, `#reel-prev`, `#reel-next`; and a `#reel` nav link in both the desktop and mobile menus. `#reel-readout` carries `data-frame-label` for the localised "Frame NN / TT" string.

- [ ] **Step 1: Insert the section into `docs/index.html`**

The section goes between the Career section's closing `</section>` (ends at line 173) and `<section class="section films" id="films">` (line 174). Insert:

```html
<section class="section reel" id="reel">
<div class="container">
<div class="section-header reveal">
<span class="section-label">Reel — Last 90 Days</span>
<h2 class="section-title">The Reel</h2>
</div>
<p class="reel-intro reveal">Everything watched, read, run and shipped, in order, on one strip. Drag it through the gate.</p>
</div>
<div class="reel-stage">
<div class="reel-gate" aria-hidden="true"><div class="reel-gate-glow"></div></div>
<div class="reel-rail reel-rail-top" aria-hidden="true"></div>
<div class="reel-track" id="reel-track" tabindex="0" aria-label="The Reel — films, books, runs and commits in date order">
<!-- SITE-REEL:START --><!-- SITE-REEL:END -->
</div>
<div class="reel-rail reel-rail-bot" aria-hidden="true"></div>
</div>
<div class="container">
<div class="reel-readout" id="reel-readout" data-frame-label="Frame" aria-live="polite"></div>
<div class="reel-ruler" id="reel-ruler"></div>
<div class="reel-controls">
<button class="reel-ctrl" id="reel-prev" type="button">&larr; Prev frame</button>
<button class="reel-ctrl" id="reel-next" type="button">Next frame &rarr;</button>
</div>
</div>
</section>
```

- [ ] **Step 2: Insert the Spanish section into `docs/es/index.html`**

At the same position (between the Career section's `</section>` and `<section class="section films" id="films">`), insert:

```html
<section class="section reel" id="reel">
<div class="container">
<div class="section-header reveal">
<span class="section-label">Bobina — Últimos 90 Días</span>
<h2 class="section-title">La Bobina</h2>
</div>
<p class="reel-intro reveal">Todo lo visto, leído, corrido y publicado, en orden, en una sola tira. Arrástrala por la ventanilla.</p>
</div>
<div class="reel-stage">
<div class="reel-gate" aria-hidden="true"><div class="reel-gate-glow"></div></div>
<div class="reel-rail reel-rail-top" aria-hidden="true"></div>
<div class="reel-track" id="reel-track" tabindex="0" aria-label="La Bobina — películas, libros, carreras y commits en orden de fecha">
<!-- SITE-REEL:START --><!-- SITE-REEL:END -->
</div>
<div class="reel-rail reel-rail-bot" aria-hidden="true"></div>
</div>
<div class="container">
<div class="reel-readout" id="reel-readout" data-frame-label="Fotograma" aria-live="polite"></div>
<div class="reel-ruler" id="reel-ruler"></div>
<div class="reel-controls">
<button class="reel-ctrl" id="reel-prev" type="button">&larr; Fotograma anterior</button>
<button class="reel-ctrl" id="reel-next" type="button">Siguiente fotograma &rarr;</button>
</div>
</div>
</section>
```

- [ ] **Step 3: Add the nav links**

In `docs/index.html`, in **both** the `.nav-links` block (line 18) and the `.mobile-menu` block (line 32), insert after the `#experience` link:

```html
<a href="#reel">The Reel</a>
```

In `docs/es/index.html`, in both the same blocks, insert after the `#experience` link:

```html
<a href="#reel">La Bobina</a>
```

- [ ] **Step 4: Verify the structure**

Run:
```bash
grep -c 'id="reel"' docs/index.html docs/es/index.html
grep -c 'SITE-REEL:START' docs/index.html docs/es/index.html
grep -c 'href="#reel"' docs/index.html docs/es/index.html
```
Expected: `1` for the first two in each file, `2` for the nav links in each file (desktop + mobile).

- [ ] **Step 5: Verify section order**

Run: `grep -n '<section class="section' docs/index.html docs/es/index.html`
Expected: in each file, `reel` appears after `experience` and before `films`.

- [ ] **Step 6: Commit**

```bash
git add docs/index.html docs/es/index.html
git commit -m "Add The Reel section skeleton and nav links"
```

---

### Task 4: Scrape, window and sort reel items

**Files:**
- Create: `.github/scripts/update_reel.py`

**Interfaces:**
- Consumes: the `data-reel-*` attribute contract produced by Tasks 1 and 2.
- Produces: `parse_items(html) -> list[dict]` where each dict has keys `kind, date, target, title, sub, detail, path_d, viewbox`; `within_window(items, today, days=90) -> list[dict]` (adds a `_d` `datetime.date` key and sorts ascending); `month_buckets(start, end) -> list[tuple[date, date]]`; and the module constants `WINDOW_DAYS`, `KIND_ORDER`, `SITE_PATHS`, `SOURCE_PATH`, `MIN_FRAMES`.

- [ ] **Step 1: Write the failing test**

Create `/tmp/test_reel_parse.py`:

```python
import sys
sys.path.insert(0, ".github/scripts")
from datetime import date
import update_reel as r

FIXTURE = """
<a href="x" class="film-card" id="film-the-invite-2026" data-reel-date="2026-08-11"
   data-reel-kind="film" data-reel-title="The Invite" data-reel-sub="2026"
   data-reel-detail="&#9733;&#9733;&#9733;&#9733;&#189;" target="_blank">poster</a>
<div class="book-item" id="book-the-metamorphosis" data-reel-date="2026-07-18"
     data-reel-kind="book" data-reel-title="The Metamorphosis" data-reel-sub="Franz Kafka"
     data-reel-detail="&#9733;&#9733;&#9733;&#9733;">cover</div>
<button class="route-item active" id="route-987" data-reel-date="2026-08-12"
        data-reel-kind="route" data-reel-title="Holloway Loop" data-reel-sub="London, UK"
        data-reel-detail="5.1 km" data-reel-path="M10 20 L30 40"
        data-reel-viewbox="0 0 400 300" data-route="0">item</button>
<div class="book-item" id="book-no-date">undated, must be skipped</div>
<div class="book-item" id="book-old" data-reel-date="2020-01-01" data-reel-kind="book"
     data-reel-title="Old" data-reel-sub="X" data-reel-detail="">outside window</div>
"""

items = r.parse_items(FIXTURE)
assert len(items) == 4, items          # the undated book is excluded
kinds = sorted(i["kind"] for i in items)
assert kinds == ["book", "book", "film", "route"], kinds

film = next(i for i in items if i["kind"] == "film")
assert film["target"] == "film-the-invite-2026"
assert film["title"] == "The Invite"
assert film["detail"] == "&#9733;&#9733;&#9733;&#9733;&#189;"   # not re-escaped

route = next(i for i in items if i["kind"] == "route")
assert route["path_d"] == "M10 20 L30 40"
assert route["viewbox"] == "0 0 400 300"

# 90-day window, sorted ascending, tie-break by kind order
today = date(2026, 8, 24)
kept = r.within_window(items, today)
assert [i["target"] for i in kept] == [
    "book-the-metamorphosis", "film-the-invite-2026", "route-987"], [i["target"] for i in kept]

# A watched date one day ahead of the build date is kept (Letterboxd feeds
# report in +1200, so "tomorrow" in UTC terms is normal)
future = r.parse_items(
    '<a class="film-card" id="film-f" data-reel-date="2026-08-25" data-reel-kind="film"'
    ' data-reel-title="F" data-reel-sub="" data-reel-detail="">x</a>')
assert len(r.within_window(future, today)) == 1

# Two days ahead is a data error and is dropped
too_far = r.parse_items(
    '<a class="film-card" id="film-g" data-reel-date="2026-08-27" data-reel-kind="film"'
    ' data-reel-title="G" data-reel-sub="" data-reel-detail="">x</a>')
assert len(r.within_window(too_far, today)) == 0

# Month buckets clamp to the window end
buckets = r.month_buckets(date(2026, 5, 26), date(2026, 8, 24))
assert buckets == [
    (date(2026, 5, 26), date(2026, 5, 31)),
    (date(2026, 6, 1), date(2026, 6, 30)),
    (date(2026, 7, 1), date(2026, 7, 31)),
    (date(2026, 8, 1), date(2026, 8, 24)),
], buckets

# December rolls the year over correctly
assert r.month_buckets(date(2026, 12, 5), date(2027, 1, 10)) == [
    (date(2026, 12, 5), date(2026, 12, 31)),
    (date(2027, 1, 1), date(2027, 1, 10)),
]

print("OK: all update_reel.py parse/window tests passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 /tmp/test_reel_parse.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'update_reel'`.

- [ ] **Step 3: Create the script with the parsing and windowing functions**

Create `.github/scripts/update_reel.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 /tmp/test_reel_parse.py`
Expected: `OK: all update_reel.py parse/window tests passed`

- [ ] **Step 5: Verify it parses the real page**

Run:
```bash
python3 -c "
import sys; sys.path.insert(0, '.github/scripts')
import update_reel as r
from datetime import date
items = r.within_window(r.parse_items(open('docs/index.html').read()), date.today())
print(f'{len(items)} items in window')
for i in items[:5]: print(' ', i['_d'], i['kind'], i['target'])
"
```
Expected: a non-zero count of `film` and `book` items in ascending date order. `route` items appear only after `update-strava.yml` has run (Task 9).

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/update_reel.py
git commit -m "Add reel item scraping and 90-day windowing"
```

---

### Task 5: Fetch monthly commit counts

**Files:**
- Modify: `.github/scripts/update_reel.py`

**Interfaces:**
- Consumes: `month_buckets()` from Task 4.
- Produces: `fetch_commit_counts(buckets, token) -> dict[tuple[int, int], int]` keyed by `(year, month)`, and `commit_items(counts, buckets) -> list[dict]` returning `kind="code"` items shaped like the scraped ones (`date`, `target`, `title`, `sub`, `detail`) so they merge into the same sorted list.

- [ ] **Step 1: Write the failing test**

Create `/tmp/test_reel_commits.py`:

```python
import sys
sys.path.insert(0, ".github/scripts")
from datetime import date
import update_reel as r

buckets = [(date(2026, 7, 1), date(2026, 7, 31)), (date(2026, 8, 1), date(2026, 8, 24))]
counts = {(2026, 7): 308, (2026, 8): 341}
items = r.commit_items(counts, buckets)

assert len(items) == 2, items
assert all(i["kind"] == "code" for i in items)
# A commit frame is dated at the end of its bucket so it sits after that
# month's content rather than before it.
assert items[0]["date"] == "2026-07-31", items[0]
assert items[1]["date"] == "2026-08-24", items[1]
assert items[0]["detail"] == "308"
assert items[1]["detail"] == "341"
assert items[0]["target"] == ""   # commit frames link off-site, not to an id

# A month with no data is skipped rather than rendered as zero
assert r.commit_items({(2026, 8): 341}, buckets) == [i for i in items if i["date"] == "2026-08-24"]

print("OK: all update_reel.py commit tests passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 /tmp/test_reel_commits.py`
Expected: FAIL with `AttributeError: module 'update_reel' has no attribute 'commit_items'`.

- [ ] **Step 3: Add the query, fetch and item builder**

Append to `.github/scripts/update_reel.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 /tmp/test_reel_commits.py`
Expected: `OK: all update_reel.py commit tests passed`

- [ ] **Step 5: Commit**

```bash
git add .github/scripts/update_reel.py
git commit -m "Add monthly commit counts to the reel builder"
```

---

### Task 6: Render frames and inject the block

**Files:**
- Modify: `.github/scripts/update_reel.py`

**Interfaces:**
- Consumes: `parse_items`, `within_window`, `month_buckets`, `fetch_commit_counts`, `commit_items`.
- Produces: `render_frame(item, lang) -> str`, `render_reel(items, lang) -> str`, `inject(html, block, path) -> str`, `main()`. Frames are `<a class="reel-frame k-<kind>">` carrying `data-month`, `data-r-date`, `data-r-kind`, `data-r-title`, `data-r-sub`, `data-r-detail` — the attributes `initReel()` reads for the readout and ruler.

**Note on markup:** frames are anchors, so every child element must be phrasing content — use `<span>`, never `<div>`.

- [ ] **Step 1: Write the failing test**

Create `/tmp/test_reel_render.py`:

```python
import sys
sys.path.insert(0, ".github/scripts")
from datetime import date
import update_reel as r

film = {"kind": "film", "date": "2026-08-11", "_d": date(2026, 8, 11),
        "target": "film-the-invite-2026", "title": "The Invite", "sub": "2026",
        "detail": "&#9733;&#9733;&#9733;&#9733;&#189;", "path_d": "", "viewbox": ""}
book = {"kind": "book", "date": "2026-07-18", "_d": date(2026, 7, 18),
        "target": "book-the-metamorphosis", "title": "The Metamorphosis",
        "sub": "Franz Kafka", "detail": "&#9733;&#9733;&#9733;&#9733;",
        "path_d": "", "viewbox": ""}
route = {"kind": "route", "date": "2026-08-12", "_d": date(2026, 8, 12),
         "target": "route-987", "title": "Holloway Loop", "sub": "London, UK",
         "detail": "5.1 km", "path_d": "M10 20 L30 40", "viewbox": "0 0 400 300"}
code = {"kind": "code", "date": "2026-08-24", "_d": date(2026, 8, 24),
        "target": "", "title": "", "sub": "", "detail": "341",
        "path_d": "", "viewbox": ""}

f = r.render_frame(film, "en")
assert 'href="#film-the-invite-2026"' in f, f
assert 'class="reel-frame k-film"' in f
assert 'data-month="AUG"' in f
assert 'data-r-date="11 Aug"' in f
assert "Now Showing" in f
assert "&#9733;&#9733;&#9733;&#9733;&#189;" in f      # passed through, not re-escaped
assert "&amp;#9733;" not in f
assert "<div" not in f                                # anchors take phrasing content only

b = r.render_frame(book, "en")
assert 'class="reel-frame k-book"' in b
assert "Intermission" in b
assert 'class="reel-inset"' in b

rt = r.render_frame(route, "en")
assert 'href="#route-987"' in rt
assert 'viewBox="0 0 400 300"' in rt
assert 'd="M10 20 L30 40"' in rt
assert "On Location" in rt

c = r.render_frame(code, "en")
assert 'href="https://github.com/cshields236"' in c, c
assert "Box Office" in c
assert "341" in c
assert 'class="reel-bar"' in c

# Spanish labels
assert "En Cartelera" in r.render_frame(film, "es")
assert "Intermedio" in r.render_frame(book, "es")
assert "Exteriores" in r.render_frame(route, "es")
assert "Taquilla" in r.render_frame(code, "es")
assert 'data-month="AGO"' in r.render_frame(film, "es")

# Fewer than MIN_FRAMES renders nothing
assert r.render_reel([film], "en") == ""
assert r.render_reel([], "en") == ""
block = r.render_reel([film, book, route, code], "en")
assert block.count("reel-frame") == 4

# Injection replaces the marker block and fails loudly when absent
page = '<div><!-- SITE-REEL:START -->old<!-- SITE-REEL:END --></div>'
out = r.inject(page, "NEW", "docs/index.html")
assert "NEW" in out and "old" not in out
assert "SITE-REEL:START" in out and "SITE-REEL:END" in out
try:
    r.inject("<div>no markers</div>", "NEW", "docs/index.html")
except SystemExit as e:
    assert "SITE-REEL" in str(e)
else:
    raise AssertionError("inject() must raise SystemExit when the marker is missing")

print("OK: all update_reel.py render tests passed")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 /tmp/test_reel_render.py`
Expected: FAIL with `AttributeError: module 'update_reel' has no attribute 'render_frame'`.

- [ ] **Step 3: Add the copy tables**

Append to `.github/scripts/update_reel.py`:

```python
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
```

- [ ] **Step 4: Add the frame renderer**

Append:

```python
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
```

- [ ] **Step 5: Add injection and `main()`**

Append:

```python
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
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `python3 /tmp/test_reel_render.py`
Expected: `OK: all update_reel.py render tests passed`

- [ ] **Step 7: Run the script end to end against the real page**

Needs a token with `read:user`. Run:
```bash
GITHUB_TOKEN=$(gh auth token) python .github/scripts/update_reel.py
```
Expected: `Updated 2 site file(s) with N reel frames: {...}` where N is roughly 20-30 (`route` will be 0 until Task 9).

Then confirm both files were written:
```bash
grep -c 'class="reel-frame' docs/index.html docs/es/index.html
```
Expected: the same non-zero count in both files.

- [ ] **Step 8: Commit**

```bash
git add .github/scripts/update_reel.py docs/index.html docs/es/index.html
git commit -m "Render reel frames and inject them into both site files"
```

---

### Task 7: Style the Reel

**Files:**
- Modify: `docs/style.css`

**Interfaces:**
- Consumes: the class names emitted in Tasks 3 and 6 (`.reel`, `.reel-stage`, `.reel-gate`, `.reel-rail`, `.reel-track`, `.reel-frame`, `.k-film|k-book|k-route|k-code`, `.reel-kind`, `.reel-body`, `.reel-inset`, `.reel-title`, `.reel-sub`, `.reel-stars`, `.reel-num`, `.reel-route`, `.reel-bars`, `.reel-bar`, `.reel-readout`, `.reel-ruler`, `.reel-controls`, `.reel-ctrl`, `.reel-intro`).
- Produces: the `--emulsion` token and a `.in-gate` class contract that `initReel()` toggles in Task 8.

- [ ] **Step 1: Add the `--emulsion` token**

In the `:root` block at the top of `docs/style.css`, add after `--bg-alt`:

```css
    --emulsion: #081310;
```

- [ ] **Step 2: Add the Reel block**

Append to `docs/style.css`, before the `@media print` block:

```css
/* ─── The Reel ─── */
.reel-intro {
    max-width: 52ch;
    color: var(--text-muted);
    margin-top: 0.9rem;
}

.reel-stage {
    position: relative;
    margin-top: 2.6rem;
    background: var(--emulsion);
    border-top: 1px solid var(--line);
    border-bottom: 1px solid var(--line);
    /* full-bleed escape from the centred .container */
    width: 100vw;
    margin-left: calc(50% - 50vw);
}

.reel-rail {
    height: 22px;
    background-image: repeating-linear-gradient(90deg,
        transparent 0 12px,
        rgba(242, 233, 214, 0.82) 12px 26px,
        transparent 26px 38px);
    background-size: auto 9px;
    background-position: center;
    background-repeat: repeat-x;
    opacity: 0.5;
}

.reel-rail-top { border-bottom: 1px solid rgba(239, 230, 208, 0.08); }
.reel-rail-bot { border-top: 1px solid rgba(239, 230, 208, 0.08); }

.reel-gate {
    position: absolute;
    top: 22px;
    bottom: 22px;
    left: 50%;
    transform: translateX(-50%);
    width: 206px;
    pointer-events: none;
    z-index: 3;
}

.reel-gate::before,
.reel-gate::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    height: 14px;
    border-left: 2px solid var(--crimson);
    border-right: 2px solid var(--crimson);
}

.reel-gate::before { top: 0; border-top: 2px solid var(--crimson); }
.reel-gate::after { bottom: 0; border-bottom: 2px solid var(--crimson); }

.reel-gate-glow {
    position: absolute;
    inset: 0;
    box-shadow: 0 0 0 100vmax rgba(8, 19, 16, 0.62);
}

.reel-track {
    display: flex;
    overflow-x: auto;
    overflow-y: hidden;
    cursor: grab;
    scrollbar-width: none;
    -ms-overflow-style: none;
    /* lets the first and last frame reach the centre gate */
    padding: 0 calc(50vw - 100px);
}

.reel-track::-webkit-scrollbar { display: none; }
.reel-track.dragging { cursor: grabbing; }

.reel-frame {
    flex: 0 0 200px;
    height: 270px;
    position: relative;
    display: flex;
    flex-direction: column;
    padding: 14px 12px;
    border-right: 1px solid rgba(239, 230, 208, 0.1);
    background: var(--emulsion);
    text-decoration: none;
    color: var(--text);
    opacity: 0.34;
    transform: scale(0.94);
    transition: opacity 0.45s var(--ease-smooth), transform 0.45s var(--ease-smooth);
}

.reel-frame.in-gate {
    opacity: 1;
    transform: scale(1);
}

.reel-kind {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: auto;
    font-family: var(--mono);
    font-size: 0.55rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-dim);
}

.reel-kind em {
    font-style: normal;
    margin-left: auto;
}

.reel-kind i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex: 0 0 auto;
}

.k-film .reel-kind i { background: var(--crimson); }
.k-book .reel-kind i { background: var(--paper-dim); }
.k-route .reel-kind i { background: #6f9b7f; }
.k-code .reel-kind i { background: #c9a227; }

.reel-body {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}

.reel-title {
    font-family: var(--display);
    font-weight: 800;
    text-transform: uppercase;
    font-size: 1.3rem;
    line-height: 0.94;
}

.reel-sub {
    font-size: 0.8rem;
    color: var(--text-muted);
    font-style: italic;
    line-height: 1.3;
}

.reel-stars {
    font-family: var(--mono);
    font-size: 0.78rem;
    color: var(--crimson);
}

.reel-num {
    font-family: var(--display);
    font-weight: 800;
    font-size: 2.2rem;
    line-height: 0.85;
    color: var(--paper);
    font-variant-numeric: tabular-nums;
}

.reel-num small {
    display: block;
    margin-top: 0.25rem;
    font-family: var(--mono);
    font-size: 0.6rem;
    font-weight: 400;
    letter-spacing: 0.14em;
    color: var(--text-dim);
}

.reel-inset {
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    gap: 0.3rem;
    flex: 1;
    margin: 0 -12px -14px;
    padding: 12px;
    background: var(--paper);
    color: var(--ink);
}

.reel-inset .reel-title { font-size: 1.1rem; }
.reel-inset .reel-sub { color: #5c5647; }

.reel-route {
    width: 100%;
    height: 96px;
    margin-bottom: 0.4rem;
}

.reel-route path {
    fill: none;
    stroke: #6f9b7f;
    stroke-width: 4;
    stroke-linecap: round;
}

.reel-bars {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 80px;
    margin-bottom: 0.5rem;
}

.reel-bar {
    flex: 1;
    background: rgba(201, 162, 39, 0.55);
}

.reel-readout {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.6rem 1.6rem;
    padding: 1rem 0;
    border-bottom: 1px solid var(--line);
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
}

.reel-readout .r-title {
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.3rem;
    letter-spacing: 0.02em;
    color: var(--text);
}

.reel-readout .r-meta { color: var(--text-muted); }

.reel-readout .r-count {
    margin-left: auto;
    font-variant-numeric: tabular-nums;
}

.reel-ruler {
    display: flex;
    border-bottom: 1px solid var(--line);
}

.reel-ruler button {
    flex: 1;
    padding: 0.7rem 0.3rem;
    background: none;
    border: 0;
    border-right: 1px solid var(--line);
    color: var(--text-dim);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 0.63rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    transition: color 0.25s, background 0.25s;
}

.reel-ruler button:last-child { border-right: 0; }
.reel-ruler button:hover { color: var(--text); }

.reel-ruler button.active {
    color: var(--crimson);
    background: var(--crimson-soft);
}

.reel-controls {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 1.4rem;
}

.reel-ctrl {
    padding: 0.6rem 1rem;
    background: none;
    border: 1px solid var(--line-strong);
    color: var(--text-muted);
    cursor: pointer;
    font-family: var(--mono);
    font-size: 0.63rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    transition: border-color 0.25s, color 0.25s, background 0.25s;
}

.reel-ctrl:hover {
    border-color: var(--crimson);
    color: var(--text);
    background: var(--crimson-soft);
}

/* Arrival highlight for a frame's scroll target — no JS involved */
#films .film-card:target,
#books .book-item:target,
#routes .route-item:target {
    outline: 2px solid var(--crimson);
    outline-offset: 4px;
}

@media (prefers-reduced-motion: reduce) {
    .reel-frame { transition: none; }
    .reel-track { scroll-behavior: auto; }
}

@media (max-width: 700px) {
    .reel-frame { flex: 0 0 160px; height: 230px; }
    .reel-gate { width: 166px; }
    .reel-track { padding: 0 calc(50vw - 80px); }
}
```

- [ ] **Step 3: Add the Reel to the print hide-list**

In the `@media print` block, change:

```css
    .section.films, .section.routes, .section.books,
```

to:

```css
    .section.films, .section.routes, .section.books, .section.reel,
```

- [ ] **Step 4: Verify the CSS**

Run:
```bash
grep -c "^\.reel\|^\.k-film\|--emulsion" docs/style.css
grep -n "section.reel" docs/style.css
python3 -c "
css = open('docs/style.css').read()
assert css.count('{') == css.count('}'), f\"unbalanced braces: {css.count('{')} open, {css.count('}')} close\"
print('OK: braces balanced')
"
```
Expected: a non-zero count, one `section.reel` hit inside the print block, and `OK: braces balanced`.

- [ ] **Step 5: Visual check**

Open `docs/index.html` in a browser. Expected: the strip renders full-bleed with sprocket rails above and below, frames are dim (the gate JS is not written yet, so nothing is highlighted), and the page does not scroll sideways.

- [ ] **Step 6: Commit**

```bash
git add docs/style.css
git commit -m "Style The Reel strip, gate, readout and ruler"
```

---

### Task 8: Add `initReel()` to `main.js`

**Files:**
- Modify: `docs/main.js`

**Interfaces:**
- Consumes: `#reel`, `#reel-track`, `#reel-readout` (with `data-frame-label`), `#reel-ruler`, `#reel-prev`, `#reel-next`, `.reel-frame[data-month][data-r-date][data-r-kind][data-r-title][data-r-sub][data-r-detail]`, and the `.in-gate` class from Task 7.
- Produces: `initReel()`, called from the `DOMContentLoaded` handler.

- [ ] **Step 1: Register the call**

In `docs/main.js`, in the `DOMContentLoaded` handler, add after `initRoutes();` (line 54):

```javascript
    initReel();
```

- [ ] **Step 2: Add the function**

Append to `docs/main.js`:

```javascript
/* The Reel: a native horizontal scroll container whose "current" frame is
   derived from proximity to the centre gate rather than tracked as state. */
function initReel() {
    const section = document.getElementById('reel');
    const track = document.getElementById('reel-track');
    if (!section || !track) return;

    const frames = Array.from(track.querySelectorAll('.reel-frame'));
    if (frames.length < 2) {
        section.hidden = true;
        return;
    }

    const readout = document.getElementById('reel-readout');
    const ruler = document.getElementById('reel-ruler');
    const frameLabel = readout ? readout.dataset.frameLabel : 'Frame';
    let current = -1;

    const centreOf = el => el.offsetLeft + el.offsetWidth / 2;

    function scrollToFrame(i) {
        const clamped = Math.max(0, Math.min(frames.length - 1, i));
        track.scrollTo({
            left: centreOf(frames[clamped]) - track.clientWidth / 2,
            behavior: 'smooth'
        });
    }

    const months = [];
    frames.forEach(f => {
        const m = f.dataset.month;
        if (m && !months.includes(m)) months.push(m);
    });

    months.forEach(month => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = month;
        btn.dataset.month = month;
        btn.addEventListener('click', () => {
            scrollToFrame(frames.findIndex(f => f.dataset.month === month));
        });
        ruler.appendChild(btn);
    });

    function updateGate() {
        const mid = track.scrollLeft + track.clientWidth / 2;
        let best = 0;
        let bestDist = Infinity;
        frames.forEach((el, i) => {
            const dist = Math.abs(centreOf(el) - mid);
            if (dist < bestDist) {
                bestDist = dist;
                best = i;
            }
        });
        if (best === current) return;
        current = best;

        frames.forEach((el, i) => el.classList.toggle('in-gate', i === best));

        const f = frames[best];
        readout.innerHTML =
            '<span>' + f.dataset.rDate + '</span>' +
            '<span class="r-title">' + (f.dataset.rTitle || f.dataset.rKind) + '</span>' +
            '<span class="r-meta">' + (f.dataset.rSub || '') + '</span>' +
            '<span class="r-meta">' + (f.dataset.rDetail || '') + '</span>' +
            '<span class="r-count">' + frameLabel + ' ' +
            String(best + 1).padStart(2, '0') + ' / ' + frames.length + '</span>';

        Array.from(ruler.children).forEach(btn => {
            btn.classList.toggle('active', btn.dataset.month === f.dataset.month);
        });
    }

    let ticking = false;
    track.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(() => {
            ticking = false;
            updateGate();
        });
    });

    let down = false;
    let startX = 0;
    let startScroll = 0;
    let moved = 0;

    track.addEventListener('pointerdown', e => {
        down = true;
        moved = 0;
        startX = e.clientX;
        startScroll = track.scrollLeft;
        track.classList.add('dragging');
        track.setPointerCapture(e.pointerId);
    });

    track.addEventListener('pointermove', e => {
        if (!down) return;
        const dx = e.clientX - startX;
        moved = Math.max(moved, Math.abs(dx));
        track.scrollLeft = startScroll - dx;
    });

    function endDrag() {
        if (!down) return;
        down = false;
        track.classList.remove('dragging');
        scrollToFrame(current);
    }

    track.addEventListener('pointerup', endDrag);
    track.addEventListener('pointercancel', endDrag);

    /* A drag that ends on a frame must not also navigate. */
    track.addEventListener('click', e => {
        if (moved > 6) e.preventDefault();
    });

    track.addEventListener('keydown', e => {
        if (e.key === 'ArrowRight') {
            e.preventDefault();
            scrollToFrame(current + 1);
        }
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            scrollToFrame(current - 1);
        }
    });

    document.getElementById('reel-prev').addEventListener('click', () => scrollToFrame(current - 1));
    document.getElementById('reel-next').addEventListener('click', () => scrollToFrame(current + 1));

    /* .route-item is a button that switches the routes sketch, so :target
       alone would highlight it while the sketch showed a different trace. */
    function activateRouteFromHash() {
        const id = window.location.hash.slice(1);
        if (!id.startsWith('route-')) return;
        const item = document.getElementById(id);
        if (item && item.classList.contains('route-item')) item.click();
    }

    window.addEventListener('hashchange', activateRouteFromHash);
    activateRouteFromHash();

    scrollToFrame(0);
    updateGate();
}
```

- [ ] **Step 3: Verify it is wired in once**

Run: `grep -n "initReel" docs/main.js`
Expected: exactly two hits — the call inside `DOMContentLoaded` and the function definition.

- [ ] **Step 4: Browser verification**

Open `docs/index.html` and confirm each of:
- The frame at the centre of the gate is bright; the others are dimmed.
- Dragging the strip moves it and it snaps to a frame on release.
- The readout updates as the gated frame changes, and shows `Frame NN / TT`.
- The month ruler renders one button per month and clicking one jumps to it.
- `Prev frame` / `Next frame` step one frame.
- Clicking the track then pressing `←` / `→` steps one frame.
- Clicking a film frame scrolls to *Now Showing* with a crimson outline on that poster; the same for a book frame and *Reading List*.
- A commit frame opens GitHub in a new tab.
- Dragging across a frame and releasing does **not** navigate.

Then confirm no regressions: the films carousel arrows, a film review flip, the routes list switching the sketch, the email ticket modal and the contact-form casting modal.

- [ ] **Step 5: Verify the empty guard**

Run:
```bash
python3 -c "
import re
html = open('docs/index.html').read()
stub = re.sub(r'<!-- SITE-REEL:START -->.*?<!-- SITE-REEL:END -->',
              '<!-- SITE-REEL:START --><!-- SITE-REEL:END -->', html, flags=re.DOTALL)
open('/tmp/reel-empty.html', 'w').write(stub)
print('wrote /tmp/reel-empty.html')
"
cp docs/style.css docs/main.js /tmp/
```
Open `/tmp/reel-empty.html`. Expected: the Reel section is hidden entirely (no empty strip, no orphan readout or ruler).

- [ ] **Step 6: Commit**

```bash
git add docs/main.js
git commit -m "Add initReel gate tracking, scrubbing and route activation"
```

---

### Task 9: Add the workflow and verify end to end

**Files:**
- Create: `.github/workflows/update-reel.yml`

**Interfaces:**
- Consumes: `.github/scripts/update_reel.py` from Tasks 4-6.
- Produces: a scheduled build that writes the `SITE-REEL` block to both site files.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/update-reel.yml`:

```yaml
name: Update site with the reel
on:
  schedule:
    - cron: "55 5 * * *"
  workflow_dispatch:
jobs:
  update-reel:
    name: Update reel strip
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Update reel HTML
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python .github/scripts/update_reel.py
      - name: Commit and push if changed
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git diff --quiet || (git add docs/index.html docs/es/index.html && git commit -m "Update site with the reel" && git push)
```

- [ ] **Step 2: Verify the cron stagger**

Run: `grep -n "cron:" .github/workflows/*.yml`
Expected: `goodreads` and `letterboxd` at `0 5`, `update-site` at `15 5`, `update-strava` at `45 5`, `update-reel` at `55 5` — the Reel runs last, after every source section is written for the day.

- [ ] **Step 3: Verify the YAML parses**

Run:
```bash
python3 -c "
import re
text = open('.github/workflows/update-reel.yml').read()
assert '\t' not in text, 'tabs are invalid in YAML'
assert 'GITHUB_TOKEN' in text and 'permissions' in text
print('OK: workflow shape valid')
"
```
Expected: `OK: workflow shape valid`

- [ ] **Step 4: Commit and push the branch**

```bash
git add .github/workflows/update-reel.yml
git commit -m "Add update-reel workflow on a 5:55 UTC schedule"
git push -u origin HEAD
```

- [ ] **Step 5: Dispatch the source workflows and confirm the route attributes**

Run:
```bash
gh workflow run update-strava.yml --ref "$(git branch --show-current)"
```
Wait for it to finish (`gh run watch`), then:
```bash
git pull
grep -o 'id="route-[0-9]*"' docs/index.html | head
```
Expected: several `id="route-<numeric-id>"` hits. If empty, `update_strava.py`'s attribute emission (Task 2) is wrong — fix before continuing.

- [ ] **Step 6: Dispatch the reel workflow and confirm route frames appear**

Run:
```bash
gh workflow run update-reel.yml --ref "$(git branch --show-current)"
gh run watch
git pull
python3 -c "
import re
html = open('docs/index.html').read()
block = re.search(r'<!-- SITE-REEL:START -->(.*?)<!-- SITE-REEL:END -->', html, re.DOTALL).group(1)
kinds = re.findall(r'reel-frame k-(\w+)', block)
dates = re.findall(r'data-reel-date=\"([^\"]+)\"', html)
from collections import Counter
print('frames by kind:', Counter(kinds))
assert kinds, 'no frames rendered'
assert 'route' in kinds, 'route frames missing — check update_strava attributes'
assert 'code' in kinds, 'commit frames missing — check GITHUB_TOKEN scope'
print('OK: all four frame kinds present')
"
```
Expected: `OK: all four frame kinds present`, with roughly 20-30 frames total.

- [ ] **Step 7: Verify frames are in ascending date order**

Run:
```bash
python3 -c "
import re
html = open('docs/index.html').read()
block = re.search(r'<!-- SITE-REEL:START -->(.*?)<!-- SITE-REEL:END -->', html, re.DOTALL).group(1)
dates = re.findall(r'data-r-date=\"([^\"]+)\"', block)
months = re.findall(r'data-month=\"([^\"]+)\"', block)
print(' -> '.join(dates))
assert months == sorted(months, key=lambda m: months.index(m)), 'months out of order'
print('OK: frames in ascending order')
"
```
Expected: the dates read left to right oldest to newest, and `OK: frames in ascending order`.

- [ ] **Step 8: Verify bilingual parity**

Run:
```bash
python3 -c "
import re
for path in ('docs/index.html', 'docs/es/index.html'):
    html = open(path).read()
    block = re.search(r'<!-- SITE-REEL:START -->(.*?)<!-- SITE-REEL:END -->', html, re.DOTALL).group(1)
    print(path, block.count('reel-frame'), 'frames')
en = open('docs/index.html').read()
es = open('docs/es/index.html').read()
assert en.count('reel-frame') == es.count('reel-frame'), 'frame count differs between languages'
assert 'En Cartelera' in es and 'Now Showing' in en
print('OK: both languages render the same frames with their own labels')
"
```
Expected: equal counts and `OK: both languages render the same frames with their own labels`.

- [ ] **Step 9: Final browser pass**

Open both `docs/index.html` and `docs/es/index.html` and re-run the Task 8 Step 4 checklist against each, plus:
- Route frames render a visible trace and clicking one switches the routes sketch, readout and photo strip to that activity.
- At a 375px-wide viewport the strip still scrolls horizontally and the page body does not.
- `Download Résumé (PDF)` produces a print preview with no Reel section in it.
- A keyboard-only pass reaches the track, the ruler buttons and the prev/next controls with a visible focus ring.

- [ ] **Step 10: Commit any final fixes and open the PR**

```bash
git add -A
git commit -m "Fix issues found in end-to-end reel verification" || echo "nothing to fix"
git push
gh pr create --title "Add The Reel — a 90-day chronological strip" --body "$(cat <<'EOF'
## Summary
Adds a full-bleed "The Reel" section showing the last 90 days of films, books, runs and monthly commit counts on one scrubbable film strip, in date order.

Additive rather than a replacement: the strip carries the time axis the existing sections lack, and clicking a frame scrolls to that item in its own section, so the Reel is an index rather than a second copy of the content.

## Implementation
- The Reel is built by scraping the site's own rendered output, so there is no duplicated feed-parsing and every frame provably has an on-page target.
- `update_site.py` and `update_strava.py` now emit `id` and `data-reel-*` attributes on the items they already render.
- `update_reel.py` merges those into one date-sorted list, adds monthly commit counts from the GitHub GraphQL API, and writes both language files.
- Frames are anchors, so scrolling and arrival highlighting use `scroll-behavior: smooth` and `:target` rather than JavaScript.
- Supersedes the standalone Box Office section from `.planning/specs/2026-08-12-cinema-site-features-design.md`.

## Spec and plan
- Spec: `.planning/specs/2026-08-24-the-reel-design.md`
- Plan: `.planning/plans/2026-08-24-the-reel-plan.md`

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Plan Self-Review

**Spec coverage:**

| Spec section | Task |
|---|---|
| §1 Placement, nav, gate, interaction, typographic frames | 3, 6, 7, 8 |
| §2 Rolling 90-day window, label, one-way guarantee, empty state | 4 (window), 3 (label), 8 (empty guard) |
| §3 Page-as-source-of-truth architecture, item model | 1, 2, 4 |
| §4 `update_site.py` dates and attributes | 1 |
| §4 `update_strava.py` dates and attributes | 2 |
| §4 `update_reel.py` scrape/render/inject, fail-loud markers | 4, 5, 6 |
| §4 `update-reel.yml` at 5:55 UTC | 9 |
| §5 Monthly commit buckets, GraphQL, public-only accepted, off-site link | 5, 6 |
| §6 Anchors not buttons, `:target`, route activation on `hashchange` | 6, 7, 8 |
| §6 CSS block, `--emulsion`, reduced motion | 7 |
| §6 `initReel()` responsibilities | 8 |
| §7 EN/ES copy | 3 (section chrome), 6 (frame labels) |
| Risks: id stability, slug collisions | 1 (`unique_id`), 2 (activity id) |
| Testing: output-neutrality, ordering, parity, keyboard, reduced motion, print | 1 step 9, 9 steps 6-9, 7 step 3 |

No gaps found.

**Placeholder scan:** no `TBD`/`TODO`/"handle edge cases"/"similar to Task N" present; every code step carries the literal code to write.

**Type consistency checked:**
- `reel_attrs(item_id, kind, date, title, sub, detail)` in Task 1; Task 2's copy adds a trailing `extra=""` parameter and this difference is stated in its Interfaces block.
- `render_books(books, reel=False)` — the `reel` keyword is used consistently in Task 1 steps 7 and its two call sites.
- Item dict keys `kind, date, target, title, sub, detail, path_d, viewbox` are identical across `parse_items` (Task 4), `commit_items` (Task 5) and `render_frame` (Task 6). `within_window` adds `_d`, which `render_frame` reads.
- `.in-gate` is defined in Task 7's CSS and toggled in Task 8's JS.
- `data-r-date`/`data-r-kind`/`data-r-title`/`data-r-sub`/`data-r-detail` and `data-month` are emitted in Task 6 and read as `dataset.rDate`/`rKind`/`rTitle`/`rSub`/`rDetail`/`month` in Task 8.
- Element ids `#reel`, `#reel-track`, `#reel-readout`, `#reel-ruler`, `#reel-prev`, `#reel-next` are created in Task 3 and consumed in Task 8.
