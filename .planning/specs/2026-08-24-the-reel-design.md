# The Reel — design

Date: 2026-08-24
Branch: `the-reel-design` (design only; implementation lands on its own branch)

## Context

The site (`docs/`, published to `conorshields.ie` via GitHub Pages) is themed as a
cinema programme: *Tonight's Programme* (hero), *Behind The Scenes* (toolkit),
*Engagements* (career), *Now Showing* (films), *On Location* (routes),
*Intermission* (reading list), *Now Casting* (contact). Content stays fresh
through build-time GitHub Actions that scrape RSS/APIs and write into
`docs/index.html` and `docs/es/index.html` between HTML comment markers.

Today the three data sections are independent lists with no time axis. You can
see the last 15 films and the last 6 books, but not that June was all books and
no films, or that the running picked up in July.

The Reel adds that axis: one horizontal film strip, in date order, carrying every
film watched, book finished, run logged and month of commits from the last 90
days. It sits alongside the existing sections rather than replacing them —
the strip answers *what has this stretch been like*, the sections answer
*what specifically*.

## 1. Concept and placement

**Placement:** a new full-bleed `<section class="section reel" id="reel">`
inserted after Career (`#experience`) and before Films (`#films`), in both
language files. The site currently runs professional-then-personal; the Reel
becomes the establishing shot for the personal half.

**Nav:** a new link (`#reel`, label "The Reel" / ES "La Bobina") added to
`.nav-links` and `.mobile-menu`, placed between *Engagements* and *Now Showing*
to match section order.

**The gate.** A fixed, crimson-bracketed window at the horizontal centre of the
strip. The strip scrolls through it; whichever frame is nearest centre gets
`.in-gate` (full opacity, `scale(1)`) while every other frame sits at 34%
opacity and `scale(.94)`. The frame in the gate drives a readout bar below the
strip showing date, title, source detail and frame number. This replaces
carousel state with a derived value: "in the gate" is only ever *whichever frame
is nearest centre*.

**Interaction.** Frames are anchors, not buttons (see section 6) — clicking one
scrolls the page to that item in its own section, where `:target` highlights it.
The Reel is an index; the sections are the content. Movement through the strip:
native horizontal scroll, pointer drag with snap-to-frame on release, arrow keys
when the track has focus, and a month ruler beneath that jumps to the first frame
of a month.

**Frames are typographic, not posters.** Film and book frames render as type
(condensed uppercase title, italic byline, crimson stars) on the emulsion ground,
with books getting a cream paper inset for rhythm. Posters were considered and
rejected: 27 poster thumbnails in a row reproduces a Letterboxd grid, and the
posters already do their job in *Now Showing*. Route frames render the existing
Strava SVG trace; commit frames render a bar column.

## 2. The window: rolling 90 days

The Reel renders **only items already rendered on the page**, filtered to the
last 90 days from build date, so click-to-scroll is a guarantee rather than a
best effort.

Current section limits (`watched=15`, `books=6`, `ACTIVITY_LIMIT=6`) span
roughly 90 days as measured against the live feeds on 2026-08-24:

| Set | Span |
|---|---|
| 15 films | 2026-05-10 → 2026-08-11 |
| 6 books | 2026-05-18 → 2026-08-19 |

That gives ~27 content frames plus 3–4 commit frames.

**Label:** `REEL <NN>` where `NN` is the build month (e.g. `REEL 08`), with
"Last 90 Days" / ES "Últimos 90 Días" as the window text. A calendar-year framing
was rejected: it needs deeper fetches, most frames would then have no on-page
target, and the section would sit nearly empty every January.

**Guarantee direction is one-way.** Every Reel frame has a scroll target; not
every section item has a frame. A section item older than 90 days simply does not
appear in the strip. This is intended and needs no special handling.

**Empty state:** if the window yields fewer than two content frames,
`update_reel.py` writes nothing between the markers, and `initReel()` sets the
`hidden` attribute on `#reel` when the track has fewer than two children. The
decision lives in JS rather than in the script because the section markup is
static in both language files and only the frames are injected.

## 3. Architecture: the page is the source of truth

The naive approach — have each of the three existing scripts write its own items
into a shared block — cannot work, because a merged list must be sorted as a
whole and the scripts run in separate workflows at separate times
(`goodreads`/`letterboxd` 5:00, `update-site` 5:15, `update-strava` 5:45).
Re-fetching all three feeds in a new script would instead duplicate the fetch and
parse logic and open a consistency gap: a film logged at 5:30 would appear in the
Reel but not in *Now Showing*.

**Instead, the Reel is built by reading the already-rendered HTML.** The three
existing scripts start emitting date and identity attributes on the items they
render; a new script scrapes those attributes out of `docs/index.html` and builds
the strip from them. No duplicated fetching, exact consistency with what is on
the page, and every frame provably has a target because it was read *from* its
target.

Only commit counts need a live fetch, because there is no on-page Box Office
section to read them from.

### Data flow

