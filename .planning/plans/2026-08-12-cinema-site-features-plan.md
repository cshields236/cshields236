# Cinema-Themed Site Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Box Office" GitHub-commits section, reskin the contact section as "Now Casting" with its own audition-confirmation modal, surface Goodreads "currently reading" data on-site and in the README, and align all build-time workflow schedules to 5am UTC.

**Architecture:** The site (`docs/`) is a static two-file bilingual site (`docs/index.html` EN, `docs/es/index.html` ES) kept fresh by Python scripts run on a GitHub Actions schedule. Each script fetches an external feed/API and rewrites content between `<!-- MARKER:START -->...<!-- MARKER:END -->` HTML comment pairs in both language files, then a workflow step commits the diff. Interactive behavior lives in one shared `docs/main.js`; all styling lives in one shared `docs/style.css` using CSS custom properties for the palette/fonts. This plan follows that exact pattern for every new piece.

**Tech Stack:** Static HTML/CSS/vanilla JS, Python 3.12 (stdlib only — `urllib`, `re`, `xml.etree`), GitHub Actions (`schedule` + `workflow_dispatch` triggers).

## Global Constraints

- Every content change to `docs/index.html` must have a matching change in `docs/es/index.html` — the site is bilingual and the two files are structurally identical except for copy.
- New injected/dynamic content must use the existing `<!-- MARKER:START -->...<!-- MARKER:END -->` comment-pair convention, substituted via `re.sub(..., flags=re.DOTALL)`, matching `update_site.py`/`update_strava.py`.
- No client-side API calls for data — all dynamic content is written at build time by a Python script run on a schedule, matching the existing architecture.
- Reuse existing CSS custom properties (`--display`, `--serif`, `--mono`, `--crimson`, `--paper`, `--ink`, `--text`, `--text-dim`, `--line`, `--line-strong`, `--ease-smooth`) — no new hard-coded colors or fonts.
- Cron schedules use a 5am UTC base line, preserving the existing stagger (workflows that write to the same files must not run at the same minute).
- Anything new that isn't part of a résumé (decorative sections, modals) must be added to the `@media print` hide-list in `docs/style.css` alongside the existing `.quiz-backdrop, .ticket-backdrop` etc.

---

### Task 1: Align all workflow schedules to 5am UTC

**Files:**
- Modify: `.github/workflows/goodreads.yml:4`
- Modify: `.github/workflows/letterboxd.yml:4`
- Modify: `.github/workflows/update-site.yml:4`
- Modify: `.github/workflows/update-strava.yml:4`

**Interfaces:** None — this task only changes `cron:` values, no code interfaces.

- [ ] **Step 1: Update `goodreads.yml`'s cron to 5am UTC**

In `.github/workflows/goodreads.yml`, change:
```yaml
    - cron: "0 8 * * *"
```
to:
```yaml
    - cron: "0 5 * * *"
```

- [ ] **Step 2: Update `letterboxd.yml`'s cron to 5am UTC**

In `.github/workflows/letterboxd.yml`, change:
```yaml
    - cron: "0 8 * * *"
```
to:
```yaml
    - cron: "0 5 * * *"
```

- [ ] **Step 3: Update `update-site.yml`'s cron to 5:15am UTC**

In `.github/workflows/update-site.yml`, change:
```yaml
    - cron: "15 8 * * *"
```
to:
```yaml
    - cron: "15 5 * * *"
```

- [ ] **Step 4: Update `update-strava.yml`'s cron to 5:45am UTC**

In `.github/workflows/update-strava.yml`, change:
```yaml
    - cron: "45 8 * * *"
```
to:
```yaml
    - cron: "45 5 * * *"
```

- [ ] **Step 5: Verify all four crons**

Run: `grep -n "cron:" .github/workflows/*.yml`
Expected:
```
.github/workflows/goodreads.yml:    - cron: "0 5 * * *"
.github/workflows/letterboxd.yml:    - cron: "0 5 * * *"
.github/workflows/update-site.yml:    - cron: "15 5 * * *"
.github/workflows/update-strava.yml:    - cron: "45 5 * * *"
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/goodreads.yml .github/workflows/letterboxd.yml .github/workflows/update-site.yml .github/workflows/update-strava.yml
git commit -m "chore: align build-time workflow schedules to 5am UTC"
```

---

### Task 2: Box Office data — GitHub commit-count script and workflow

**Files:**
- Create: `.github/scripts/update_github_stats.py`
- Create: `.github/workflows/update-github-stats.yml`

**Interfaces:**
- Produces: HTML marker pair `<!-- SITE-BOX-OFFICE:START -->…<!-- SITE-BOX-OFFICE:END -->`, written into `docs/index.html` and `docs/es/index.html`, containing a comma-formatted integer (e.g. `1,284`) — consumed by Task 3's markup.

- [ ] **Step 1: Write `update_github_stats.py`**

Create `.github/scripts/update_github_stats.py`:

