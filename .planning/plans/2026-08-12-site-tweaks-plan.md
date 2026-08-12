# Site Tweaks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Box Office section, surface Letterboxd review text via a film-card flip, add a "Read"/"Leídos" subheading, change the contact email everywhere, and add a personal welcome line to the hero.

**Architecture:** Same static bilingual site (`docs/index.html` EN, `docs/es/index.html` ES) kept fresh by build-time Python scripts. This plan removes one whole feature (Box Office: its markup, CSS, script, and workflow), makes several small copy/markup edits, and extends `update_site.py`'s Letterboxd sync plus `docs/style.css`/`docs/main.js` to support a click-to-flip film card that reveals review text on its back face.

**Tech Stack:** Static HTML/CSS/vanilla JS, Python 3.12 (stdlib only), GitHub Actions.

## Global Constraints

- Every content change to `docs/index.html` must have a matching change in `docs/es/index.html`.
- Reuse existing CSS custom properties (`--display`, `--serif`, `--mono`, `--crimson`, `--paper`, `--ink`, `--text-dim`, `--line`, `--line-strong`, `--ease-smooth`) — no new hard-coded colors or fonts.
- New injected/dynamic content uses the existing `<!-- MARKER:START -->…<!-- MARKER:END -->` comment-pair convention where applicable.
- The "All-Time Favourites" grid (`render_favourites`) is untouched — no review data is available for it (it's scraped from the profile page, not the watch-log RSS).
- Non-reviewed film cards in "Recently Screened" keep their exact current markup (`<a class="film-card">` linking straight to Letterboxd) — only cards with a review change shape.

---

### Task 1: Remove the Box Office feature

**Files:**
- Modify: `docs/index.html` (remove nav links + section)
- Modify: `docs/es/index.html` (remove nav links + section)
- Modify: `docs/style.css` (remove CSS rules + print hide-list entry)
- Delete: `.github/scripts/update_github_stats.py`
- Delete: `.github/workflows/update-github-stats.yml`

**Interfaces:** None — this is a pure removal, nothing else in the codebase reads `SITE-BOX-OFFICE` or `.box-office-*` classes after this task.

- [ ] **Step 1: Remove the English nav links**

In `docs/index.html`, the line `<a href="#box-office">Box Office</a>` appears twice (once in `.nav-links`, once in `.mobile-menu`), identically. Using a find-and-replace with "replace all occurrences" enabled, replace:
```html
<a href="#box-office">Box Office</a>
```
with nothing (delete both occurrences, including their trailing newline).

- [ ] **Step 2: Remove the English section**

In `docs/index.html`, find:
```html
</section>
<section class="section box-office" id="box-office">
<div class="container">
<div class="section-header reveal">
<span class="section-label">Opening Weekend</span>
<h2 class="section-title">Box Office</h2>
</div>
<div class="box-office-stat reveal">
<span class="box-office-number"><!-- SITE-BOX-OFFICE:START -->0<!-- SITE-BOX-OFFICE:END --></span>
<span class="box-office-caption">Tickets Sold — Commits, All-Time</span>
</div>
</div>
</section>
<section class="section experience" id="experience">
```
Replace with:
```html
</section>
<section class="section experience" id="experience">
```

- [ ] **Step 3: Remove the Spanish nav links**

In `docs/es/index.html`, the line `<a href="#box-office">Taquilla</a>` appears twice, identically. Using "replace all occurrences", replace:
```html
<a href="#box-office">Taquilla</a>
```
with nothing.

- [ ] **Step 4: Remove the Spanish section**

In `docs/es/index.html`, find:
```html
</section>
<section class="section box-office" id="box-office">
<div class="container">
<div class="section-header reveal">
<span class="section-label">Fin de Semana de Estreno</span>
<h2 class="section-title">Taquilla</h2>
</div>
<div class="box-office-stat reveal">
<span class="box-office-number"><!-- SITE-BOX-OFFICE:START -->0<!-- SITE-BOX-OFFICE:END --></span>
<span class="box-office-caption">Entradas Vendidas — Commits, Histórico</span>
</div>
</div>
</section>
<section class="section experience" id="experience">
```
Replace with:
```html
</section>
<section class="section experience" id="experience">
```

- [ ] **Step 5: Remove the CSS rules**

In `docs/style.css`, find:
```css
/* ─── Box Office ─── */
.box-office-stat {
    text-align: center;
}

.box-office-number {
    display: block;
    font-family: var(--display);
    font-weight: 800;
    font-size: clamp(3.5rem, 12vw, 6rem);
    line-height: 1;
    color: var(--crimson);
}

.box-office-caption {
    display: block;
    margin-top: 1rem;
    font-family: var(--mono);
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
}

/* ─── Timeline (Engagements) ─── */
```
Replace with:
```css
/* ─── Timeline (Engagements) ─── */
```

- [ ] **Step 6: Remove the print hide-list entry**

In `docs/style.css`, find:
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books, .section.box-office,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop, .casting-backdrop {
        display: none !important;
    }
```
Replace with:
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop, .casting-backdrop {
        display: none !important;
    }
```

- [ ] **Step 7: Delete the script and workflow files**

```bash
git rm .github/scripts/update_github_stats.py .github/workflows/update-github-stats.yml
```

- [ ] **Step 8: Verify removal**

Run: `grep -rn "box-office\|Box Office\|Taquilla\b" docs/index.html docs/es/index.html docs/style.css`
Expected: no output (no matches).

Run: `ls .github/scripts/update_github_stats.py .github/workflows/update-github-stats.yml 2>&1`
Expected: `No such file or directory` for both.

- [ ] **Step 9: Commit**

The file deletions from Step 7 are already staged (`git rm` stages automatically) — this commit combines them with the HTML/CSS edits:

```bash
git add docs/index.html docs/es/index.html docs/style.css
git commit -m "$(cat <<'EOF'
Remove Box Office section

A public GitHub commit count isn't representative when most work
happens in private repos.
EOF
)"
```

---

### Task 2: "Read" subheading and hero welcome blurb

**Files:**
- Modify: `docs/index.html`
- Modify: `docs/es/index.html`

**Interfaces:** None — static copy/markup only, reuses the existing `.books-subtitle` and `.hero-subtitle` classes (no new CSS).

- [ ] **Step 1: Add the English "Read" subheading**

In `docs/index.html`, find:
```html
            </div><!-- SITE-CURRENTLY-READING:END -->
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```
Replace with:
```html
            </div><!-- SITE-CURRENTLY-READING:END -->
<h3 class="books-subtitle">Read</h3>
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```

- [ ] **Step 2: Add the Spanish "Leídos" subheading**

In `docs/es/index.html`, find:
```html
            </div><!-- SITE-CURRENTLY-READING:END -->
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```
Replace with:
```html
            </div><!-- SITE-CURRENTLY-READING:END -->
<h3 class="books-subtitle">Leídos</h3>
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```

- [ ] **Step 3: Add the English hero blurb**

In `docs/index.html`, find:
```html
<p class="hero-subtitle reveal">"Building event-driven systems and scalable cloud infrastructure."</p>
<div class="hero-location reveal">Cavan, Ireland → London, UK</div>
```
Replace with:
```html
<p class="hero-subtitle reveal">"Building event-driven systems and scalable cloud infrastructure."</p>
<p class="hero-subtitle reveal">Hey welcome to my site, I'm interested in films, books, very slow running so I thought I'd document that here!</p>
<div class="hero-location reveal">Cavan, Ireland → London, UK</div>
```

- [ ] **Step 4: Add the Spanish hero blurb**

In `docs/es/index.html`, find:
```html
<p class="hero-subtitle reveal">"Construyendo sistemas basados en eventos e infraestructura en la nube escalable."</p>
<div class="hero-location reveal">Cavan, Irlanda → Londres, Reino Unido</div>
```
Replace with:
```html
<p class="hero-subtitle reveal">"Construyendo sistemas basados en eventos e infraestructura en la nube escalable."</p>
<p class="hero-subtitle reveal">¡Hola, bienvenido a mi sitio! Me interesan las películas, los libros, correr muy lento, y estoy intentando aprender español, así que pensé en documentarlo aquí.</p>
<div class="hero-location reveal">Cavan, Irlanda → Londres, Reino Unido</div>
```

- [ ] **Step 5: Verify**

Run: `grep -c 'class="books-subtitle">Read<\|class="books-subtitle">Leídos<' docs/index.html docs/es/index.html`
Expected: `docs/index.html:1` (only "Read" matches there) and `docs/es/index.html:1` (only "Leídos" matches there) — run the grep separately per file if the combined pattern is confusing, e.g. `grep -c 'Read</h3>' docs/index.html` → `1`, `grep -c 'Leídos</h3>' docs/es/index.html` → `1`.

Run: `grep -c "very slow running" docs/index.html` → expect `1`.
Run: `grep -c "aprender español" docs/es/index.html` → expect `1`.

- [ ] **Step 6: Commit**

```bash
git add docs/index.html docs/es/index.html
git commit -m "feat: add Read subheading and personal welcome blurb to hero"
```

---

### Task 3: Change contact email

**Files:**
- Modify: `docs/index.html`
- Modify: `docs/es/index.html`
- Modify: `docs/main.js`

**Interfaces:** None — string replacement only, no signature changes.

- [ ] **Step 1: Replace the email in the English page**

In `docs/index.html`, using "replace all occurrences", replace every instance of:
```
con.shields1@gmail.com
```
with:
```
me@conorshields.ie
```
(This covers both the `href="mailto:con.shields1@gmail.com"` and the visible link text `con.shields1@gmail.com`, since both contain this exact substring.)

- [ ] **Step 2: Replace the email in the Spanish page**

In `docs/es/index.html`, using "replace all occurrences", replace every instance of:
```
con.shields1@gmail.com
```
with:
```
me@conorshields.ie
```

- [ ] **Step 3: Replace the email in main.js**

In `docs/main.js`, find:
```js
        continueLink.href = `mailto:con.shields1@gmail.com?subject=${subject}&body=${body}`;
```
Replace with:
```js
        continueLink.href = `mailto:me@conorshields.ie?subject=${subject}&body=${body}`;
```

- [ ] **Step 4: Verify no old email remains**

Run: `grep -rn "con.shields1@gmail.com" docs/`
Expected: no output.

Run: `grep -c "me@conorshields.ie" docs/index.html docs/es/index.html docs/main.js`
Expected: `docs/index.html:2`, `docs/es/index.html:2`, `docs/main.js:1`.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html docs/es/index.html docs/main.js
git commit -m "feat: change contact email to me@conorshields.ie"
```

---

### Task 4: Extract Letterboxd review text in `update_site.py`

**Files:**
- Modify: `.github/scripts/update_site.py`

**Interfaces:**
- Produces: `get_recent_watched()`'s returned dicts gain a `"review"` key (string, `""` if no review was written for that entry).
- Produces: `render_watched(films, view_on_letterboxd_text)` — signature changes from `render_watched(films)` to take a second parameter, and emits one of two markup shapes per film depending on whether `f["review"]` is non-empty (exact shapes below — Task 5's CSS/JS target these class names verbatim).
- Produces: `REVIEW_ICON` module-level constant (a string of inline SVG markup).
- Consumes: `STRINGS[lang]` gains a `"view_on_letterboxd"` key, alongside the existing `"currently_reading"` key.

- [ ] **Step 1: Add the `view_on_letterboxd` string**

In `.github/scripts/update_site.py`, find:
```python
STRINGS = {
    "en": {"currently_reading": "Currently Reading"},
    "es": {"currently_reading": "Actualmente Leyendo"},
}
```
Replace with:
```python
STRINGS = {
    "en": {"currently_reading": "Currently Reading", "view_on_letterboxd": "View on Letterboxd →"},
    "es": {"currently_reading": "Actualmente Leyendo", "view_on_letterboxd": "Ver en Letterboxd →"},
}
```

- [ ] **Step 2: Extract review text in `get_recent_watched()`**

In `.github/scripts/update_site.py`, find:
```python
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
        films.append({
            "title": title_el.text,
            "year": year,
            "rating": rating,
            "stars_html": STAR_MAP.get(rating, ""),
            "link": link,
            "poster": poster,
        })
        if len(films) == limit:
            break
    return films
```
Replace with:
```python
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
                review = paragraphs[1].strip()

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
```

- [ ] **Step 3: Add the review-icon constant and rewrite `render_watched()`**

In `.github/scripts/update_site.py`, find:
```python
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
```
Replace with:
```python
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
```

- [ ] **Step 4: Pass the localized link text at the call site**

In `.github/scripts/update_site.py`, find:
```python
        if watched:
            watched_html = render_watched(watched)
```
Replace with:
```python
        if watched:
            watched_html = render_watched(watched, STRINGS[lang]["view_on_letterboxd"])
```

- [ ] **Step 5: Sanity-check the review-detection logic against a fixture**

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, '.github/scripts')
from update_site import render_watched

reviewed = {'title': 'Test Film', 'link': 'https://letterboxd.com/x/', 'poster': 'p.jpg', 'stars_html': '★★★★', 'review': 'A great watch.'}
plain = {'title': 'Plain Film', 'link': 'https://letterboxd.com/y/', 'poster': 'q.jpg', 'stars_html': '★★★', 'review': ''}

html = render_watched([reviewed, plain], 'View on Letterboxd →')
assert 'film-card-flippable' in html, 'flippable card missing'
assert 'A great watch.' in html, 'review text missing'
assert 'View on Letterboxd →' in html, 'link text missing'
assert html.count('film-card-flippable') == 1, 'plain card should not be flippable'
assert '<a href=\"https://letterboxd.com/y/\" class=\"film-card\"' in html, 'plain card markup changed'
print('OK')
"
```
Expected: `OK` with no assertion error.

- [ ] **Step 6: Run the script for real and inspect the diff**

This requires network access (hits the live Letterboxd RSS feed).

Run: `python3 .github/scripts/update_site.py`
Expected output: a line like `Updated 2 site file(s): N favourites, N watched, N books, N currently reading.`

Then run: `git diff docs/index.html | grep -A3 "film-card-flippable"`
Expected: if any of your recent watch-log entries have a real review, you'll see `<div class="film-card film-card-flippable">` blocks with the review text inline; entries without a review keep the plain `<a class="film-card">` shape.

- [ ] **Step 7: Commit**

```bash
git add .github/scripts/update_site.py docs/index.html docs/es/index.html
git commit -m "feat: extract Letterboxd review text for reviewed films"
```

---

### Task 5: Film card flip — CSS and JS

**Files:**
- Modify: `docs/style.css`
- Modify: `docs/main.js`

**Interfaces:**
- Consumes: the exact markup shape from Task 4's `render_watched()` — classes `film-card-flippable`, `film-flip`, `film-flip-front`, `film-flip-back`, `film-review-toggle`, `review-icon`, `film-review`, `film-review-link`.
- Produces: `initFilmFlip()`, called from the `DOMContentLoaded` handler alongside the other `init*()` calls.

- [ ] **Step 1: Add the flip CSS**

In `docs/style.css`, find the end of the `.film-rating` rule (immediately before the `/* ─── On Location (Routes) ─── */` comment):
```css
.film-rating {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--crimson);
    letter-spacing: 0.02em;
    padding: 0 0.1rem;
}

/* ─── On Location (Routes) ─── */
```
Replace with:
```css
.film-rating {
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--crimson);
    letter-spacing: 0.02em;
    padding: 0 0.1rem;
}

/* ─── Film Review Flip ─── */
.film-card-flippable {
    perspective: 1000px;
}

.film-flip {
    position: relative;
    width: 100%;
    aspect-ratio: 2 / 3;
    transform-style: preserve-3d;
    transition: transform 0.6s var(--ease-smooth);
}

.film-card-flippable.flipped .film-flip {
    transform: rotateY(180deg);
}

.film-flip-front,
.film-flip-back {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    border-radius: var(--radius);
    overflow: hidden;
}

.film-flip-front .film-poster {
    height: 100%;
}

.film-flip-back {
    transform: rotateY(180deg);
    background: var(--paper);
    color: var(--ink);
    padding: 0.85rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.film-review {
    font-family: var(--serif);
    font-style: italic;
    font-size: 0.7rem;
    line-height: 1.45;
    overflow-y: auto;
}

.film-review-link {
    display: inline-block;
    margin-top: 0.5rem;
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 0.03em;
    color: var(--crimson);
    text-decoration: none;
}

.film-review-toggle {
    position: absolute;
    bottom: 0.5rem;
    right: 0.5rem;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(6, 12, 10, 0.72);
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    z-index: 2;
    padding: 0;
}

.review-icon {
    width: 12px;
    height: 12px;
    stroke: var(--paper);
}

@media (prefers-reduced-motion: reduce) {
    .film-flip {
        transition: none;
    }
}

/* ─── On Location (Routes) ─── */
```

- [ ] **Step 2: Add `initFilmFlip()` and wire it up**

In `docs/main.js`, find:
```js
    initQuiz();
    initTicket();
    initCasting();
    initCreditsRoll();
    initFilmsCarousel();
    initRoutes();
```
Replace with:
```js
    initQuiz();
    initTicket();
    initCasting();
    initCreditsRoll();
    initFilmsCarousel();
    initFilmFlip();
    initRoutes();
```

In `docs/main.js`, find the end of `initFilmsCarousel()`:
```js
    let ticking = false;
    track.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => { updateButtons(); ticking = false; });
    }, { passive: true });
    window.addEventListener('resize', updateButtons);
    updateButtons();
}

/* ─── On Location (Strava Routes) ───
```
Replace with:
```js
    let ticking = false;
    track.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => { updateButtons(); ticking = false; });
    }, { passive: true });
    window.addEventListener('resize', updateButtons);
    updateButtons();
}

/* ─── Film Review Flip ───
   Reviewed films in "Recently Screened" flip in place to reveal the
   review text left on Letterboxd, via the small toggle badge in the
   poster's corner. Plain (non-reviewed) cards are untouched. */
function initFilmFlip() {
    document.querySelectorAll('#watched-track .film-review-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const card = btn.closest('.film-card-flippable');
            if (card) card.classList.toggle('flipped');
        });
    });
}

/* ─── On Location (Strava Routes) ───
```

- [ ] **Step 3: Verify structure**

Run: `grep -n "initFilmFlip" docs/main.js`
Expected: shows the function definition and its single call site in the `DOMContentLoaded` handler.

- [ ] **Step 4: Manually test the flip in a browser**

```bash
cd docs && python3 -m http.server 8000
```
Open `http://localhost:8000/#films` and check "Recently Screened". For any card with a review (has the small badge icon in the poster's bottom-right corner):
1. Click the badge — the card should flip to reveal the review text on a paper-colored back face, with a "View on Letterboxd →" link.
2. Click the badge again — it flips back to the poster.
3. Click a plain card (no badge) — it should navigate to Letterboxd as before (unchanged behavior).
4. Confirm the "All-Time Favourites" grid above is completely unaffected.

Stop the server (Ctrl+C) when done.

- [ ] **Step 5: Commit**

```bash
git add docs/style.css docs/main.js
git commit -m "feat: add click-to-flip review reveal for reviewed film cards"
```

---

## After all tasks

Push the branch and open a PR:

```bash
git push -u origin site-tweaks
gh pr create --base main --title "Remove Box Office, add Letterboxd review flip, email + hero updates" --body "$(cat <<'EOF'
## Summary
- Removes the Box Office (GitHub commit count) section entirely
- Adds a click-to-flip interaction on reviewed "Recently Screened" films, revealing the actual Letterboxd review text
- Adds a "Read"/"Leídos" subheading above the main book list
- Changes the contact email to me@conorshields.ie everywhere it appears
- Adds a personal welcome line to the hero, in both languages

## Test plan
- [ ] Confirm Box Office is fully gone (nav, section, CSS) in both languages
- [ ] Confirm the "Read"/"Leídos" heading renders above the main book list
- [ ] Confirm the hero blurb renders in both languages
- [ ] Confirm mailto links/casting modal use the new email
- [ ] Confirm a reviewed film card flips to show review text and back again, and plain cards still link out normally

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
