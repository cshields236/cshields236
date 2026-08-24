const LANG = document.documentElement.lang === 'es' ? 'es' : 'en';
const dateLocale = LANG === 'es' ? 'es-ES' : 'en-GB';

let scrollLockCount = 0;
function lockScroll() {
    scrollLockCount++;
    document.body.style.overflow = 'hidden';
}
function unlockScroll() {
    scrollLockCount = Math.max(0, scrollLockCount - 1);
    if (scrollLockCount === 0) document.body.style.overflow = '';
}

document.addEventListener('DOMContentLoaded', () => {
    const nav = document.getElementById('nav');
    const toggle = document.querySelector('.nav-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const reveals = document.querySelectorAll('.reveal');

    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 50);
    });

    toggle.addEventListener('click', () => {
        const opening = !mobileMenu.classList.contains('open');
        mobileMenu.classList.toggle('open');
        if (opening) lockScroll(); else unlockScroll();
    });

    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            if (mobileMenu.classList.contains('open')) unlockScroll();
            mobileMenu.classList.remove('open');
        });
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    reveals.forEach(el => observer.observe(el));

    initQuiz();
    initTicket();
    initCasting();
    initCreditsRoll();
    initFilmsCarousel();
    initFilmFlip();
    initRoutes();
    initReel();

    const resumeBtn = document.getElementById('resume-btn');
    if (resumeBtn) resumeBtn.addEventListener('click', () => window.print());
});

function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

function sameSet(a, b) {
    if (a.length !== b.length) return false;
    const as = [...a].sort();
    const bs = [...b].sort();
    return as.every((v, i) => v === bs[i]);
}

/* ─── Pop Quiz ───
   Answers are read live from the page's own content (hero location,
   favourite films, book authors) so the quiz never drifts out of sync
   with the Letterboxd/Goodreads auto-updates. Film/book/author names
   are proper nouns and stay untranslated in both languages. */
const QUIZ_I18N = {
    en: {
        placeDecoys: ['Dublin, Ireland', 'Cork, Ireland', 'Belfast', 'Galway, Ireland', 'Manchester, UK', 'Edinburgh, UK'],
        authorDecoys: ['George Orwell', 'Virginia Woolf', 'James Joyce'],
        titleDecoys: ['1984', 'The Great Gatsby', 'Pride and Prejudice', 'Brave New World'],
        qBorn: 'Where was Conor born?',
        qFilms: 'Which two of these are among his all-time favourite films?',
        qFilmsHint: '(pick 2)',
        qCity: 'Where does he live now?',
        qAuthor: 'Which author shows up twice on his reading list?',
        qFallbackTitle: 'Which of these is currently on his reading list?',
        eyebrow: 'Before You Go…',
        heading: 'One Quick Quiz',
        next: 'Next',
        seeScore: 'See Score',
        replay: 'Watch It Again',
        flavor: {
            0: 'Might want to scroll back up.',
            1: 'Might want to scroll back up.',
            2: 'Half marks — skim reader.',
            3: 'Solid. You were paying attention.',
            4: 'Perfect. Did you screenshot my Letterboxd?',
        },
    },
    es: {
        placeDecoys: ['Dublín, Irlanda', 'Cork, Irlanda', 'Belfast', 'Galway, Irlanda', 'Mánchester, Reino Unido', 'Edimburgo, Reino Unido'],
        authorDecoys: ['George Orwell', 'Virginia Woolf', 'James Joyce'],
        titleDecoys: ['1984', 'El Gran Gatsby', 'Orgullo y Prejuicio', 'Un Mundo Feliz'],
        qBorn: '¿Dónde nació Conor?',
        qFilms: '¿Cuáles dos de estas películas están entre sus favoritas de siempre?',
        qFilmsHint: '(elige 2)',
        qCity: '¿Dónde vive ahora?',
        qAuthor: '¿Qué autor aparece dos veces en su lista de lectura?',
        qFallbackTitle: '¿Cuál de estos está actualmente en su lista de lectura?',
        eyebrow: 'Antes De Irte…',
        heading: 'Un Quiz Rápido',
        next: 'Siguiente',
        seeScore: 'Ver Puntaje',
        replay: 'Verlo de Nuevo',
        flavor: {
            0: 'Tal vez deberías desplazarte hacia arriba.',
            1: 'Tal vez deberías desplazarte hacia arriba.',
            2: 'Mitad de puntos — lector superficial.',
            3: 'Bien hecho. Estabas prestando atención.',
            4: 'Perfecto. ¿Le tomaste captura a mi Letterboxd?',
        },
    },
};

