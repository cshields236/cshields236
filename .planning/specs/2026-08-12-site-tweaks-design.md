# Site tweaks: remove Box Office, Letterboxd review flip, email change, hero blurb — design

Date: 2026-08-12
Branch: implementation should land on its own branch off `main`

## Context

`main` currently includes the "cinema-themed site features" work (Box Office section, Now Casting contact reskin, Goodreads currently-reading, cron alignment — see `.planning/specs/2026-08-12-cinema-site-features-design.md`). This follow-up makes four further changes to the live site (`docs/`, published to `conorshields.ie` via GitHub Pages):

1. Remove the Box Office section entirely.
2. Show the review text left on Letterboxd-logged films, revealed by flipping the film card.
3. Change the contact email everywhere it appears.
4. Add a short personal welcome blurb to the hero.

## 1. Remove Box Office

Fully reverts the feature added in the prior spec, since a GitHub public commit count isn't representative when most work happens in private repos:

- Delete the `<section class="section box-office" id="box-office">` block from both `docs/index.html` and `docs/es/index.html`.
- Remove the `#box-office` nav links from `.nav-links` and `.mobile-menu` in both files.
- Delete `.box-office-stat`/`.box-office-number`/`.box-office-caption` CSS rules from `docs/style.css`, and drop `.section.box-office` from the `@media print` hide-list.
- Delete `.github/scripts/update_github_stats.py` and `.github/workflows/update-github-stats.yml`.
- No marker/data dependency elsewhere — nothing else reads `SITE-BOX-OFFICE`.

## 2. Letterboxd review card-flip

**Purpose:** Surface the actual review text left on Letterboxd, not just the star rating, for films in the "Recently Screened" carousel — revealed by flipping the card rather than disrupting the carousel's fixed-width row layout.

**Data source — `.github/scripts/update_site.py`:**
- The Letterboxd RSS feed's `<description>` contains a poster `<img>` followed by a text paragraph. For a plain watch-log entry (no review written), that paragraph is always the auto-generated "Watched on `<date>`." — confirmed against the live feed. For an entry with a real review, the `<guid>` element's text starts with `letterboxd-review-` (a plain log's guid starts with `letterboxd-watch-`); the paragraph after the poster image is the actual review text in that case.
- `get_recent_watched()` gains: read the `<guid>` text; if it starts with `letterboxd-review-`, extract the second `<p>...</p>` from `description` (HTML-decode it, keep `<br />` line breaks, strip other tags) as `review`; otherwise `review` is `""`.
- `render_watched()` adds a `data-review` attribute (HTML-escaped) to the `.film-card` `<a>` only when `review` is non-empty, and adds a `film-card-flippable` class plus a small badge (an inline SVG "quote" icon, styled like the existing `camera-icon` used on route items with photos) inside `.film-poster` for those cards.

**Markup/CSS — flip mechanic:**
- Each flippable `.film-card` gets a front/back structure: front = existing poster/title/rating (unchanged), back = a new `.film-card-back` panel with the review text, styled on the `--paper`/`--ink` palette (matching the ticket/casting modal's paper look) so it reads as a distinct "note".
- CSS: `.film-card-flippable` uses a 3D flip (`perspective` on the container, `transform-style: preserve-3d` and `rotateY(180deg)` toggled via a `.flipped` class on click), sized to the existing fixed `150px` carousel card width — the card's height is driven by its own content (poster aspect-ratio today), so the back panel matches that same footprint via `position: absolute; inset: 0`.
- Non-flippable cards (no review, and all of "All-Time Favourites") are completely unaffected — no badge, no cursor change, no click handler.

**JS — `docs/main.js`:**
- New `initFilmFlip()` scoped to `#watched-track .film-card-flippable`: click toggles `.flipped` on that card only. Cards are independent — flipping one does not affect any other card's state, and a flipped card flips back only when clicked again. No modal, no scroll lock — this is a lightweight per-card interaction.
- Only the "Recently Screened" track is touched; "All-Time Favourites" markup/JS is untouched.

## 3. Email change

Replace `con.shields1@gmail.com` with `me@conorshields.ie` in:
- `docs/index.html` and `docs/es/index.html`: the `mailto:` href and the visible link text in the contact-info list.
- `docs/main.js`: the `mailto:` string built in `initCasting()`.

(`README.md` has no email reference — confirmed, no change needed there.)

## 4. Hero blurb

Add a new paragraph directly under the existing italic hero quote, reusing the existing `hero-subtitle reveal` class (no new CSS needed), in both languages:

- EN: "Hey welcome to my site, I'm interested in films, books, very slow running so I thought I'd document that here!"
- ES: "¡Hola, bienvenido a mi sitio! Me interesan las películas, los libros y correr muy lento, así que pensé en documentarlo aquí."

## Out of scope

- No changes to the "All-Time Favourites" grid (no review data available there — it's scraped from the profile page, not the watch-log RSS).
- No changes to how ratings are displayed — this adds review text alongside the existing star rating, doesn't replace it.
- No persistence/caching of review text beyond the existing build-time sync mechanism (same markers/re-run cadence as today).

## Testing

- Run `update_site.py` for real and confirm at least one card in "Recently Screened" gets a non-empty `review` and the flip badge, while plain watch-log entries do not.
- Manually flip a reviewed card in a browser and confirm the review text renders legibly and the card flips back on a second click; confirm a non-reviewed card does nothing on click.
- Confirm the Box Office section, its nav links, and its CSS are fully gone from both language files with no leftover dead CSS or broken print-hide list syntax.
- Confirm the new email appears everywhere the old one did, including the `mailto:` links actually opening the right address (both the raw link's ticket modal and the casting-form modal use the same `con.shields1@gmail.com` string in `main.js` — both call sites must be updated).
- Confirm the new hero blurb renders correctly in both `docs/index.html` and `docs/es/index.html`.
