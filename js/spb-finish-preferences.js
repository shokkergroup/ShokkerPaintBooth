/* Owner 2026-09-15: personal favorites/ratings belong outside the installation. */
(function (global) {
    'use strict';
    const journalKey = 'spb_finish_preferences_pending_v1';
    function read(key, fallback) {
        try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch (_) { return fallback; }
    }
    function write(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* server remains durable */ }
    }
    let pending = read(journalKey, { favorites: {}, ratings: {} });
    let ready = false, running = false, warned = false, timer;
    function endpoint() {
        if (/^https?:$/.test(global.location && global.location.protocol || '') &&
            /^(localhost|127\.0\.0\.1|\[::1\])$/.test(global.location.hostname))
            return global.location.origin + '/api/finish-preferences';
        return (global.ShokkerAPI && global.ShokkerAPI.baseUrl ||
            'http://localhost:' + (global._SHOKKER_PORT || 59876)) + '/api/finish-preferences';
    }
    async function post(body) {
        const response = await fetch(endpoint(), {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body), keepalive: true
        });
        if (!response.ok) throw new Error('Preference save failed (' + response.status + ')');
        return response.json();
    }
    function status(saved) {
        global.dispatchEvent(new CustomEvent('spb-preferences-status', { detail: { saved } }));
        if (!saved && !warned && typeof global.showToast === 'function')
            global.showToast('Favorites and ratings are saved in this browser. App backup will retry.', 'warning');
        warned = !saved;
    }
    function apply(data) {
        const favorites = Object.assign({}, data.favorites, pending.favorites);
        const ratings = Object.assign({}, data.ratings, pending.ratings);
        if (typeof _favoriteFinishes !== 'undefined') {
            _favoriteFinishes.clear();
            Object.keys(favorites).forEach(id => { if (favorites[id]) _favoriteFinishes.add(id); });
        }
        if (typeof _spbFinishRatingsCache !== 'undefined') _spbFinishRatingsCache = ratings;
        write('shokker_favorites', Object.keys(favorites).filter(id => favorites[id]));
        write('spb_finish_ratings_v1', ratings);
        document.querySelectorAll('#swatchPopup .swatch-item[data-finish-id]').forEach(card => {
            const id = card.dataset.finishId, rating = ratings[id] === undefined ? 50 : ratings[id];
            card.dataset.rating = rating;
            const slider = card.querySelector('.swatch-rate-slider');
            const output = card.querySelector('.swatch-rate-val');
            if (slider) slider.value = rating;
            if (output) output.textContent = rating;
            const fav = card.querySelector('.swatch-fav-btn');
            if (fav) {
                fav.classList.toggle('active', !!favorites[id]);
                fav.textContent = favorites[id] ? '★' : '☆';
                fav.title = favorites[id] ? 'Remove from favorites' : 'Add to favorites';
            }
        });
        global.dispatchEvent(new CustomEvent('spb-finish-preferences-restored'));
    }
    async function flush() {
        if (!ready || running) return;
        const batch = JSON.parse(JSON.stringify(pending));
        if (!Object.keys(batch.favorites).length && !Object.keys(batch.ratings).length) return;
        running = true;
        try {
            await post(batch);
            for (const kind of ['favorites', 'ratings']) {
                Object.keys(batch[kind]).forEach(id => {
                    if (pending[kind][id] === batch[kind][id]) delete pending[kind][id];
                });
            }
            write(journalKey, pending);
            status(true);
        } catch (_) { status(false); }
        finally {
            running = false;
            if (Object.keys(pending.favorites).length || Object.keys(pending.ratings).length)
                timer = setTimeout(flush, 5000);
        }
    }
    function queue(kind, id, value) {
        pending[kind][id] = value;
        write(journalKey, pending);
        clearTimeout(timer);
        timer = setTimeout(flush, 250);
    }
    global.SPBFinishPreferences = {
        favorite: (id, value) => queue('favorites', id, !!value),
        rating: (id, value) => queue('ratings', id, value),
        flush
    };
    async function boot() {
        try {
            const favorites = {};
            const legacy = read('shokker_favorites', []);
            if (Array.isArray(legacy)) legacy.forEach(id => {
                if (typeof id === 'string' && id.length > 0 && id.length <= 256) favorites[id] = true;
            });
            const ratings = {};
            Object.entries(read('spb_finish_ratings_v1', {})).forEach(([id, value]) => {
                if (id.length > 0 && id.length <= 256 && typeof value === 'number' && Number.isFinite(value))
                    ratings[id] = Math.max(0, Math.min(100, Math.round(value)));
            });
            const data = await post({ migrate: true, favorites, ratings });
            apply(data);
            ready = true;
            await flush();
        } catch (_) {
            status(false);
            setTimeout(boot, 5000);
        }
    }
    global.addEventListener('pagehide', flush);
    global.addEventListener('online', () => ready ? flush() : boot());
    boot();
})(window);