function buildQuizQuestions() {
    const t = QUIZ_I18N[LANG];

    let birthplace = 'Cavan, Ireland';
    let city = 'London, UK';
    const heroLoc = document.querySelector('.hero-location');
    if (heroLoc) {
        const parts = heroLoc.textContent.split('→').map(s => s.trim()).filter(Boolean);
        if (parts.length === 2) [birthplace, city] = parts;
    }

    const firstFilmsBlock = document.querySelector('#films .films-block');
    const favTitles = firstFilmsBlock
        ? Array.from(firstFilmsBlock.querySelectorAll('.film-title')).map(el => el.textContent.trim()).filter(Boolean)
        : [];

    const authorCounts = {};
    Array.from(document.querySelectorAll('#books .book-author')).forEach(el => {
        const name = el.textContent.trim();
        if (name) authorCounts[name] = (authorCounts[name] || 0) + 1;
    });
    const repeatedAuthor = Object.keys(authorCounts).find(name => authorCounts[name] >= 2);
    const singleAuthors = Object.keys(authorCounts).filter(name => authorCounts[name] === 1);

    const bookTitles = Array.from(document.querySelectorAll('#books .book-title'))
        .map(el => el.textContent.trim()).filter(Boolean);

    const questions = [];

    questions.push({
        q: t.qBorn,
        type: 'single',
        options: shuffle([birthplace, ...t.placeDecoys.filter(p => p !== birthplace && p !== city).slice(0, 3)]),
        correct: [birthplace],
    });

    const FILM_DECOYS = ['Titanic (1997)', 'Frozen (2013)', 'The Avengers (2012)', 'Jurassic Park (1993)', 'Fast & Furious 9 (2021)'];
    if (favTitles.length >= 2) {
        const correctFilms = shuffle(favTitles).slice(0, 2);
        const decoyFilms = FILM_DECOYS.filter(f => !favTitles.includes(f)).slice(0, 3);
        questions.push({
            q: t.qFilms,
            hint: t.qFilmsHint,
            type: 'multi',
            options: shuffle([...correctFilms, ...decoyFilms]),
            correct: correctFilms,
        });
    }

    questions.push({
        q: t.qCity,
        type: 'single',
        options: shuffle([city, ...t.placeDecoys.filter(p => p !== birthplace && p !== city).slice(0, 3)]),
        correct: [city],
    });

    if (repeatedAuthor) {
        const decoyAuthors = singleAuthors.length >= 3 ? singleAuthors.slice(0, 3) : [...singleAuthors, ...t.authorDecoys].slice(0, 3);
        questions.push({
            q: t.qAuthor,
            type: 'single',
            options: shuffle([repeatedAuthor, ...decoyAuthors]),
            correct: [repeatedAuthor],
        });
    } else if (bookTitles.length) {
        const realTitle = shuffle(bookTitles)[0];
        const decoyTitles = t.titleDecoys.filter(ti => !bookTitles.includes(ti)).slice(0, 3);
        questions.push({
            q: t.qFallbackTitle,
            type: 'single',
            options: shuffle([realTitle, ...decoyTitles]),
            correct: [realTitle],
        });
    }

    return questions;
}

