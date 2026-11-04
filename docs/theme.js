// Loaded render-blocking from <head> so a saved theme applies before first
// paint; the switcher UI is built once the DOM is ready.
(function () {
    var STORAGE_KEY = 'site-theme';
    var FONT_CSS = 'https://fonts.googleapis.com/css2?display=swap&family=';

    var THEMES = [
        { id: 'house', year: null, en: 'House Print', es: 'Copia de la casa' },
        { id: 'la-haine', year: 1995, en: 'La Haine', es: 'El odio', font: 'Anton' },
        { id: 'barry-lyndon', year: 1975, en: 'Barry Lyndon', es: 'Barry Lyndon', font: 'Cormorant+Garamond:wght@700' },
        { id: 'autumn-sonata', year: 1978, en: 'Autumn Sonata', es: 'Sonata de otoño', font: 'Libre+Caslon+Display' },
        { id: 'handmaiden', year: 2016, en: 'The Handmaiden', es: 'La doncella', font: 'Shippori+Mincho:wght@800' },
        { id: 'goodfellas', year: 1990, en: 'Goodfellas', es: 'Uno de los nuestros', font: 'Abril+Fatface' },
        { id: 'taxi-driver', year: 1976, en: 'Taxi Driver', es: 'Taxi Driver', font: 'Bebas+Neue' },
        { id: 'apocalypse-now', year: 1979, en: 'Apocalypse Now', es: 'Apocalypse Now', font: 'Oswald:wght@700' },
        { id: 'koyaanisqatsi', year: 1982, en: 'Koyaanisqatsi', es: 'Koyaanisqatsi', font: 'Syne:wght@800' },
        { id: 'in-bruges', year: 2008, en: 'In Bruges', es: 'Escondidos en Brujas', font: 'Cinzel:wght@700' },
        { id: 'in-the-mood-for-love', year: 2000, en: 'In the Mood for Love', es: 'Deseando amar', font: 'Bodoni+Moda:wght@800' }
    ];

    function find(id) {
        for (var i = 0; i < THEMES.length; i++) {
            if (THEMES[i].id === id) return THEMES[i];
        }
        return THEMES[0];
    }

    function loadFont(theme) {
        if (!theme.font) return;
        var linkId = 'theme-font-' + theme.id;
        if (document.getElementById(linkId)) return;
        var link = document.createElement('link');
        link.id = linkId;
        link.rel = 'stylesheet';
        link.href = FONT_CSS + theme.font;
        document.head.appendChild(link);
    }

    function apply(id) {
        var theme = find(id);
        if (theme.id === 'house') {
            document.documentElement.removeAttribute('data-theme');
        } else {
            document.documentElement.setAttribute('data-theme', theme.id);
        }
        loadFont(theme);
        return theme;
    }

    function set(id) {
        var theme = apply(id);
        try {
            if (theme.id === 'house') localStorage.removeItem(STORAGE_KEY);
            else localStorage.setItem(STORAGE_KEY, theme.id);
        } catch (e) { /* storage blocked: theme lasts for this page view */ }
        return theme;
    }

    var saved = null;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { /* see above */ }
    apply(saved);

    window.SiteTheme = {
        themes: THEMES,
        current: function () {
            return document.documentElement.getAttribute('data-theme') || 'house';
        },
        set: set
    };
})();

const THEME_I18N = {
    en: { toggle: 'Theme', title: 'Now screening', label: 'Choose a film theme' },
    es: { toggle: 'Tema', title: 'En pantalla', label: 'Elige un tema de película' },
};

function initThemeSwitcher() {
    const site = window.SiteTheme;
    const LANG = document.documentElement.lang === 'es' ? 'es' : 'en';
    const t = THEME_I18N[LANG];

    const swatch = (cls, themeId) => {
        const el = document.createElement('span');
        el.className = cls;
        el.setAttribute('aria-hidden', 'true');
        if (themeId) el.dataset.theme = themeId;
        el.innerHTML = '<i></i><i></i><i></i>';
        return el;
    };

    const panel = document.createElement('div');
    panel.className = 'theme-panel';
    panel.id = 'theme-panel';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', t.label);

    const title = document.createElement('p');
    title.className = 'theme-panel-title';
    title.textContent = t.title;
    panel.appendChild(title);

    const options = site.themes.map(theme => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'theme-option';
        btn.dataset.themeId = theme.id;
        btn.appendChild(swatch('theme-swatch', theme.id));
        const name = document.createElement('span');
        name.className = 'theme-option-name';
        name.textContent = theme[LANG];
        btn.appendChild(name);
        if (theme.year) {
            const year = document.createElement('span');
            year.className = 'theme-option-year';
            year.textContent = theme.year;
            btn.appendChild(year);
        }
        panel.appendChild(btn);
        return btn;
    });
    document.body.appendChild(panel);

    const toggles = [];
    // Home pages put the toggle beside the language switch; pages without one
    // (the blog) mark where it goes with data-theme-slot.
    [['#lang-toggle', 'lang-toggle theme-toggle'],
     ['#lang-toggle-mobile', 'lang-toggle lang-toggle-mobile theme-toggle'],
     ['[data-theme-slot]', 'lang-toggle theme-toggle']].forEach(([selector, cls]) => {
        const anchor = document.querySelector(selector);
        if (!anchor) return;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = cls;
        btn.setAttribute('aria-haspopup', 'dialog');
        btn.setAttribute('aria-controls', panel.id);
        btn.setAttribute('aria-expanded', 'false');
        btn.appendChild(swatch('theme-toggle-dots'));
        btn.appendChild(document.createTextNode(t.toggle));
        anchor.parentNode.insertBefore(btn, anchor);
        toggles.push(btn);
    });

    let opener = null;

    const sync = () => {
        const current = site.current();
        options.forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.themeId === current)));
    };

    const open = (btn) => {
        opener = btn;
        sync();
        panel.hidden = false;
        toggles.forEach(b => b.setAttribute('aria-expanded', 'true'));
        (options.find(o => o.getAttribute('aria-pressed') === 'true') || options[0]).focus();
    };

    const close = (restoreFocus) => {
        if (panel.hidden) return;
        panel.hidden = true;
        toggles.forEach(b => b.setAttribute('aria-expanded', 'false'));
        if (restoreFocus && opener && opener.offsetParent !== null) opener.focus();
    };

    toggles.forEach(btn => btn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (panel.hidden) open(btn); else close(true);
    }));

    // Stays open after a pick so visitors can flick through prints.
    options.forEach(btn => btn.addEventListener('click', () => {
        site.set(btn.dataset.themeId);
        sync();
    }));

    document.addEventListener('click', (e) => {
        if (!panel.hidden && !panel.contains(e.target)) close(false);
    });

    document.addEventListener('keydown', (e) => {
        if (panel.hidden) return;
        if (e.key === 'Escape') {
            close(true);
            return;
        }
        if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && panel.contains(document.activeElement)) {
            e.preventDefault();
            const i = options.indexOf(document.activeElement);
            const step = e.key === 'ArrowDown' ? 1 : -1;
            options[(i + step + options.length) % options.length].focus();
        }
    });
}

document.addEventListener('DOMContentLoaded', initThemeSwitcher);
