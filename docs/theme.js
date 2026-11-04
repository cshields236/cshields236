// Loaded render-blocking from <head> so a saved theme applies before first
// paint; main.js builds the switcher from window.SiteTheme.
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
