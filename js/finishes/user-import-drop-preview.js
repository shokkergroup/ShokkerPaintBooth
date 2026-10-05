// SHOKK DROP — multi-panel import preview (upload, spec ALL, paint|R/G/B channels).
(function () {
    'use strict';

    var CHANNEL_META = {
        r: { label: 'R · Metallic', hint: 'Left = your upload · Right = M channel (0=dielectric, 255=metallic)', color: '#ff6666' },
        g: { label: 'G · Roughness', hint: 'Left = your upload · Right = R channel (0=mirror, 255=matte)', color: '#66ff66' },
        b: { label: 'B · Clearcoat', hint: 'Left = your upload · Right = CC channel (16=max gloss, 255=dull)', color: '#6688ff' }
    };

    function _cell(src, label, hint, accent) {
        if (!src) return '';
        var cap = hint
            ? '<div class="drop-preview-cap" style="color:' + (accent || 'var(--muted,#9ba8b8)') + '">' + label +
              '<span class="drop-preview-hint">' + hint + '</span></div>'
            : '<div class="drop-preview-cap">' + label + '</div>';
        return '<div class="drop-preview-cell">' +
            '<img src="' + src + '" alt="' + label + '" loading="lazy">' + cap + '</div>';
    }

    function renderShokkDropPreviewPanel(container, data) {
        if (!container) return;
        if (!data || (!data.preview_paint && !data.preview)) {
            container.innerHTML = '';
            return;
        }
        var paint = data.preview_paint || '';
        var spec = data.preview_spec || '';
        var ch = data.preview_channels || {};
        var html = '<div class="drop-preview-grid">';
        html += _cell(paint, data.preview_kind === 'spec_overlay' ? 'Your spec plate' : 'Your upload', data.preview_kind === 'spec_overlay'
            ? 'Normalized 2048² RGB spec overlay (R=M, G=R, B=CC)'
            : 'Normalized 2048² paint plate');
        html += _cell(spec, data.preview_kind === 'spec_overlay' ? 'Spec overlay (ALL)' : 'Import DNA spec (ALL)', 'Blended M · R · CC channels');
        html += '</div>';
        html += '<div class="drop-preview-grid drop-preview-channels">';
        html += _cell(ch.r, CHANNEL_META.r.label, CHANNEL_META.r.hint, CHANNEL_META.r.color);
        html += _cell(ch.g, CHANNEL_META.g.label, CHANNEL_META.g.hint, CHANNEL_META.g.color);
        html += _cell(ch.b, CHANNEL_META.b.label, CHANNEL_META.b.hint, CHANNEL_META.b.color);
        html += '</div>';
        container.innerHTML = html;
    }

    function showShokkDropSavedPreview(finishId) {
        var box = document.getElementById('userImportPreviewBox');
        var meta = document.getElementById('userImportPreviewMeta');
        if (!box || !finishId) return Promise.resolve();
        box.innerHTML = '<p class="hint" style="padding:8px;">Loading preview…</p>';
        return fetch('/api/user-imports/preview-detail/' + encodeURIComponent(finishId))
            .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
            .then(function (res) {
                if (!res.ok) throw new Error((res.body && res.body.error) || 'Preview failed');
                var ts = '?t=' + Date.now();
                var data = res.body;
                renderShokkDropPreviewPanel(box, {
                    preview_paint: data.preview_paint + ts,
                    preview_spec: data.preview_spec + ts,
                    preview_channels: {
                        r: data.preview_channels.r + ts,
                        g: data.preview_channels.g + ts,
                        b: data.preview_channels.b + ts
                    }
                });
                if (meta) {
                    var dna = data.dna || {};
                    meta.textContent = (data.name || finishId) +
                        (dna.style ? (' · DNA: ' + dna.style) : '') +
                        (dna.gauntlet_passed ? ' · gauntlet PASS' : '');
                }
                var actions = document.getElementById('userImportPreviewActions');
                if (actions) actions.style.display = 'none';
            })
            .catch(function (err) {
                if (box) box.innerHTML = '<p class="hint" style="color:#f88;">' + err.message + '</p>';
            });
    }

    window.renderShokkDropPreviewPanel = renderShokkDropPreviewPanel;
    window.showShokkDropSavedPreview = showShokkDropSavedPreview;
})();