```
letterboxd.yml ─┐
goodreads.yml  ─┤
update-site.py ─┼─→ docs/index.html   ─→ update_reel.py ─→ SITE-REEL block
update-strava.py┘   (items now carry        (+ GitHub API)   in both files
                     id / data-reel-date)
```

### Reel item model

Each frame is derived from one scraped element:

| Field | Source |
|---|---|
| `kind` | `film` \| `book` \| `route` \| `code` |
| `date` | `data-reel-date` attribute (`YYYY-MM-DD`) |
| `target` | the item's `id` on the page |
| `title`, `sub`, `detail` | scraped from the item's existing child elements |

Sorted ascending by `date`. Ties broken by kind order (film, book, route, code)
for stable output across builds.

## 4. Changes to the existing scripts

### `update_site.py`

**Extract dates.** `get_recent_watched()` reads
`letterboxd:watchedDate` (verified present on all 50 feed items, clean
`YYYY-MM-DD`). `get_books()` reads `user_read_at`, falling back to
`user_date_added` when it is empty — verified empty on 5 of 100 books, including
4 of the most recent 12 (*Capitalist Realism*, *Heart of Darkness*). Where both
exist they match; the two diverge only for backfilled entries (*Intermezzo*:
read Oct 2024, added Jul 2025), which preferring `user_read_at` handles
correctly. Both are RFC-822 and need normalising to `YYYY-MM-DD`.

**Emit identity and date.** `render_watched()` adds
`id="film-<letterboxd-slug>"` and `data-reel-date` to each `.film-card`; the slug
comes from the existing `link`. `render_books()` adds
`id="book-<slug>"` (slugified title, lowercased, non-alphanumerics collapsed to
`-`) and `data-reel-date` to each `.book-item`.

`render_favourites()` is **not** touched — favourites are a static top-4, not
dated events, and must not enter the Reel.

### `update_strava.py`

`get_activities()` already parses `start_date_local` at line 217 for `weekday`;
it additionally keeps the ISO date and the activity id.
`render_routes_html()` emits `id="route-<activity-id>"` and `data-reel-date` on
each route list item. The activity id is used rather than the loop index because
the index shifts as new activities arrive, which would break saved links.

### New: `.github/scripts/update_reel.py`

1. Read `docs/index.html`.
2. Scrape every element carrying `data-reel-date`, capturing its `id`, kind
   (from its class — `film-card`, `book-item`, route item), and display text.
3. Fetch monthly commit counts for each month the window touches (section 5).
4. Filter to the last 90 days, sort ascending, render frames.
5. Write between `<!-- SITE-REEL:START -->` / `<!-- SITE-REEL:END -->` in
   **both** `docs/index.html` and `docs/es/index.html`, following the existing
   `re.sub` marker pattern, and raise `SystemExit` if a marker is missing —
   matching the fail-loud posture `update_site.py` already uses for
   `SITE-CURRENTLY-READING`.

Both language files receive the same frames; only the labels differ (section 7).
The scrape reads the EN file only, since both are rendered from the same data.

### New: `.github/workflows/update-reel.yml`

Cron `55 5 * * *` — after `update-strava.yml` at `45 5`, so every source section
is already written for the day. Same checkout/commit pattern as the existing
workflows, committing both site files if changed, plus `workflow_dispatch`.

## 5. Commit frames

**Bucketing: monthly.** Weekly buckets over 90 days would put 13 commit frames
into a ~40 frame strip — a third of it in bar charts. Monthly gives 3–4 frames
that read as punctuation between the content.

**Source:** the GitHub GraphQL `contributionsCollection` with `from`/`to` per
month, read for `totalCommitContributions`. This is preferred over
`GET /search/commits`, which covers public repositories only and undercounts.
Authenticated with the Actions `GITHUB_TOKEN`. If that token cannot see private
contribution counts, the number is public-only and that is accepted — no new PAT
secret is introduced for this feature, since the frame is texture rather than a
headline metric. On API failure the step exits non-zero rather than writing a
zero — same posture as the existing scripts, no silent fallback content.

**No on-page target.** Commit frames are the one kind with nowhere to scroll to,
since Box Office is folded into the Reel rather than built as its own section
(superseding that part of `2026-08-12-cinema-site-features-design.md`). They link
out to `https://github.com/cshields236`, consistent with how film cards already
link out to Letterboxd.

## 6. Front-end

### Markup

Frames are `<a href="#film-the-invite">`, not buttons. Native anchors give
keyboard access, real focus behaviour and browser-handled smooth scrolling
(`html { scroll-behavior: smooth }` is already set) with no JavaScript in the
scroll path at all. Commit frames are anchors too, pointing off-site.

Arrival highlighting is pure CSS via `:target`:

```css
#films .film-card:target,
#books .book-item:target,
#routes .route-item:target { outline: 2px solid var(--crimson); outline-offset: 4px }
```

No JS needed to focus the destination.