```python
import json
import os
import re
import urllib.request

GITHUB_USERNAME = "cshields236"
SEARCH_URL = f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}"
SITE_PATHS = ["docs/index.html", "docs/es/index.html"]


def fetch_json(url):
    headers = {
        "Accept": "application/vnd.github.cloak-preview+json",
        "User-Agent": "conorshields.ie site sync (contact: con.shields1@gmail.com)",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_commit_count():
    data = fetch_json(SEARCH_URL)
    return data["total_count"]


def format_count(count):
    return f"{count:,}"


def main():
    count = get_commit_count()
    formatted = format_count(count)

    for site_path in SITE_PATHS:
        with open(site_path, "r") as f:
            html = f.read()
        html = re.sub(
            r"<!-- SITE-BOX-OFFICE:START -->.*?<!-- SITE-BOX-OFFICE:END -->",
            f"<!-- SITE-BOX-OFFICE:START -->{formatted}<!-- SITE-BOX-OFFICE:END -->",
            html, flags=re.DOTALL,
        )
        with open(site_path, "w") as f:
            f.write(html)

    print(f"Updated {len(SITE_PATHS)} site file(s): {formatted} commits.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Sanity-check the substitution logic against a fixture string**

Run:
```bash
python3 -c "
import re
html = '<span><!-- SITE-BOX-OFFICE:START -->0<!-- SITE-BOX-OFFICE:END --></span>'
result = re.sub(
    r'<!-- SITE-BOX-OFFICE:START -->.*?<!-- SITE-BOX-OFFICE:END -->',
    '<!-- SITE-BOX-OFFICE:START -->1,284<!-- SITE-BOX-OFFICE:END -->',
    html, flags=re.DOTALL,
)
assert result == '<span><!-- SITE-BOX-OFFICE:START -->1,284<!-- SITE-BOX-OFFICE:END --></span>', result
print('OK:', result)
"
```
Expected: `OK: <span><!-- SITE-BOX-OFFICE:START -->1,284<!-- SITE-BOX-OFFICE:END --></span>` with no assertion error.

- [ ] **Step 3: Create the workflow**

Create `.github/workflows/update-github-stats.yml`:

```yaml
name: Update site with GitHub commit stats
on:
  schedule:
    - cron: "55 5 * * *"
  workflow_dispatch:
jobs:
  update-github-stats:
    name: Update Box Office section
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Update GitHub stats
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python .github/scripts/update_github_stats.py
      - name: Commit and push if changed
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git diff --quiet || (git add docs/index.html docs/es/index.html && git commit -m "Update site with latest GitHub commit stats" && git push)
```

Note: this task's markers don't exist in `docs/index.html`/`docs/es/index.html` yet — that's Task 3. Running this script before Task 3 lands will fetch the count successfully but the `re.sub` will silently no-op (no match found), which is expected and harmless.

- [ ] **Step 4: Commit**

```bash
git add .github/scripts/update_github_stats.py .github/workflows/update-github-stats.yml
git commit -m "feat: add GitHub commit-count sync script and workflow"
```

---

### Task 3: Box Office section on the site

**Files:**
- Modify: `docs/index.html` (insert new section between the Toolkit and Experience sections)
- Modify: `docs/es/index.html` (same insertion point, Spanish copy)
- Modify: `docs/style.css` (new `.box-office-*` rules)

**Interfaces:**
- Consumes: the `SITE-BOX-OFFICE` marker pair from Task 2.
- Produces: `<section class="section box-office" id="box-office">` — no other task depends on this section's internals.

- [ ] **Step 1: Insert the English section**

In `docs/index.html`, find:
```html
</div>
</div>
</section>
<section class="section experience" id="experience">
```
(this is the end of the Toolkit `tech` section). Replace with:
```html
</div>
</div>
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

- [ ] **Step 2: Insert the Spanish section**

In `docs/es/index.html`, find the same anchor:
```html
</div>
</div>
</section>
<section class="section experience" id="experience">
```
Replace with:
```html
</div>
</div>
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

- [ ] **Step 3: Add nav links for the new section (both languages)**

In `docs/index.html`, the line `<a href="#experience">Engagements</a>` appears twice (once in `.nav-links`, once in `.mobile-menu`), byte-identical. Using a find-and-replace with "replace all occurrences" enabled, replace:
```html
<a href="#experience">Engagements</a>
```
with:
```html
<a href="#box-office">Box Office</a>
<a href="#experience">Engagements</a>
```
This inserts the new link immediately before both existing occurrences in one pass.

In `docs/es/index.html`, the line `<a href="#experience">Actuaciones</a>` also appears twice, identically. Using the same "replace all occurrences" approach, replace:
```html
<a href="#experience">Actuaciones</a>
```
with:
```html
<a href="#box-office">Taquilla</a>
<a href="#experience">Actuaciones</a>
```

- [ ] **Step 4: Add CSS for the stat display**

In `docs/style.css`, find the end of the Tech section's rules:
```css
.tech-tag:hover {
    border-color: var(--crimson);
    color: var(--crimson);
}
```
Insert immediately after (before the `/* ─── Timeline (Engagements) ─── */` comment):
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
```

