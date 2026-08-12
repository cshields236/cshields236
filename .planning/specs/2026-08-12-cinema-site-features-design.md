# Cinema-themed site features — design

Date: 2026-08-12
Branch: fix/routes-photos (design work; implementation should land on its own branch)

## Context

The site (`docs/`, published to `conorshields.ie` via GitHub Pages) is themed as a movie premiere/programme: "Tonight's Programme" (hero), "Now Showing" (films), "On Location" (Strava routes), "Reading" (books), plus playful extras (pop quiz, ticket-stub modal, closing credits, poster flicker). Content sections are kept fresh by build-time GitHub Actions workflows that scrape RSS/APIs and write directly into `docs/index.html` and `docs/es/index.html` between HTML comment markers (e.g. `SITE-BOOKS:START/END`).

This design adds two new themed features, extends an existing data section, and aligns the refresh schedule across all build-time workflows.

## 1. Box Office (GitHub commits as ticket sales)

**Purpose:** A new section framing GitHub commit activity as box-office numbers, consistent with the site's cinema conceit.

**Placement:** New `<section class="section box-office" id="box-office">` inserted after the Toolkit section and before Experience, following the existing section-header pattern (`section-label` + `section-title`).

**Content:** A single large stat — total commit count across `cshields236`'s repos, all-time — styled as "TICKETS SOLD", using the `Big Shoulders Display` font already used for large numerals elsewhere on the site.

**Data flow:**
- New script `.github/scripts/update_github_stats.py` calls the GitHub API (`GET /search/commits?q=author:cshields236` or the GraphQL contributions API — implementer's choice, pick whichever gives an accurate all-time count without hitting rate limits) to compute the commit total.
- Writes the number into `docs/index.html` and `docs/es/index.html` between new markers, e.g. `<!-- SITE-BOX-OFFICE:START -->…<!-- SITE-BOX-OFFICE:END -->`, mirroring how `update_site.py` injects books/films.
- New workflow `.github/workflows/update-github-stats.yml`, scheduled per section 4 below, committing `docs/index.html` and `docs/es/index.html` if changed (same commit pattern as the other workflows).

**Error handling:** If the GitHub API call fails or rate-limits, the workflow step should fail loudly (non-zero exit) rather than writing a blank/zero value — same failure posture as the existing scripts (no silent fallback content).

## 2. Now Casting (contact section)

**Purpose:** Reskin the existing contact section as a casting call, and give the contact *form* the same themed confirmation treatment the raw email link already gets via the ticket-stub modal.

**Naming fix:** The contact section's `section-label` currently reads "Box Office" (English) / "Taquilla" (Spanish) — this collides with the new section above. Rename to "Now Casting" (EN) / a suitable Spanish equivalent (e.g. "Se Buscan Actores" or similar — implementer/user to pick final ES copy), in both `docs/index.html` and `docs/es/index.html`.

**Copy pass (light theming):** Keep the existing three fields (name, email, message) unchanged structurally. Reword surrounding copy to fit the casting-call conceit, e.g.:
- Intro paragraph: something like "Casting for new collaborations and conversations. Submit your details below."
- Submit button: "Send Message" → "Submit for Consideration"
Exact copy to be finalized during implementation, in both languages.

**New audition confirmation modal:** Structurally parallel to the existing `ticket-backdrop`/`ticket` modal (reuses `lockScroll`/`unlockScroll` and the same show/hide/Escape/backdrop-click plumbing in `main.js`), but with its own markup and copy — e.g. a "Casting Notice" / callback-slip look rather than a ticket-stub look, with its own ids (`casting-backdrop`, `casting-close`, `casting-continue`, etc.) to avoid clashing with the ticket modal.

**Data flow:** On `contact-form` submit, instead of immediately building the `mailto:` link and navigating (current behavior in `main.js`), the handler shows the new casting confirmation modal first; the modal's "continue" action performs the existing `mailto:` handoff (same subject/body construction as today) and closes the modal — mirroring exactly how the ticket modal intercepts the raw email link today.

## 3. Currently Reading (Goodreads)

**Purpose:** Surface what's currently being read, not just what's been finished, in both places Goodreads data already appears.

**Website (Reading List section):**
- `update_site.py` gains a second RSS fetch against the Goodreads shelf endpoint with `shelf=currently-reading` (same feed host as the existing `shelf=read` fetch, just a different shelf parameter and no rating expected).
- Renders a small "Currently Reading" block above the existing book list, between new markers `SITE-CURRENTLY-READING:START/END`, in both `docs/index.html` and `docs/es/index.html`.
- If the currently-reading shelf is empty, the block should render nothing (omit the sub-heading rather than show an empty state) — the existing `update_site.py` book-rendering code should be checked for how it already handles empty results, and this should follow the same convention.

**README:**
- `.github/workflows/goodreads.yml` gains a second step using the same `zwacky/goodreads-profile-workflow` action, with `shelf: "currently-reading"` and its own template/marker pair, writing a new "Currently Reading" block into `README.md` alongside the existing "Last 10 Books I've Read" list.

## 4. Schedule alignment

All build-time workflows move to a 5am UTC base (≈6am BST during summer daylight saving; drifts to 5am local time during GMT winter months — accepted trade-off, since GitHub Actions cron is fixed UTC and can't track DST), preserving the existing stagger so workflows that write to the same files don't race on committing:

| Workflow | Old cron | New cron |
|---|---|---|
| `goodreads.yml` | `0 8 * * *` | `0 5 * * *` |
| `letterboxd.yml` | `0 8 * * *` | `0 5 * * *` |
| `update-site.yml` | `15 8 * * *` | `15 5 * * *` |
| `update-strava.yml` | `45 8 * * *` | `45 5 * * *` |
| `update-github-stats.yml` (new) | — | `55 5 * * *` |

## Out of scope

- Deeper casting-form restructuring (role dropdowns, headshot upload, etc.) — explicitly deferred per light-theming choice.
- Live/client-side GitHub stats fetching — build-time only, matching the existing pattern.
- Resolving the pre-existing `goodreads.yml`/`letterboxd.yml` same-cron-slot README-commit overlap — not introduced by this change, left as-is.

## Testing

- Manual `workflow_dispatch` run of each modified/new workflow to confirm it fetches data and commits the expected diff to `docs/index.html`, `docs/es/index.html`, and/or `README.md`.
- Manual browser check of: Box Office section renders and matches site styling; Now Casting form submit shows the new modal and still successfully hands off to the mailto link; Reading List shows Currently Reading block above the read list (and hides gracefully if the shelf is empty).
- Verify the ticket-stub modal (email link) still works unaffected after the casting modal is added, since both share modal plumbing in `main.js`.