function initQuiz() {
    const t = QUIZ_I18N[LANG];
    const backdrop = document.getElementById('quiz-backdrop');
    const closeBtn = document.getElementById('quiz-close');
    const progress = document.getElementById('quiz-progress');
    const body = document.getElementById('quiz-body');
    const footer = document.querySelector('.footer');
    if (!backdrop || !footer) return;

    const questions = buildQuizQuestions();
    if (!questions.length) return;

    let current = 0;
    const answers = [];
    let opened = false;

    function openQuiz() {
        if (opened) return;
        opened = true;
        current = 0;
        answers.length = 0;
        progress.innerHTML = questions.map(() => '<div class="quiz-dot"></div>').join('');
        renderStep();
        backdrop.classList.add('show');
        lockScroll();
    }

    function closeQuiz() {
        if (!backdrop.classList.contains('show')) return;
        backdrop.classList.remove('show');
        unlockScroll();
    }

    function getSelected(name) {
        return Array.from(body.querySelectorAll(`input[name="${name}"]:checked`)).map(i => i.value);
    }

    function renderStep() {
        Array.from(progress.children).forEach((d, i) => d.classList.toggle('on', i === current));

        if (current < questions.length) {
            const qData = questions[current];
            const inputType = qData.type === 'multi' ? 'checkbox' : 'radio';
            const name = `quiz-q${current}`;
            body.innerHTML = `
                <div class="quiz-q">
                    <div class="quiz-qtext"><span class="quiz-qnum">${String(current + 1).padStart(2, '0')}</span>${qData.q}${qData.hint ? `<span class="quiz-hint">${qData.hint}</span>` : ''}</div>
                    <div class="quiz-opts">
                        ${qData.options.map((opt, i) => `
                            <div class="quiz-opt">
                                <input type="${inputType}" name="${name}" id="${name}-${i}" value="${opt}">
                                <label for="${name}-${i}">${opt}</label>
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="quiz-nav">
                    <button class="quiz-nav-btn" id="quiz-next">${current === questions.length - 1 ? t.seeScore : t.next} &rarr;</button>
                </div>
            `;
            document.getElementById('quiz-next').addEventListener('click', () => {
                answers[current] = getSelected(name);
                current++;
                renderStep();
            });
        } else {
            let score = 0;
            questions.forEach((q, i) => { if (sameSet(answers[i] || [], q.correct)) score++; });
            body.innerHTML = `
                <div class="quiz-result">
                    <div class="quiz-score">${score} / ${questions.length}</div>
                    <div class="quiz-flavor">${t.flavor[score]}</div>
                    <button class="quiz-replay" id="quiz-replay">${t.replay}</button>
                </div>
            `;
            document.getElementById('quiz-replay').addEventListener('click', () => {
                current = 0;
                answers.length = 0;
                renderStep();
            });
        }
    }

    closeBtn.addEventListener('click', closeQuiz);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeQuiz(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && backdrop.classList.contains('show')) closeQuiz(); });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                openQuiz();
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    observer.observe(footer);
}

/* ─── Ticket Stub ───
   Intercepts the mailto link with a fun "ticket" confirmation before
   handing off to the visitor's email client. */
function initTicket() {
    const backdrop = document.getElementById('ticket-backdrop');
    const closeBtn = document.getElementById('ticket-close');
    const continueLink = document.getElementById('ticket-continue');
    const dateEl = document.getElementById('ticket-date');
    const serialEl = document.getElementById('ticket-serial');
    const emailLink = document.querySelector('.contact-link[href^="mailto:"]');
    if (!backdrop || !emailLink) return;

    emailLink.addEventListener('click', (e) => {
        e.preventDefault();
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString(dateLocale, { day: '2-digit', month: 'short', year: 'numeric' });
        serialEl.textContent = '#' + now.getTime().toString().slice(-6);
        continueLink.href = emailLink.href;
        backdrop.classList.add('show');
        lockScroll();
    });

    function closeTicket() {
        if (!backdrop.classList.contains('show')) return;
        backdrop.classList.remove('show');
        unlockScroll();
    }

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

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = form.querySelector('#name').value;
        const email = form.querySelector('#email').value;
        const message = form.querySelector('#message').value;
        const subject = encodeURIComponent(`Message from ${name}`);
        const body = encodeURIComponent(`From: ${name} (${email})\n\n${message}`);
        continueLink.href = `mailto:me@conorshields.ie?subject=${subject}&body=${body}`;

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
   A fun easter egg: once the visitor scrolls all the way to the bottom
   of the page, a small scrolling credits reel appears below the footer. */
const CREDITS_I18N = {
    en: [
        ['WRITTEN, DIRECTED & DEBUGGED BY', 'Conor Shields'],
        ['FILMED ON LOCATION', 'Cavan, Dublin & London'],
        ['CAFFEINE SUPPLY', "Bewley's & Spite"],
        ['SOUNDTRACK', 'Whatever Autoplayed Next'],
        ['KEY GRIP', 'Someone Had To Hold The Laptop'],
        ['CONTINUITY ERRORS', 'Several, Undetected'],
        ['SPECIAL THANKS', 'Letterboxd, Goodreads & Stack Overflow'],
        ['TRANSLATION CONSULTANT', 'Nuria Lozano'],
        ['CATERING', 'Instant Noodles, As Always'],
        ['NO DEADLINES WERE MET IN THE MAKING OF THIS SITE', ''],
        ['THIS HAS BEEN A CSHIELDS_ PRODUCTION', ''],
        ['THANKS FOR SCROLLING THIS FAR', ''],
    ],
    es: [
        ['ESCRITO, DIRIGIDO Y DEPURADO POR', 'Conor Shields'],
        ['FILMADO EN LOCACIÓN', 'Cavan, Dublín y Londres'],
        ['SUMINISTRO DE CAFEÍNA', 'Bewley\'s y Despecho'],
        ['BANDA SONORA', 'Lo Que Sonara al Azar'],
        ['JEFE DE TRAMOYA', 'Alguien Tenía Que Sostener El Portátil'],
        ['ERRORES DE CONTINUIDAD', 'Varios, Sin Detectar'],
        ['AGRADECIMIENTOS ESPECIALES', 'Letterboxd, Goodreads y Stack Overflow'],
        ['CONSULTORA DE TRADUCCIÓN', 'Nuria Lozano'],
        ['CATERING', 'Fideos Instantáneos, Como Siempre'],
        ['NO SE CUMPLIÓ NINGÚN PLAZO EN LA CREACIÓN DE ESTE SITIO', ''],
        ['ESTA HA SIDO UNA PRODUCCIÓN DE CSHIELDS_', ''],
        ['GRACIAS POR DESPLAZARTE HASTA AQUÍ', ''],
    ],
};

function initCreditsRoll() {
    const panel = document.getElementById('credits-roll');
    const scrollEl = document.getElementById('credits-scroll');
    if (!panel || !scrollEl) return;

    const lines = CREDITS_I18N[LANG];
    const html = lines.map(([role, name]) => `<p>${role}${name ? `<b>${name}</b>` : ''}</p>`).join('');
    scrollEl.innerHTML = html + html;

    let shown = false;
    function checkBottom() {
        if (shown) return;
        const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
        if (atBottom) {
            shown = true;
            panel.classList.add('show');
            window.removeEventListener('scroll', onScroll);
        }
    }
    let ticking = false;
    function onScroll() {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => { checkBottom(); ticking = false; });
    }
    window.addEventListener('scroll', onScroll, { passive: true });
}

/* ─── Films Carousel ───
   Lets visitors browse the full "Recently Screened" selection rather
   than only the first few titles that fit on screen. */
function initFilmsCarousel() {
    const track = document.getElementById('watched-track');
    const prevBtn = document.getElementById('watched-prev');
    const nextBtn = document.getElementById('watched-next');
    if (!track || !prevBtn || !nextBtn) return;

    function scrollByCards(dir) {
        const card = track.querySelector('.film-card');
        if (!card) return;
        const trackStyle = getComputedStyle(track);
        const gap = parseFloat(trackStyle.columnGap || trackStyle.gap || '0');
        const amount = (card.getBoundingClientRect().width + gap) * 3;
        track.scrollBy({ left: dir * amount, behavior: 'smooth' });
    }

    prevBtn.addEventListener('click', () => scrollByCards(-1));
    nextBtn.addEventListener('click', () => scrollByCards(1));

    function updateButtons() {
        const maxScroll = track.scrollWidth - track.clientWidth - 1;
        prevBtn.disabled = track.scrollLeft <= 4;
        nextBtn.disabled = maxScroll <= 0 || track.scrollLeft >= maxScroll - 4;
    }

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

    document.querySelectorAll('#watched-track .film-flip-back').forEach(back => {
        back.addEventListener('click', (e) => {
            if (e.target.closest('a')) return;
            const card = back.closest('.film-card-flippable');
            if (card) card.classList.remove('flipped');
        });
    });
}

/* ─── On Location (Strava Routes) ───
   Routes/locations/photos are synced in by update_strava.py. Clicking
   a route highlights its sketch, updates the location tag and stats,
   and swaps the on-location photo strip in or out. */
function initRoutes() {
    const list = document.getElementById('routes-list');
    if (!list) return;

    const items = list.querySelectorAll('.route-item');
    const paths = document.querySelectorAll('.route-path');
    const markers = document.querySelectorAll('.route-marker');
    const readoutDist = document.getElementById('routes-readout-dist');
    const readoutMeta = document.getElementById('routes-readout-meta');
    const locTag = document.getElementById('routes-loc-tag');
    const photosWrap = document.getElementById('route-photos');
    const photoStrips = photosWrap ? photosWrap.querySelectorAll('.photos-strip') : [];

    items.forEach(item => {
        item.addEventListener('click', () => {
            const idx = item.dataset.route;
            items.forEach(i => i.classList.toggle('active', i === item));
            paths.forEach(p => p.classList.toggle('active', p.dataset.route === idx));
            markers.forEach(m => m.classList.toggle('active', m.dataset.route === idx));
            readoutDist.textContent = item.dataset.dist;
            readoutMeta.textContent = item.dataset.meta;
            locTag.innerHTML = 'Loc. <b>' + item.dataset.loc + '</b>';

            const hasPhotos = parseInt(item.dataset.photos, 10) > 0;
            photosWrap.classList.toggle('show', hasPhotos);
            photoStrips.forEach(strip => {
                strip.hidden = strip.dataset.route !== idx;
            });
        });
    });
}

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
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    function scrollToFrame(i) {
        const clamped = Math.max(0, Math.min(frames.length - 1, i));
        track.scrollTo({
            left: centreOf(frames[clamped]) - track.clientWidth / 2,
            behavior: reducedMotion.matches ? 'auto' : 'smooth'
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
        const dateSpan = document.createElement('span');
        dateSpan.textContent = f.dataset.rDate;

        const titleSpan = document.createElement('span');
        titleSpan.className = 'r-title';
        titleSpan.textContent = f.dataset.rTitle || f.dataset.rKind;

        const subSpan = document.createElement('span');
        subSpan.className = 'r-meta';
        subSpan.textContent = f.dataset.rSub || '';

        const detailSpan = document.createElement('span');
        detailSpan.className = 'r-meta';
        detailSpan.textContent = f.dataset.rDetail || '';

        const countSpan = document.createElement('span');
        countSpan.className = 'r-count';
        countSpan.textContent = frameLabel + ' ' +
            String(best + 1).padStart(2, '0') + ' / ' + frames.length;

        readout.replaceChildren(dateSpan, titleSpan, subSpan, detailSpan, countSpan);

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
        try {
            track.setPointerCapture(e.pointerId);
        } catch (err) {
            /* capture is an optimisation; drag still works without it */
        }
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

    window.addEventListener('pointerup', endDrag);
    window.addEventListener('pointercancel', endDrag);

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