- [ ] **Step 5: Hide the section from the print stylesheet**

In `docs/style.css`, find:
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop {
        display: none !important;
    }
```
Replace with:
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books, .section.box-office,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop {
        display: none !important;
    }
```

- [ ] **Step 6: Verify structure and render locally**

Run: `grep -c 'class="section box-office"' docs/index.html docs/es/index.html`
Expected: `docs/index.html:1` and `docs/es/index.html:1`.

Then serve the site and eyeball it:
```bash
cd docs && python3 -m http.server 8000
```
Open `http://localhost:8000/` in a browser, scroll past "Toolkit" and confirm a "Box Office" section renders with a large "0" and the caption "Tickets Sold — Commits, All-Time", styled consistently with the rest of the page (crimson number, mono caption). Confirm the "Box Office" nav link scrolls to it. Stop the server (Ctrl+C) when done.

- [ ] **Step 7: Commit**

```bash
git add docs/index.html docs/es/index.html docs/style.css
git commit -m "feat: add Box Office section showing GitHub commit count"
```

---

### Task 4: Now Casting — rename and copy pass on the contact section

**Files:**
- Modify: `docs/index.html:426,431,457`
- Modify: `docs/es/index.html:426,431,457`

**Interfaces:** None — copy-only changes, no new markup or ids.

- [ ] **Step 1: Rename the English section label and update the copy**

In `docs/index.html`, change:
```html
<span class="section-label">Box Office</span>
<h2 class="section-title">Get in Touch</h2>
```
to:
```html
<span class="section-label">Now Casting</span>
<h2 class="section-title">Get in Touch</h2>
```

Then change:
```html
<p class="contact-text">Interested in working together or just want to chat? Drop me a message.</p>
```
to:
```html
<p class="contact-text">Casting for new collaborations and conversations — submit your details below.</p>
```

Then change:
```html
<button class="form-submit" type="submit">Send Message</button>
```
to:
```html
<button class="form-submit" type="submit">Submit for Consideration</button>
```

- [ ] **Step 2: Rename the Spanish section label and update the copy**

In `docs/es/index.html`, change:
```html
<span class="section-label">Taquilla</span>
<h2 class="section-title">Ponte en Contacto</h2>
```
to:
```html
<span class="section-label">Casting Abierto</span>
<h2 class="section-title">Ponte en Contacto</h2>
```

Then change:
```html
<p class="contact-text">¿Interesado en trabajar juntos o simplemente quieres charlar? Envíame un mensaje.</p>
```
to:
```html
<p class="contact-text">En casting para nuevas colaboraciones y conversaciones — envía tus datos a continuación.</p>
```

Then change:
```html
<button class="form-submit" type="submit">Enviar Mensaje</button>
```
to:
```html
<button class="form-submit" type="submit">Enviar Audición</button>
```

- [ ] **Step 3: Verify no leftover "Box Office"/"Taquilla" label on the contact section**

Run: `grep -n "section-label" docs/index.html docs/es/index.html`
Expected: the `box-office` section's label ("Opening Weekend"/"Fin de Semana de Estreno") appears once each, and the contact section's label now reads "Now Casting" (EN) / "Casting Abierto" (ES) — "Box Office" and "Taquilla" no longer appear as the contact section's label.

- [ ] **Step 4: Commit**

```bash
git add docs/index.html docs/es/index.html
git commit -m "feat: reskin contact section copy as a casting call"
```

---

### Task 5: Now Casting — audition confirmation modal (markup, CSS, and JS wiring)

**Files:**
- Modify: `docs/index.html` (new `casting-backdrop` modal markup)
- Modify: `docs/es/index.html` (same, Spanish copy)
- Modify: `docs/style.css` (extend Ticket Stub CSS to cover the casting modal)
- Modify: `docs/main.js` (remove the inline mailto submit handler, add `initCasting()`)

**Interfaces:**
- Consumes: `lockScroll()`/`unlockScroll()` and the `LANG` constant already defined at the top of `docs/main.js`.
- Produces: `initCasting()` function, called from the `DOMContentLoaded` handler alongside `initTicket()`. No other task depends on it.

- [ ] **Step 1: Add the English modal markup**

In `docs/index.html`, find:
```html
<a class="ticket-continue" href="#" id="ticket-continue">Continue to Email →</a>
</div>
</div>
</div>
<script src="/main.js"></script>
```
Replace with:
```html
<a class="ticket-continue" href="#" id="ticket-continue">Continue to Email →</a>
</div>
</div>
</div>
<div class="casting-backdrop" id="casting-backdrop">
<div aria-labelledby="casting-heading" aria-modal="true" class="casting-notice" role="dialog">
<button aria-label="Close" class="casting-close" id="casting-close">×</button>
<div class="casting-stub">
<span class="casting-eyebrow">Casting Notice</span>
<span class="casting-serial" id="casting-serial"></span>
</div>
<div class="casting-perf"></div>
<div class="casting-main">
<h2 class="casting-title" id="casting-heading">Submission Received</h2>
<p class="casting-detail">Your details have been logged for consideration. Expect a callback within 1–2 business days.</p>
<div class="casting-meta">
<span><span>DATE:</span> <span id="casting-date"></span></span>
<span>ROLE: COLLABORATOR</span>
</div>
<a class="casting-continue" href="#" id="casting-continue">Continue to Email →</a>
</div>
</div>
</div>
<script src="/main.js"></script>
```

