// Guest Designer finishes — merge shipped designer plates into Specials picker.
(function () {
    'use strict';

    function _assignSpecialGroup(groupName, ids) {
        if (!groupName || !ids || !ids.length) return;
        if (typeof SPECIAL_GROUPS !== 'undefined') {
            SPECIAL_GROUPS[groupName] = ids.slice();
        }
        if (typeof MONOLITHIC_GROUPS !== 'undefined') {
            MONOLITHIC_GROUPS[groupName] = ids.slice();
        }
    }

    function _mergeIntoPicker(payload) {
        var entries = (payload && payload.entries) || [];
        var groups = (payload && payload.groups) || {};
        if (!entries.length) return;

        if (typeof MONOLITHICS !== 'undefined') {
            entries.forEach(function (e) {
                if (MONOLITHICS.some(function (m) { return m.id === e.id; })) return;
                MONOLITHICS.push({
                    id: e.id,
                    name: e.name || e.id,
                    desc: e.desc || 'Guest designer finish',
                    swatch: e.swatch || '#4a5568',
                    category: e.group || 'Guest Designer',
                    tags: e.tags || ['guest-designer']
                });
            });
        }

        Object.keys(groups).forEach(function (groupName) {
            _assignSpecialGroup(groupName, groups[groupName] || []);
        });

        if (typeof FINISH_TYPE_BY_ID !== 'undefined') {
            entries.forEach(function (e) { FINISH_TYPE_BY_ID[e.id] = 'monolithic'; });
        }

        if (typeof renderFinishLibrary === 'function') renderFinishLibrary();
    }

    function loadGuestDesigners() {
        return fetch('/api/guest-designers/catalog')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.entries) _mergeIntoPicker(data);
                return data;
            })
            .catch(function (err) {
                console.warn('[guest-designers] catalog load failed:', err);
                return { entries: [] };
            });
    }

    window.loadGuestDesigners = loadGuestDesigners;

    function boot() {
        loadGuestDesigners();
    }
    if (document.visibilityState === 'visible') {
        document.addEventListener('visibilitychange', function () {
            if (document.visibilityState === 'visible') loadGuestDesigners();
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();
})();