**Routes need one extra step.** `.route-item` is a `<button>` that switches the
active trace in the routes sketch, so a `:target` outline would highlight the
button while the sketch still showed a different route. `initReel()` therefore
listens for `hashchange` and, when the new hash matches a `.route-item` id,
dispatches a click on it so the sketch, readout and photo strip all follow. Films
and books need no equivalent — arriving at the item *is* the whole destination.

### `style.css`

New `/* ─── The Reel ─── */` block using existing tokens only — `--emulsion`
(new, `#081310`) is the single addition, for the strip ground. Sprocket rails are
a `repeating-linear-gradient`; the gate is an absolutely-positioned overlay with
crimson corner brackets and a large `box-shadow` spread to dim the strip either
side. The track is `display:flex; overflow-x:auto` with scrollbars hidden and
`padding: 0 calc(50vw - 100px)` so the first and last frames can reach the gate.
Full-bleed escape from the 1000px container via
`width:100vw; margin-left:calc(50% - 50vw)`.

`@media (prefers-reduced-motion: reduce)` drops the frame transitions and
`scroll-behavior`.

### `main.js` — `initReel()`

Follows the existing `initX()` convention. Responsibilities, all of them
derived-state only:

- **Gate tracking:** on `scroll` (rAF-throttled), find the frame whose centre is
  nearest the track centre, toggle `.in-gate`, update the readout and the active
  month on the ruler. Early-returns when the nearest frame has not changed.
- **Drag to scrub:** pointer events with `setPointerCapture`, snapping to the
  gated frame on release. A movement threshold (~6px) distinguishes a drag from
  a click so dragging never triggers navigation.
- **Keyboard:** `ArrowLeft`/`ArrowRight` on the focused track move one frame.
- **Month ruler:** click scrolls to the first frame of that month.
- **Route arrival:** on `hashchange`, activate the matching `.route-item` so the
  routes sketch follows the link (see above).
- **Empty guard:** set `hidden` on `#reel` when the track holds fewer than two
  frames.

No modal. The programme-note modal from the mockup is deliberately dropped —
click-to-scroll replaced it — so this feature touches none of the shared
`lockScroll`/`unlockScroll` modal plumbing that the ticket and casting modals use.

## 7. Copy

| Key | EN | ES |
|---|---|---|
| Section label | `REEL <NN> — LAST 90 DAYS` | `BOBINA <NN> — ÚLTIMOS 90 DÍAS` |
| Section title | The Reel | La Bobina |
| Intro | Everything watched, read, run and shipped, in order, on one strip. Drag it through the gate. | Todo lo visto, leído, corrido y publicado, en orden, en una sola tira. Arrástrala por la ventanilla. |
| Frame kinds | Now Showing / Intermission / On Location / Box Office | reuse each section's existing ES label |
| Readout | `FRAME NN / TT` | `FOTOGRAMA NN / TT` |

Frame-kind labels reuse the existing section names so the strip cross-references
the page instead of introducing new vocabulary. ES copy is a first pass for the
user to correct during implementation.

## Out of scope

- Replacing the Films, Reading List or Routes sections. The Reel is additive;
  those sections keep the posters, ratings, outbound links, route photos and
  distance readout that a 200px frame cannot hold.
- The standalone Box Office section from
  `2026-08-12-cinema-site-features-design.md` — superseded by commit frames.
- Poster or cover images inside frames (section 1).
- The programme-note modal (section 6).
- Any client-side data fetching. Build-time only, matching the existing pattern.
- Calendar-year or all-time windows (section 2).

## Risks

- **Scraping own output.** `update_reel.py` depends on markup shape from three
  other scripts. Mitigated by keying only off `data-reel-date` and `id` — both
  explicit contracts added for this purpose — rather than off structural
  position, and by failing loudly when the scrape yields nothing.
- **Workflow ordering.** The Reel is one build cycle behind if an earlier
  workflow fails, showing yesterday's strip against today's sections. Acceptable:
  the strip is a 90-day view, so a one-day lag is invisible.
- **ID stability.** Slug collisions are possible if two books share a title.
  Implementer should suffix a counter on collision rather than emit duplicate ids.
- **GITHUB_TOKEN scope** for private commit counts (section 5).

## Testing

- `workflow_dispatch` run of `update-site.yml` and `update-strava.yml` to confirm
  the new `id`/`data-reel-date` attributes appear and **no other diff** appears in
  the rendered sections — the refactor must be output-neutral apart from the new
  attributes. Verify by diffing generated HTML before and after.
- `workflow_dispatch` run of `update-reel.yml`; confirm the block is written to
  both language files, frames are in ascending date order, and the count matches
  the 90-day window.
- Browser: gate tracking follows scroll, drag snaps, arrow keys step one frame,
  month ruler jumps; clicking a frame of each kind lands on the right item with
  the `:target` outline visible; commit frames open GitHub.
- Verify the films carousel, film flip, route markers, ticket modal and casting
  modal all still work — the Reel adds no shared state, so this is a regression
  check on the new ids and CSS not colliding.
- Keyboard-only pass through the whole strip, and a `prefers-reduced-motion` pass.
- Both `docs/index.html` and `docs/es/index.html`, desktop and mobile widths.