- [ ] **Step 2: Add the Spanish modal markup**

In `docs/es/index.html`, find:
```html
<a class="ticket-continue" href="#" id="ticket-continue">Continuar al Correo →</a>
</div>
</div>
</div>
<script src="/main.js"></script>
```
Replace with:
```html
<a class="ticket-continue" href="#" id="ticket-continue">Continuar al Correo →</a>
</div>
</div>
</div>
<div class="casting-backdrop" id="casting-backdrop">
<div aria-labelledby="casting-heading" aria-modal="true" class="casting-notice" role="dialog">
<button aria-label="Close" class="casting-close" id="casting-close">×</button>
<div class="casting-stub">
<span class="casting-eyebrow">Aviso de Casting</span>
<span class="casting-serial" id="casting-serial"></span>
</div>
<div class="casting-perf"></div>
<div class="casting-main">
<h2 class="casting-title" id="casting-heading">Solicitud Recibida</h2>
<p class="casting-detail">Tus datos han sido registrados para su consideración. Espera noticias en 1–2 días hábiles.</p>
<div class="casting-meta">
<span><span>FECHA:</span> <span id="casting-date"></span></span>
<span>PAPEL: COLABORADOR</span>
</div>
<a class="casting-continue" href="#" id="casting-continue">Continuar al Correo →</a>
</div>
</div>
</div>
<script src="/main.js"></script>
```

- [ ] **Step 3: Extend the Ticket Stub CSS to cover the casting modal**

In `docs/style.css`, this whole block currently styles only the ticket modal:
```css
/* ─── Ticket Stub ─── */
.ticket-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(6, 12, 10, 0.72);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s var(--ease-smooth);
}

.ticket-backdrop.show {
    opacity: 1;
    pointer-events: all;
}

.ticket {
    width: 100%;
    max-width: 420px;
    background: var(--paper);
    color: var(--ink);
    border-radius: 8px;
    position: relative;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    transform: scale(0.94);
    opacity: 0;
    transition: transform 0.4s var(--ease-smooth), opacity 0.4s var(--ease-smooth);
    overflow: hidden;
}

.ticket-backdrop.show .ticket {
    transform: scale(1);
    opacity: 1;
}

.ticket-close {
    position: absolute;
    top: 0.85rem;
    right: 1rem;
    background: none;
    border: none;
    color: var(--ink);
    opacity: 0.5;
    font-family: var(--mono);
    font-size: 1.1rem;
    line-height: 1;
    cursor: pointer;
    transition: opacity 0.2s;
    z-index: 1;
}

.ticket-close:hover {
    opacity: 1;
}

.ticket-stub {
    padding: 1.1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--paper-dim);
}

.ticket-eyebrow {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--crimson);
}

.ticket-serial {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--ink);
    opacity: 0.55;
}

.ticket-perf {
    position: relative;
    height: 0;
    border-top: 2px dashed rgba(34, 31, 24, 0.35);
}

.ticket-perf::before,
.ticket-perf::after {
    content: '';
    position: absolute;
    top: -9px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(6, 12, 10, 0.72);
}

.ticket-perf::before {
    left: -9px;
}

.ticket-perf::after {
    right: -9px;
}

.ticket-main {
    padding: 1.6rem 1.75rem 1.9rem;
}

.ticket-title {
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.3rem;
    text-transform: uppercase;
    letter-spacing: 0.005em;
    color: var(--ink);
}

.ticket-detail {
    font-family: var(--serif);
    font-size: 0.92rem;
    line-height: 1.55;
    color: var(--ink);
    opacity: 0.75;
    margin-top: 0.75rem;
}

.ticket-meta {
    display: flex;
    justify-content: space-between;
    margin-top: 1.1rem;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink);
    opacity: 0.6;
}

.ticket-continue {
    display: inline-block;
    margin-top: 1.4rem;
    padding: 0.75rem 1.5rem;
    background: var(--ink);
    color: var(--paper);
    border-radius: 100px;
    text-decoration: none;
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: opacity 0.2s;
}

.ticket-continue:hover {
    opacity: 0.85;
}

@media (prefers-reduced-motion: reduce) {
    .ticket-backdrop,
    .ticket {
        transition: none;
    }
}
```

Replace the entire block with (adds the `.casting-*` equivalents to every selector, sharing the same rules):

