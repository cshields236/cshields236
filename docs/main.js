document.addEventListener('DOMContentLoaded', () => {
    const nav = document.getElementById('nav');
    const toggle = document.querySelector('.nav-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const reveals = document.querySelectorAll('.reveal');

    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 50);
    });

    toggle.addEventListener('click', () => {
        mobileMenu.classList.toggle('open');
        document.body.style.overflow = mobileMenu.classList.contains('open') ? 'hidden' : '';
    });

    mobileMenu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => {
            mobileMenu.classList.remove('open');
            document.body.style.overflow = '';
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
});

/* ─── Pop Quiz ───
   Answers are read live from the page's own content (hero location,
   favourite films, book authors) so the quiz never drifts out of sync
   with the Letterboxd/Goodreads auto-updates. */
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

function buildQuizQuestions() {
    const PLACE_DECOYS = ['Dublin, Ireland', 'Cork, Ireland', 'Belfast', 'Galway, Ireland', 'Manchester, UK', 'Edinburgh, UK'];
    const FILM_DECOYS = ['Titanic (1997)', 'Frozen (2013)', 'The Avengers (2012)', 'Jurassic Park (1993)', 'Fast & Furious 9 (2021)'];
    const AUTHOR_DECOYS = ['George Orwell', 'Virginia Woolf', 'James Joyce'];
    const TITLE_DECOYS = ['1984', 'The Great Gatsby', 'Pride and Prejudice', 'Brave New World'];

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
        q: 'Where was Conor born?',
        type: 'single',
        options: shuffle([birthplace, ...PLACE_DECOYS.filter(p => p !== birthplace && p !== city).slice(0, 3)]),
        correct: [birthplace],
    });

    if (favTitles.length >= 2) {
        const correctFilms = shuffle(favTitles).slice(0, 2);
        const decoys = FILM_DECOYS.filter(f => !favTitles.includes(f)).slice(0, 3);
        questions.push({
            q: 'Which two of these are among his all-time favourite films?',
            hint: '(pick 2)',
            type: 'multi',
            options: shuffle([...correctFilms, ...decoys]),
            correct: correctFilms,
        });
    }

    questions.push({
        q: 'Where does he live now?',
        type: 'single',
        options: shuffle([city, ...PLACE_DECOYS.filter(p => p !== birthplace && p !== city).slice(0, 3)]),
        correct: [city],
    });

    if (repeatedAuthor) {
        const decoyAuthors = singleAuthors.length >= 3 ? singleAuthors.slice(0, 3) : [...singleAuthors, ...AUTHOR_DECOYS].slice(0, 3);
        questions.push({
            q: 'Which author shows up twice on his reading list?',
            type: 'single',
            options: shuffle([repeatedAuthor, ...decoyAuthors]),
            correct: [repeatedAuthor],
        });
    } else if (bookTitles.length) {
        const realTitle = shuffle(bookTitles)[0];
        const decoyTitles = TITLE_DECOYS.filter(t => !bookTitles.includes(t)).slice(0, 3);
        questions.push({
            q: 'Which of these is currently on his reading list?',
            type: 'single',
            options: shuffle([realTitle, ...decoyTitles]),
            correct: [realTitle],
        });
    }

    return questions;
}

const QUIZ_FLAVOR = {
    0: 'Might want to scroll back up.',
    1: 'Might want to scroll back up.',
    2: 'Half marks — skim reader.',
    3: 'Solid. You were paying attention.',
    4: 'Perfect. Did you screenshot my Letterboxd?',
};

function initQuiz() {
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
        document.body.style.overflow = 'hidden';
    }

    function closeQuiz() {
        backdrop.classList.remove('show');
        document.body.style.overflow = '';
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
                    <button class="quiz-nav-btn" id="quiz-next">${current === questions.length - 1 ? 'See Score' : 'Next'} &rarr;</button>
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
                    <div class="quiz-flavor">${QUIZ_FLAVOR[score]}</div>
                    <button class="quiz-replay" id="quiz-replay">Watch It Again</button>
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
