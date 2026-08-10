const LANG = document.documentElement.lang === 'es' ? 'es' : 'en';

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

    const dateLocale = LANG === 'es' ? 'es-ES' : 'en-GB';

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