```css
/* ─── Ticket Stub & Casting Notice ─── */
.ticket-backdrop,
.casting-backdrop {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(6, 12, 10, 0.72);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s var(--ease-smooth);
}

.ticket-backdrop.show,
.casting-backdrop.show {
    opacity: 1;
    pointer-events: all;
}

.ticket,
.casting-notice {
    width: 100%;
    max-width: 420px;
    background: var(--paper);
    color: var(--ink);
    border-radius: 8px;
    position: relative;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    transform: scale(0.94);
    opacity: 0;
    transition: transform 0.4s var(--ease-smooth), opacity 0.4s var(--ease-smooth);
    overflow: hidden;
}

.ticket-backdrop.show .ticket,
.casting-backdrop.show .casting-notice {
    transform: scale(1);
    opacity: 1;
}

.ticket-close,
.casting-close {
    position: absolute;
    top: 0.85rem;
    right: 1rem;
    background: none;
    border: none;
    color: var(--ink);
    opacity: 0.5;
    font-family: var(--mono);
    font-size: 1.1rem;
    line-height: 1;
    cursor: pointer;
    transition: opacity 0.2s;
    z-index: 1;
}

.ticket-close:hover,
.casting-close:hover {
    opacity: 1;
}

.ticket-stub,
.casting-stub {
    padding: 1.1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--paper-dim);
}

.ticket-eyebrow,
.casting-eyebrow {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--crimson);
}

.ticket-serial,
.casting-serial {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--ink);
    opacity: 0.55;
}

.ticket-perf,
.casting-perf {
    position: relative;
    height: 0;
    border-top: 2px dashed rgba(34, 31, 24, 0.35);
}

.ticket-perf::before,
.ticket-perf::after,
.casting-perf::before,
.casting-perf::after {
    content: '';
    position: absolute;
    top: -9px;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(6, 12, 10, 0.72);
}

.ticket-perf::before,
.casting-perf::before {
    left: -9px;
}

.ticket-perf::after,
.casting-perf::after {
    right: -9px;
}

.ticket-main,
.casting-main {
    padding: 1.6rem 1.75rem 1.9rem;
}

.ticket-title,
.casting-title {
    font-family: var(--display);
    font-weight: 800;
    font-size: 1.3rem;
    text-transform: uppercase;
    letter-spacing: 0.005em;
    color: var(--ink);
}

.ticket-detail,
.casting-detail {
    font-family: var(--serif);
    font-size: 0.92rem;
    line-height: 1.55;
    color: var(--ink);
    opacity: 0.75;
    margin-top: 0.75rem;
}

.ticket-meta,
.casting-meta {
    display: flex;
    justify-content: space-between;
    margin-top: 1.1rem;
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--ink);
    opacity: 0.6;
}

.ticket-continue,
.casting-continue {
    display: inline-block;
    margin-top: 1.4rem;
    padding: 0.75rem 1.5rem;
    background: var(--ink);
    color: var(--paper);
    border-radius: 100px;
    text-decoration: none;
    font-family: var(--mono);
    font-size: 0.72rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    transition: opacity 0.2s;
}

.ticket-continue:hover,
.casting-continue:hover {
    opacity: 0.85;
}

@media (prefers-reduced-motion: reduce) {
    .ticket-backdrop,
    .ticket,
    .casting-backdrop,
    .casting-notice {
        transition: none;
    }
}
```

- [ ] **Step 4: Hide the casting modal from the print stylesheet**

In `docs/style.css`, find (this was already edited in Task 3 Step 5 to include `.section.box-office` — match against that updated state):
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books, .section.box-office,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop {
        display: none !important;
    }
```
Replace with:
```css
    .nav, .mobile-menu, .resume-btn, .hero-avatar, .hero-scroll,
    .section.films, .section.routes, .section.books, .section.box-office,
    .contact-form, .footer,
    .credits-roll, .quiz-backdrop, .ticket-backdrop, .casting-backdrop {
        display: none !important;
    }
```

- [ ] **Step 5: Remove the old inline mailto submit handler in `main.js`**

In `docs/main.js`, find:
```js
    const form = document.getElementById('contact-form');
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = form.querySelector('#name').value;
        const email = form.querySelector('#email').value;
        const message = form.querySelector('#message').value;
        const subject = encodeURIComponent(`Message from ${name}`);
        const body = encodeURIComponent(`From: ${name} (${email})\n\n${message}`);
        window.location.href = `mailto:con.shields1@gmail.com?subject=${subject}&body=${body}`;
        form.reset();
    });

    initQuiz();
    initTicket();
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
    initRoutes();
```

- [ ] **Step 6: Add `initCasting()`**

In `docs/main.js`, find the end of `initTicket()`:
```js
    closeBtn.addEventListener('click', closeTicket);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeTicket(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && backdrop.classList.contains('show')) closeTicket(); });
    continueLink.addEventListener('click', () => { setTimeout(closeTicket, 300); });
}

/* ─── Closing Credits ───
```
Replace with:
```js
    closeBtn.addEventListener('click', closeTicket);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeTicket(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && backdrop.classList.contains('show')) closeTicket(); });
    continueLink.addEventListener('click', () => { setTimeout(closeTicket, 300); });
}

/* ─── Casting Notice ───
   Intercepts the contact form's submit with a themed confirmation before
   handing off to the visitor's email client, mirroring initTicket(). */
