/* ============================================================================
 * EXPERIENCE 06 — CARD DECK
 * Paradigm: BROWSE-BY-SWIPE. Finishes are a deck you flick through, not a list.
 *
 * The catalog is ~2,600 finishes. A scrolling list of tiny swatches is the worst
 * possible way to meet them — you cannot judge a finish at 40px. Card Deck gives
 * one finish the whole card: big, named, and you move with Left/Right arrows or
 * the on-card buttons. Pressing Enter (or "Use this") clicks the REAL swatch in
 * the app, so choosing from the deck is identical to choosing from the picker.
 *
 * The deck is an overlay, but it opens ON DEMAND and never sits over the artwork
 * at rest — owner rule: SOURCE and LIVE PREVIEW are never covered.
 * ==========================================================================*/
(function () {
    'use strict';
    if (!window.SPBX) return;

    SPBX.register({
        id: '06-carddeck',
        name: 'Card Deck',
        tagline: 'Meet 2,600 finishes one big card at a time.',
        paradigm: 'Browse-by-swipe deck',

        apply: function (ctx) {
            // ONE canonical skeleton (Ctx.bench): ZONES + ZONE POPOUT left, LAYERS
            // right, channel previews under the artwork — all permanently visible.
            // Owner 2026-07-29: keep the main layout; vary look and feel only.
            ctx.bench();
// The right rail becomes a horizontal card rail below, which is no
            // place for a tall zone inspector — dock it into the left rail instead.

            // A deck lives on the table in front of you, not in a filing cabinet
            // at the side. The finishes/layers rail moves to a horizontal card
            // rail under the artwork, so browsing is the resting state of this
            // experience rather than something hidden behind a modal.
            // Layers stay in their rail (owner: always visible). The deck itself
            // — the big card browser — is this pack's identity and is an overlay
            // opened on demand, so it costs the artwork nothing.

            /* ---- the deck overlay ---- */
            var deck = ctx.mk('div', { cls: 'xp-deck', into: 'body' });
            var stage = ctx.mk('div', { cls: 'xp-deck-stage' });
            var card = ctx.mk('div', { cls: 'xp-deck-card' });
            var art = ctx.mk('div', { cls: 'xp-deck-art' });
            var name = ctx.mk('div', { cls: 'xp-deck-name' });
            var meta = ctx.mk('div', { cls: 'xp-deck-meta' });
            var acts = ctx.mk('div', { cls: 'xp-deck-acts' });
            card.appendChild(art); card.appendChild(name); card.appendChild(meta); card.appendChild(acts);
            var prev = ctx.mk('button', { cls: 'xp-deck-nav prev', text: '‹', attrs: { type: 'button', 'aria-label': 'Previous finish' } });
            var next = ctx.mk('button', { cls: 'xp-deck-nav next', text: '›', attrs: { type: 'button', 'aria-label': 'Next finish' } });
            stage.appendChild(prev); stage.appendChild(card); stage.appendChild(next);
            deck.appendChild(stage);
            var counter = ctx.mk('div', { cls: 'xp-deck-count' });
            deck.appendChild(counter);

            var use = ctx.mk('button', { cls: 'xp-deck-use', text: 'Use this finish', attrs: { type: 'button' } });
            var closeB = ctx.mk('button', { cls: 'xp-deck-close', text: 'Close', attrs: { type: 'button' } });
            acts.appendChild(use); acts.appendChild(closeB);

            var items = [], i = 0;

            function collect() {
                // Whatever swatch/finish rows the app currently shows — scraped
                // live so the deck always reflects the real, filtered catalog.
                var sel = '.finish-item, .swatch-item, .spec-pattern-cell, [data-finish-id], .pattern-cell';
                items = Array.prototype.slice.call(document.querySelectorAll(sel))
                    .filter(function (el) { return el.offsetParent !== null || el.closest('#swatchPopup'); });
                return items.length;
            }

            function show() {
                if (!items.length) {
                    name.textContent = 'Open a finish picker first';
                    meta.textContent = 'Pick a zone, then Base or Pattern — the deck reads whatever the app is showing.';
                    art.style.backgroundImage = '';
                    counter.textContent = '';
                    return;
                }
                i = (i + items.length) % items.length;
                var el = items[i];
                var img = el.querySelector('img, canvas');
                var bg = '';
                if (img) {
                    if (img.tagName === 'IMG') bg = img.currentSrc || img.src;
                    else { try { bg = img.toDataURL(); } catch (_) { bg = ''; } }
                }
                if (!bg) {
                    var cs = getComputedStyle(el);
                    art.style.background = cs.backgroundImage !== 'none' ? cs.backgroundImage : cs.backgroundColor;
                    art.style.backgroundSize = 'cover';
                } else {
                    art.style.background = '#0a0c12 url(' + bg + ') center/cover no-repeat';
                }
                var label = (el.getAttribute('data-name') || el.getAttribute('title') ||
                             el.textContent || '').replace(/\s+/g, ' ').trim();
                name.textContent = label.slice(0, 60) || 'Finish ' + (i + 1);
                meta.textContent = (el.getAttribute('data-category') || el.className.split(' ')[0] || '').toUpperCase();
                counter.textContent = (i + 1) + ' / ' + items.length + '   —   ← → to browse, Enter to use';
                card.classList.remove('in'); void card.offsetWidth; card.classList.add('in');
            }

            function open() { collect(); deck.classList.add('on'); show(); }
            function close() { deck.classList.remove('on'); }
            function apply() {
                var el = items[i];
                close();
                if (el) { try { el.scrollIntoView({ block: 'nearest' }); el.click(); } catch (_) {} }
            }

            ctx.on(prev, 'click', function () { i--; show(); });
            ctx.on(next, 'click', function () { i++; show(); });
            ctx.on(use, 'click', apply);
            ctx.on(closeB, 'click', close);
            ctx.on(deck, 'click', function (e) { if (e.target === deck) close(); });
            ctx.on(document, 'keydown', function (e) {
                if (!deck.classList.contains('on')) {
                    if (e.key === 'd' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); open(); }
                    return;
                }
                if (e.key === 'ArrowLeft') { e.preventDefault(); i--; show(); }
                else if (e.key === 'ArrowRight') { e.preventDefault(); i++; show(); }
                else if (e.key === 'Enter') { e.preventDefault(); apply(); }
                else if (e.key === 'Escape') { e.preventDefault(); close(); }
            }, true);

            var trigger = ctx.mk('button', {
                cls: 'xp-deck-trigger', into: '#centerPanel',
                text: '🂠  Browse finishes as cards',
                attrs: { type: 'button', 'aria-label': 'Open finish card deck' }
            });
            ctx.on(trigger, 'click', open);
            ctx.onTeardown(function () { deck.classList.remove('on'); });

            ctx.css([
                '&{ --xp-ch:52px; --xp-radius:18px; --dk-a:#ff5c8a; }',
                '& #splitViewContainer{ padding:10px !important; gap:10px; }',
                '& .main-container, & #centerPanel{ background:#0d0b12 !important; }',
                '& .left-panel{ background:#120f19 !important; border-color:#241d33 !important; }',
                '& #rightPanel.xp-deck-rail{',
                '  width:100% !important; min-width:0 !important; max-width:none !important;',
                '  flex:0 0 auto !important; height:auto !important; max-height:132px !important;',
                '  border-left:none !important; border-top:1px solid #241d33 !important;',
                '  background:#120f19 !important; overflow-y:auto !important; }',
                '& #rightPanel.xp-deck-rail .layer-row{ display:inline-flex !important;',
                '  min-width:170px !important; margin:3px !important; }',
                '& .header{ background:#120f19 !important; border-bottom:1px solid #241d33 !important; }',
                '& #spbTopToolbar{ background:#0f0d16 !important; border-bottom:1px solid #241d33 !important; }',
                '& #splitSource, & #splitPreview{ background:#07060b !important;',
                '  border:1px solid #2b2340 !important; border-radius:18px !important;',
                '  box-shadow:0 20px 50px rgba(0,0,0,0.6) !important; }',

                /* everything rounds and softens — this is a browsing experience */
                '& .zone-card, & .layer-row, & .btn, & .vtool-btn{ border-radius:12px !important; }',
                '& .vtool-btn{ animation:none !important; }',
                '& .vtool-btn.active{ background:rgba(255,92,138,0.18) !important;',
                '  border-color:var(--dk-a) !important; color:var(--dk-a) !important;',
                '  box-shadow:none !important; animation:none !important; }',

                '& .xp-deck-trigger{',
                '  position:absolute; top:8px; right:14px; z-index:70;',
                '  padding:7px 15px; border-radius:999px; cursor:pointer;',
                '  background:linear-gradient(135deg,#ff5c8a,#a855f7); color:#fff;',
                '  border:none; font-size:12px; font-weight:700;',
                '  box-shadow:0 6px 20px rgba(168,85,247,0.4); }',

                '& .xp-deck{ position:fixed; inset:0; z-index:9500; display:none;',
                '  flex-direction:column; align-items:center; justify-content:center; gap:14px;',
                '  background:rgba(8,6,14,0.93); backdrop-filter:blur(10px); }',
                '& .xp-deck.on{ display:flex; }',
                '& .xp-deck-stage{ display:flex; align-items:center; gap:22px; }',
                '& .xp-deck-card{ width:min(420px,74vw); background:#15111f;',
                '  border:1px solid #35294f; border-radius:22px; overflow:hidden;',
                '  box-shadow:0 40px 100px rgba(0,0,0,0.75); }',
                '& .xp-deck-card.in{ animation:xpDeckIn .22s cubic-bezier(.2,.8,.2,1); }',
                '@keyframes xpDeckIn{ from{ transform:scale(.94) translateY(10px); opacity:0 } to{ transform:none; opacity:1 } }',
                '& .xp-deck-art{ height:min(320px,42vh); background:#0a0810 center/cover no-repeat; }',
                '& .xp-deck-name{ padding:14px 18px 2px; font-size:19px; font-weight:800; color:#fff; }',
                '& .xp-deck-meta{ padding:0 18px 12px; font-size:10px; letter-spacing:1.4px; color:#9d8fbe; }',
                '& .xp-deck-acts{ display:flex; gap:8px; padding:0 18px 18px; }',
                '& .xp-deck-use{ flex:1 1 auto; padding:11px; border:none; border-radius:12px; cursor:pointer;',
                '  background:linear-gradient(135deg,#ff5c8a,#a855f7); color:#fff; font-weight:800; font-size:13px; }',
                '& .xp-deck-close{ padding:11px 16px; border-radius:12px; cursor:pointer;',
                '  background:transparent; color:#9d8fbe; border:1px solid #35294f; font-size:12px; }',
                '& .xp-deck-nav{ width:52px; height:52px; border-radius:50%; cursor:pointer;',
                '  background:#1b1528; color:#fff; border:1px solid #35294f; font-size:26px; line-height:1; }',
                '& .xp-deck-nav:hover{ background:#251c38; border-color:var(--dk-a); }',
                '& .xp-deck-count{ font-size:11px; color:#7d6f9e; letter-spacing:0.8px; }',
                '& .preview-living-frame, & .preview-frame-ekg, & .preview-breathing-aura{ display:none !important; }'
            ].join('\n'));

            ctx.refit();
        }
    });
})();