function initCasting() {
    const backdrop = document.getElementById('casting-backdrop');
    const closeBtn = document.getElementById('casting-close');
    const continueLink = document.getElementById('casting-continue');
    const dateEl = document.getElementById('casting-date');
    const serialEl = document.getElementById('casting-serial');
    const form = document.getElementById('contact-form');
    if (!backdrop || !form) return;

    const dateLocale = LANG === 'es' ? 'es-ES' : 'en-GB';

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = form.querySelector('#name').value;
        const email = form.querySelector('#email').value;
        const message = form.querySelector('#message').value;
        const subject = encodeURIComponent(`Message from ${name}`);
        const body = encodeURIComponent(`From: ${name} (${email})\n\n${message}`);
        continueLink.href = `mailto:con.shields1@gmail.com?subject=${subject}&body=${body}`;

        const now = new Date();
        dateEl.textContent = now.toLocaleDateString(dateLocale, { day: '2-digit', month: 'short', year: 'numeric' });
        serialEl.textContent = '#' + now.getTime().toString().slice(-6);
        backdrop.classList.add('show');
        lockScroll();
        form.reset();
    });

    function closeCasting() {
        if (!backdrop.classList.contains('show')) return;
        backdrop.classList.remove('show');
        unlockScroll();
    }

    closeBtn.addEventListener('click', closeCasting);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeCasting(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && backdrop.classList.contains('show')) closeCasting(); });
    continueLink.addEventListener('click', () => { setTimeout(closeCasting, 300); });
}

/* ─── Closing Credits ───
```

- [ ] **Step 7: Verify structure**

Run: `grep -n "initCasting\|casting-backdrop\|casting-continue" docs/main.js`
Expected: shows the `initCasting` function definition, its call in the `DOMContentLoaded` handler, and its use of `casting-backdrop`/`casting-continue` element ids — confirming the function is defined once and invoked once.

- [ ] **Step 8: Manually test the full flow in a browser**

```bash
cd docs && python3 -m http.server 8000
```
Open `http://localhost:8000/#contact`, fill in the name/email/message fields, click "Submit for Consideration". Confirm:
1. The page does NOT navigate away immediately.
2. A paper-styled "Casting Notice" modal appears with a serial number and today's date.
3. Clicking "Continue to Email →" opens the mail client (or triggers the `mailto:` navigation) and the modal closes shortly after.
4. Clicking the "×" or the backdrop closes the modal without navigating.
5. Separately, click the raw `con.shields1@gmail.com` link in the contact-info list (not the form) — confirm the original "Admit One" ticket modal still appears unaffected.

Stop the server (Ctrl+C) when done.

- [ ] **Step 9: Commit**

```bash
git add docs/index.html docs/es/index.html docs/style.css docs/main.js
git commit -m "feat: add audition confirmation modal for the casting-call contact form"
```

---

### Task 6: Currently Reading — Goodreads shelf fetch in `update_site.py`

**Files:**
- Modify: `.github/scripts/update_site.py`

**Interfaces:**
- Produces: `get_currently_reading(limit=3)` returning a list of book dicts shaped like `get_books()`'s output; `render_currently_reading_block(books, heading)` returning an HTML string (empty string if `books` is empty) — consumed by Task 7's markers.
- Consumes: existing `render_books(books)` helper (reused as-is for the currently-reading list items).

- [ ] **Step 1: Add the currently-reading RSS constant and make `SITE_PATHS` language-aware**

In `.github/scripts/update_site.py`, find:
```python
LETTERBOXD_USERNAME = "cshields_"
GOODREADS_USER_ID = "106016596"
LETTERBOXD_RSS = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
LETTERBOXD_PROFILE = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
GOODREADS_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=read"
SITE_PATHS = ["docs/index.html", "docs/es/index.html"]
```
Replace with:
```python
LETTERBOXD_USERNAME = "cshields_"
GOODREADS_USER_ID = "106016596"
LETTERBOXD_RSS = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/rss/"
LETTERBOXD_PROFILE = f"https://letterboxd.com/{LETTERBOXD_USERNAME}/"
GOODREADS_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=read"
GOODREADS_CURRENTLY_READING_RSS = f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=currently-reading"
SITE_PATHS = {"en": "docs/index.html", "es": "docs/es/index.html"}

STRINGS = {
    "en": {"currently_reading": "Currently Reading"},
    "es": {"currently_reading": "Actualmente Leyendo"},
}
```

- [ ] **Step 2: Add `get_currently_reading()`**

In `.github/scripts/update_site.py`, find the end of `get_books()`:
```python
        if len(books) == 6:
            break
    return books


def render_favourites(films):
```
Replace with:
```python
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
```

- [ ] **Step 3: Add `render_currently_reading_block()`**

In `.github/scripts/update_site.py`, find the end of `render_books()`:
```python
            f'                    <span class="book-rating">{b["stars_html"]}</span>\n'
            f'                </div>'
        )
    return "\n".join(items)


def main():
```
Replace with:
```python
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
```

- [ ] **Step 4: Rewrite `main()` to be language-aware and inject the currently-reading block**

In `.github/scripts/update_site.py`, find:
```python
def main():
    favourites = get_favourites()
    watched = get_recent_watched()
    books = get_books()

    for site_path in SITE_PATHS:
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

        with open(site_path, "w") as f:
            f.write(html)

    fav_count = len(favourites) if favourites is not None else "unchanged"
    print(f"Updated {len(SITE_PATHS)} site file(s): {fav_count} favourites, {len(watched)} watched, {len(books)} books.")


if __name__ == "__main__":
    main()
```
Replace with:
```python
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

        currently_reading_html = render_currently_reading_block(currently_reading, STRINGS[lang]["currently_reading"])
        html = re.sub(
            r"<!-- SITE-CURRENTLY-READING:START -->.*?<!-- SITE-CURRENTLY-READING:END -->",
            f"<!-- SITE-CURRENTLY-READING:START -->{currently_reading_html}<!-- SITE-CURRENTLY-READING:END -->",
            html, flags=re.DOTALL,
        )

        with open(site_path, "w") as f:
            f.write(html)

    fav_count = len(favourites) if favourites is not None else "unchanged"
    print(f"Updated {len(SITE_PATHS)} site file(s): {fav_count} favourites, {len(watched)} watched, {len(books)} books, {len(currently_reading)} currently reading.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Sanity-check the empty-shelf case against a fixture string**

Run:
```bash
python3 -c "
import sys
sys.path.insert(0, '.github/scripts')
from update_site import render_currently_reading_block
assert render_currently_reading_block([], 'Currently Reading') == ''
result = render_currently_reading_block(
    [{'title': 'Test Book', 'author': 'Test Author', 'rating': 0, 'stars_html': '', 'cover': ''}],
    'Currently Reading',
)
assert '<h3 class=\"books-subtitle\">Currently Reading</h3>' in result, result
assert 'Test Book' in result, result
print('OK')
"
```
Expected: `OK` with no assertion error. This confirms the empty-shelf case renders nothing (so Task 7's markers collapse to nothing) and the populated case includes both the heading and the book title.

- [ ] **Step 6: Commit**

```bash
git add .github/scripts/update_site.py
git commit -m "feat: fetch currently-reading Goodreads shelf in update_site.py"
```

---

### Task 7: Currently Reading — site markers and CSS

**Files:**
- Modify: `docs/index.html:369` (insert `SITE-CURRENTLY-READING` markers above the existing books list)
- Modify: `docs/es/index.html:369` (same insertion point)
- Modify: `docs/style.css` (share `.films-subtitle`'s look with a new `.books-subtitle`)

**Interfaces:**
- Consumes: the `SITE-CURRENTLY-READING` marker content produced by Task 6's `main()`.

- [ ] **Step 1: Insert the markers in `docs/index.html`**

Find:
```html
<a class="section-link" href="https://www.goodreads.com/user/show/106016596" rel="noopener" target="_blank">Goodreads Profile</a>
</div>
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```
Replace with:
```html
<a class="section-link" href="https://www.goodreads.com/user/show/106016596" rel="noopener" target="_blank">Goodreads Profile</a>
</div>
<!-- SITE-CURRENTLY-READING:START --><!-- SITE-CURRENTLY-READING:END -->
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```

- [ ] **Step 2: Insert the markers in `docs/es/index.html`**

Find:
```html
<a class="section-link" href="https://www.goodreads.com/user/show/106016596" rel="noopener" target="_blank">Perfil de Goodreads</a>
</div>
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```
Replace with:
```html
<a class="section-link" href="https://www.goodreads.com/user/show/106016596" rel="noopener" target="_blank">Perfil de Goodreads</a>
</div>
<!-- SITE-CURRENTLY-READING:START --><!-- SITE-CURRENTLY-READING:END -->
<div class="books-list reveal">
<!-- SITE-BOOKS:START -->
```

- [ ] **Step 3: Add `.books-subtitle` CSS sharing `.films-subtitle`'s rules**

In `docs/style.css`, find:
```css
.films-subtitle {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 1.4rem;
    text-align: center;
}
```
Replace with:
```css
.films-subtitle,
.books-subtitle {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 1.4rem;
    text-align: center;
}
```

- [ ] **Step 4: Run `update_site.py` end-to-end and verify the rendered markup**

This requires network access (fetches real Letterboxd/Goodreads feeds).

Run: `python3 .github/scripts/update_site.py`
Expected output: a line like `Updated 2 site file(s): N favourites, N watched, N books, N currently reading.`

Then run: `git diff docs/index.html docs/es/index.html`
Expected: if your Goodreads "currently reading" shelf has books on it, the diff shows a new `<div class="books-block reveal">` with a `<h3 class="books-subtitle">Currently Reading</h3>` (or `Actualmente Leyendo` in the ES file) inserted above the existing books list, containing `.book-item` entries. If the shelf is empty, the diff shows no change to that region (the markers stay adjacent with nothing between them).

- [ ] **Step 5: Visually confirm in a browser**

```bash
cd docs && python3 -m http.server 8000
```
Open `http://localhost:8000/#books` and confirm the "Currently Reading" block (if populated) renders above the main reading list with the same book-cover/title/author styling, and the "Intermission / Reading List" header and Goodreads link are unaffected. Stop the server (Ctrl+C) when done.

- [ ] **Step 6: Commit**

```bash
git add docs/index.html docs/es/index.html docs/style.css
git commit -m "feat: render Currently Reading block on the site"
```

---

### Task 8: Currently Reading — README and `goodreads.yml`

**Files:**
- Modify: `README.md` (new "Currently Reading" section above "Last 10 Books I've Read")
- Modify: `.github/workflows/goodreads.yml` (second action step for the `currently-reading` shelf, plus the missing commit-and-push step)

**Interfaces:** None — this task only touches README content and workflow config.

- [ ] **Step 1: Add the README section and markers**

In `README.md`, find:
```markdown
# 📚 Last 10 Books I've Read 
<!-- GOODREADS-LIST:START -->
```
Replace with:
```markdown
# 📖 Currently Reading
<!-- GOODREADS-CURRENTLY-READING:START -->
<!-- GOODREADS-CURRENTLY-READING:END -->

# 📚 Last 10 Books I've Read 
<!-- GOODREADS-LIST:START -->
```

- [ ] **Step 2: Add the second workflow step and the missing commit step**

The `zwacky/goodreads-profile-workflow` action writes directly to `README.md` but does not commit — the existing workflow is missing that step entirely, so it currently doesn't actually persist changes; this step is required for both the existing "read" shelf sync and the new "currently-reading" sync to take effect.

In `.github/workflows/goodreads.yml`, find:
```yaml
    steps:
      - uses: actions/checkout@v2
      - uses: zwacky/goodreads-profile-workflow@main
        with:
          # Replace this with your goodreads user id (go to "My Books" on goodreads to see it in the URL)
          goodreads_user_id: "106016596"
          shelf: "read"
          template: "- [$title]($url) by $author ($published_year) $my_rating_stars <br />"
```
Replace with:
```yaml
    steps:
      - uses: actions/checkout@v2
      - uses: zwacky/goodreads-profile-workflow@main
        with:
          # Replace this with your goodreads user id (go to "My Books" on goodreads to see it in the URL)
          goodreads_user_id: "106016596"
          shelf: "read"
          template: "- [$title]($url) by $author ($published_year) $my_rating_stars <br />"
      - uses: zwacky/goodreads-profile-workflow@main
        with:
          goodreads_user_id: "106016596"
          shelf: "currently-reading"
          comment_tag_name: "GOODREADS-CURRENTLY-READING"
          template: "- [$title]($url) by $author <br />"
      - name: Commit and push if changed
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"
          git diff --quiet || (git add README.md && git commit -m "Synced and updated with user's Goodreads data" && git push)
```

- [ ] **Step 3: Verify the workflow YAML is well-formed**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/goodreads.yml'))" 2>&1 || python3 -c "import json,sys; print('yaml module unavailable, skipping strict parse')"`
Expected: no exception printed (if the `yaml` module is unavailable in this environment, the fallback message is fine — the important structural check is Step 4 below).

Run: `grep -n "comment_tag_name\|shelf:\|Commit and push" .github/workflows/goodreads.yml`
Expected:
```
          shelf: "read"
          shelf: "currently-reading"
          comment_tag_name: "GOODREADS-CURRENTLY-READING"
      - name: Commit and push if changed
```

- [ ] **Step 4: Verify the README markers**

Run: `grep -n "GOODREADS-CURRENTLY-READING\|Currently Reading" README.md`
Expected:
```
# 📖 Currently Reading
<!-- GOODREADS-CURRENTLY-READING:START -->
<!-- GOODREADS-CURRENTLY-READING:END -->
```

- [ ] **Step 5: Commit**

```bash
git add README.md .github/workflows/goodreads.yml
git commit -m "feat: sync Goodreads currently-reading shelf into the README"
```

---

## After all tasks

Push the branch and open a PR:

```bash
git push -u origin fix/routes-photos
gh pr create --title "Add Box Office, Now Casting, and currently-reading features" --body "$(cat <<'EOF'
## Summary
- Adds a "Box Office" section showing GitHub commit count as ticket sales, synced by a new build-time script/workflow
- Reskins the contact section as "Now Casting" with its own audition-confirmation modal on form submit
- Surfaces a Goodreads "currently reading" shelf on the site and in the README
- Aligns all build-time workflow schedules to a shared 5am UTC cron

## Test plan
- [ ] Manually run each new/changed workflow via `workflow_dispatch` and confirm the expected diff lands
- [ ] Verify the Box Office section renders with real commit data after the first scheduled run
- [ ] Verify the casting form shows the confirmation modal and still hands off to email
- [ ] Verify the raw email link's ticket modal still works unaffected
- [ ] Verify the Currently Reading block appears/disappears correctly based on the Goodreads shelf's contents

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
