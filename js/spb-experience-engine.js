/* ============================================================================
 * SPB EXPERIENCE ENGINE — 2026-07-29 (Claude)
 * Owner ask: twenty 100% unique UI/UX experiences over the SAME app. Every tool
 * still works, nothing removed, but it can look and feel completely different.
 *
 * WHY THIS EXISTS AS AN ENGINE (and not 20 hand-built layouts):
 *   1. SAFETY. The 2026-07-28 look/layout gallery was CSS-only and the owner
 *      scrapped the layouts outright ("I pretty well just hate all of the Bench
 *      Layouts") because moving a rail is not a new experience. Real experiences
 *      need to move real DOM. Moving real DOM by hand, 20 times, is how you break
 *      a 500-button app. So the moves go through ONE audited primitive that can
 *      always put everything back.
 *   2. TOKEN MANDATE (CLAUDE.md architecture addendum). Build the generator
 *      library once; each of the 20 is then a ~50-150 line recipe.
 *
 * THE ONE RULE THAT KEEPS THE TOOLS WORKING:
 *   Packs MOVE existing nodes (appendChild / insertBefore). They never clone,
 *   never innerHTML a control, never rebuild a button. appendChild preserves
 *   every listener, every inline onclick=, every id, and all element state — so
 *   a button that worked in Classic works identically after being moved into a
 *   radial menu, a palette, or a pegboard. Every move is recorded with its
 *   original parent + next-sibling and restored exactly on teardown.
 *
 * GEOMETRY CONTRACT (owner, 2026-07-29):
 *   "The SOURCE and LIVE PREVIEW boxes MUST be at least the same size they are
 *    now... The combined, RED, GREEN, AND BLUE previews can be small. They MUST
 *    also be in the perfect squares because the canvas for the previews in
 *    iRacing is 2048x2048."
 *   Measured baseline: 547x547 @1920x1080, 149x149 @1100x800.
 *   The app sizes both panes via _sizePreviewSquares() as
 *       s = min((rowWidth - 8) / 2, rowHeight)
 *   and in BOTH viewports the binding constraint is HEIGHT. That means every
 *   pixel of vertical chrome a pack reclaims becomes a pixel of SOURCE and a
 *   pixel of LIVE PREVIEW, 1:1. Hence ctx.reclaim() below — the single highest-
 *   leverage primitive in this file.
 * ==========================================================================*/
(function () {
    'use strict';

    if (window.SPBX) return;                       // idempotent — never double-boot

    var LS_KEY = 'shokker_experience';
    var BODY_FLAG = 'spb-xp';

    /* ---------------------------------------------------------------------
     * Small helpers
     * ------------------------------------------------------------------ */
    function q(sel, root) {
        if (!sel) return null;
        if (sel.nodeType === 1) return sel;         // already an element
        // Any OTHER node type (text/comment) is not addressable. Callers
        // naturally pass things like parent.firstChild, which is usually a
        // whitespace text node — returning null beats throwing inside
        // querySelector and taking the whole pack down. That is exactly how
        // 05-pitwall silently failed to apply after the differentiation pass.
        if (sel.nodeType) return null;
        if (typeof sel !== 'string') return null;
        try { return (root || document).querySelector(sel); } catch (_) { return null; }
    }
    function qa(sel, root) {
        if (!sel) return [];
        if (sel.nodeType === 1) return [sel];
        return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    }
    function warn() {
        try { console.warn.apply(console, ['[SPBX]'].concat([].slice.call(arguments))); } catch (_) {}
    }

    /* ---------------------------------------------------------------------
     * ExperienceContext — everything a pack is allowed to do, and every one of
     * those things knows how to undo itself.
     * ------------------------------------------------------------------ */
    function Ctx(pack) {
        this.id = pack.id;
        this.pack = pack;
        this._undo = [];          // LIFO stack of teardown thunks
        this._movedOrigins = new Map();   // node -> {parent, next} (FIRST origin only)
        this._owned = [];         // elements this pack created
    }

    Ctx.prototype.q = function (s, r) { return q(s, r); };
    Ctx.prototype.qa = function (s, r) { return qa(s, r); };

    /** Register an arbitrary teardown thunk. */
    Ctx.prototype.onTeardown = function (fn) {
        if (typeof fn === 'function') this._undo.push(fn);
        return this;
    };

    /**
     * Inject pack-owned CSS. Returns the <style> node.
     * Packs get their rules scoped by body.spb-xp-<id> automatically when they
     * use ctx.css() with a leading '&' shorthand, e.g. '& .left-panel { ... }'.
     */
    Ctx.prototype.css = function (text, name) {
        var scope = 'body.' + BODY_FLAG + '-' + this.id;
        var scoped = String(text).replace(/(^|\})\s*&/g, function (m, br) {
            return (br || '') + '\n' + scope + ' ';
        });
        var st = document.createElement('style');
        st.type = 'text/css';
        st.setAttribute('data-spbx', this.id + (name ? ':' + name : ''));
        st.textContent = scoped;
        document.head.appendChild(st);
        this._undo.push(function () { if (st.parentNode) st.parentNode.removeChild(st); });
        return st;
    };

    /**
     * MOVE a live node into a new parent. THE core primitive.
     * Records the node's ORIGINAL parent + next sibling the first time it is
     * touched, so teardown restores exact document order even after a pack
     * shuffles the same node several times.
     *
     * @param node   element or selector to move
     * @param parent element or selector to move it into
     * @param opts   {before: el|sel}  insert before this child instead of appending
     */
    Ctx.prototype.move = function (node, parent, opts) {
        var el = q(node), to = q(parent);
        if (!el) { warn('move: node not found', node); return null; }
        if (!to) { warn('move: parent not found', parent); return null; }
        if (!this._movedOrigins.has(el)) {
            this._movedOrigins.set(el, { parent: el.parentNode, next: el.nextSibling });
        }
        var before = opts && opts.before ? q(opts.before, to) : null;
        if (before && before.parentNode === to) to.insertBefore(el, before);
        else to.appendChild(el);
        return el;
    };

    /** Move several nodes in order into one parent. */
    Ctx.prototype.moveAll = function (sel, parent, opts) {
        var self = this, out = [];
        qa(sel).forEach(function (el) { out.push(self.move(el, parent, opts)); });
        return out;
    };

    /** Create a pack-owned element (auto-removed on teardown). */
    Ctx.prototype.mk = function (tag, spec) {
        spec = spec || {};
        var el = document.createElement(tag || 'div');
        if (spec.id) el.id = spec.id;
        if (spec.cls) el.className = spec.cls;
        if (spec.html != null) el.innerHTML = spec.html;
        if (spec.text != null) el.textContent = spec.text;
        if (spec.css) el.style.cssText = spec.css;
        if (spec.attrs) Object.keys(spec.attrs).forEach(function (k) { el.setAttribute(k, spec.attrs[k]); });
        el.setAttribute('data-spbx-owned', this.id);
        if (spec.into) {
            var p = q(spec.into);
            if (p) { if (spec.first && p.firstChild) p.insertBefore(el, p.firstChild); else p.appendChild(el); }
        }
        this._owned.push(el);
        this._undo.push(function () { if (el.parentNode) el.parentNode.removeChild(el); });
        return el;
    };

    /** Add a class, remembering to remove it. */
    Ctx.prototype.addClass = function (node, cls) {
        var els = qa(node), added = [];
        els.forEach(function (el) {
            if (!el.classList.contains(cls)) { el.classList.add(cls); added.push(el); }
        });
        this._undo.push(function () { added.forEach(function (el) { el.classList.remove(cls); }); });
        return els;
    };

    /** Set an inline style property, remembering the previous value. */
    Ctx.prototype.style = function (node, prop, value, priority) {
        var els = qa(node), saved = [];
        els.forEach(function (el) {
            saved.push({ el: el, v: el.style.getPropertyValue(prop), p: el.style.getPropertyPriority(prop) });
            el.style.setProperty(prop, value, priority || '');
        });
        this._undo.push(function () {
            saved.forEach(function (s) {
                if (s.v) s.el.style.setProperty(s.p ? prop : prop, s.v, s.p);
                else s.el.style.removeProperty(prop);
            });
        });
        return els;
    };

    /** Set a CSS custom property on :root, restoring the old value. */
    Ctx.prototype.setVar = function (name, value) {
        var root = document.documentElement;
        var prev = root.style.getPropertyValue(name);
        root.style.setProperty(name, value);
        this._undo.push(function () {
            if (prev) root.style.setProperty(name, prev);
            else root.style.removeProperty(name);
        });
        return this;
    };

    /** Add an event listener that is removed on teardown. */
    Ctx.prototype.on = function (target, type, fn, opts) {
        var els = (target === window || target === document) ? [target] : qa(target);
        els.forEach(function (el) { el.addEventListener(type, fn, opts); });
        this._undo.push(function () {
            els.forEach(function (el) { el.removeEventListener(type, fn, opts); });
        });
        return this;
    };

    /**
     * RECLAIM VERTICAL CHROME — the highest-leverage primitive here.
     *
     * Both preview squares are height-limited in every measured viewport, so
     * shrinking the stack above them grows BOTH boxes 1:1. This hides or
     * relocates the named chrome bands and then forces the app's own square
     * math to recompute.
     *
     * Bands (measured 2026-07-29, desktop / min-1100):
     *   .header             62 / 62
     *   #spbTopToolbar      46 / 46
     *   #toolOptionsBar     28 / 28
     *   #previewBottomBar   76 / 76   (RENDER + region actions + zoom pill)
     *   #previewTopStrip    72 / 72   (the 4 channel squares)
     *
     * @param bands array of keys: 'toolbar' | 'toolOptions' | 'bottomBar' |
     *              'topStrip' | 'header' | 'commandBar'
     */
    Ctx.prototype.reclaim = function (bands) {
        var MAP = {
            header: '.header',
            toolbar: '#spbTopToolbar',
            toolOptions: '#toolOptionsBar',
            bottomBar: '#previewBottomBar',
            topStrip: '#previewTopStrip',
            commandBar: '.workbench-command-bar'
        };
        var self = this;
        (bands || []).forEach(function (b) {
            var sel = MAP[b] || b;
            qa(sel).forEach(function (el) { self.addClass(el, 'spbx-reclaimed'); });
        });
        this.refit();
        return this;
    };

    /**
     * FLOAT THE ZONE POPOUT — the highest-value width primitive.
     *
     * paint-booth-v2.html:826 makes an open zone popout reserve a 320px column
     * from .center-panel. Measured, that is the dominant limit on both sacred
     * boxes (49% of the center panel at 1100x800). This keeps the popout and
     * every control inside it, but floats it OVER the canvas instead of
     * carving a column out of the artwork.
     *
     * @param opts {scrim:boolean} also dim the canvas while it is open
     */
    Ctx.prototype.floatPopout = function (opts) {
        opts = opts || {};
        this.addClass(document.body, 'spbx-popout-float');
        if (opts.scrim) {
            var scrim = this.mk('div', { cls: 'spbx-scrim', into: 'body' });
            var pop = q('.zone-editor-float');
            var self = this;
            // Reflect the popout's open state onto <body> so the scrim can fade.
            var sync = function () {
                var open = pop && pop.classList.contains('active') && !pop.classList.contains('collapsed');
                document.body.classList.toggle('spbx-popout-open', !!open);
            };
            if (pop) {
                var mo = new MutationObserver(sync);
                mo.observe(pop, { attributes: true, attributeFilter: ['class'] });
                this.onTeardown(function () {
                    mo.disconnect();
                    document.body.classList.remove('spbx-popout-open');
                });
                sync();
            }
            // Click the scrim to dismiss, using the app's own collapse control
            // so state stays consistent with everything else that reads it.
            this.on(scrim, 'click', function () {
                var closer = q('.zone-editor-float .zone-float-collapse, .zone-editor-float [onclick*="ollapse"]');
                if (closer) closer.click();
                else if (pop) pop.classList.add('collapsed');
                self.refit();
            });
        }
        this.refit();
        return this;
    };

    /**
     * DOCK THE ZONE POPOUT into a host container (usually the right rail).
     *
     * Strictly better than floating it. Floating wins the width back but at
     * 1100x800 a 306px panel then sits on top of a 315px SOURCE box — measured
     * 0% of SOURCE visible. And its open/closed state cannot be reliably held,
     * because collapseZoneDetail() clears both 'active' and 'collapsed' and the
     * next zone render re-adds 'active' — an unwinnable race with app state.
     *
     * Docking sidesteps both problems: the panel keeps every control, occludes
     * nothing, and never fights the app. It is safe specifically because the
     * app addresses the popout by id and rewrites its innerHTML — it never
     * cares where the container lives in the tree.
     *
     * @param host  element or selector to dock into (default: #rightPanel)
     */
    Ctx.prototype.dockPopout = function (host, opts) {
        opts = opts || {};
        var pop = q('#zoneEditorFloat');
        var to = q(host || '#leftPanel');
        if (!pop || !to) { warn('dockPopout: popout or host missing'); return this; }
        this.addClass(document.body, 'spbx-popout-float');   // kill the 320px reservation
        this.addClass(document.body, 'spbx-popout-docked');
        this.move(pop, to);
        // The expand tab is meaningless once docked — but it must not vanish, so
        // it rides along and simply has nothing to expand.
        var tab = q('#zoneFloatExpandTab');
        if (tab) this.move(tab, to);
        if (opts.overlay !== false) this.overlayPopoutOverZones(to);
        this.refit();
        return this;
    };

    /**
     * INSPECTOR OVER THE ZONES RAIL — the panel model the owner asked for.
     *
     * Owner, 2026-07-29: "we should be able to have BOTH of them open with one
     * of them covering up SHOKK ZONES when the other is visible and if you click
     * minimize the Shokk Zone comes back up. It's important to be able to see
     * the actual ZONE POPOUT and LAYERS at the same time... And you have to move
     * between SHOKK ZONES so it really don't need to get buried either."
     *
     * So: the zone inspector OVERLAYS the zones list inside the left rail, and
     * LAYERS keeps the right rail — both are on screen together. A minimize
     * control collapses the inspector to a title strip, revealing SHOKK ZONES
     * underneath so you can move to another zone, then it re-opens.
     *
     * This replaces the LAYERS|ZONE tab model, which was wrong: it made the two
     * mutually exclusive, and the owner needs them simultaneously.
     *
     * Nothing is detached at any point — minimising is a height change on a
     * still-mounted panel, so every control inside stays in the DOM.
     */
    Ctx.prototype.overlayPopoutOverZones = function (host) {
        var rail = q(host || '#leftPanel');
        var pop = q('#zoneEditorFloat');
        if (!rail || !pop || rail.querySelector('.spbx-insp-bar')) return this;

        var self = this;
        this.addClass(rail, 'spbx-zones-host');
        this.addClass(pop, 'spbx-inspector');
        // A 196px zones rail is too narrow to edit a zone in. Flag it so the
        // stylesheet can enforce a usable floor without every pack restating it.
        if (rail.id === 'leftPanel') this.addClass(document.body, 'spbx-insp-left');

        // Title strip with the minimize control, pinned to the top of the panel.
        var bar = this.mk('div', { cls: 'spbx-insp-bar' });
        var title = this.mk('span', { cls: 'spbx-insp-title', text: 'ZONE' });
        var btn = this.mk('button', {
            cls: 'spbx-insp-min', text: '▾',
            attrs: { type: 'button', title: 'Minimize — show SHOKK ZONES',
                     'aria-label': 'Minimize zone inspector' }
        });
        bar.appendChild(title); bar.appendChild(btn);

        // collapseZoneDetail() does `floatPanel.innerHTML = ''` and the panel is
        // re-rendered on every zone change — which silently deleted this header,
        // so the minimize control vanished and SHOKK ZONES could never be
        // revealed. Re-assert it whenever the panel rebuilds itself.
        var reattach = function () {
            if (bar.parentElement !== pop) pop.insertBefore(bar, pop.firstChild);
        };
        reattach();
        var mo = new MutationObserver(reattach);
        mo.observe(pop, { childList: true });
        this.onTeardown(function () {
            try { mo.disconnect(); } catch (_) {}
            if (bar.parentNode) bar.parentNode.removeChild(bar);
        });

        function setMin(min) {
            document.body.classList.toggle('spbx-insp-min-on', !!min);
            btn.textContent = min ? '▴' : '▾';
            btn.title = min ? 'Expand the zone inspector' : 'Minimize — show SHOKK ZONES';
            self.refit();
        }
        this.on(btn, 'click', function (e) { e.stopPropagation(); setMin(!document.body.classList.contains('spbx-insp-min-on')); });

        // Picking a zone means you want to edit it — re-open if minimised.
        this.on(document, 'click', function (e) {
            var card = e.target && e.target.closest ? e.target.closest('#zoneList .zone-card') : null;
            if (card) setTimeout(function () { setMin(false); }, 0);
        }, true);

        this.onTeardown(function () {
            document.body.classList.remove('spbx-insp-min-on');
        });
        return this;
    };

    /**
     * PUT THE TOOL OPTIONS BAR WHERE IT CANNOT BLEED.
     *
     * #toolOptionsBar is nested inside a .workbench-command-bar, not alongside
     * #canvasViewport — so in flow it is not a flex sibling of the artwork and
     * its box bled 3px into the canvas no matter how its margins were tuned.
     * Promoting it to a direct child of #centerPanel immediately above the
     * viewport makes the column allocate it properly, and the overlap is
     * structurally impossible rather than tuned away.
     */
    Ctx.prototype.placeToolOptions = function () {
        var opts = q('#toolOptionsBar');
        var center = q('#centerPanel');
        var viewport = q('#canvasViewport');
        if (!opts || !center || !viewport) return this;
        // 07 Workbench turns #centerPanel into a ROW (pegboard | artwork). Inserting
        // the bar there made it a COLUMN sibling that stole the width — the boxes
        // collapsed to 12px. When the host is a row, wrap [bar, viewport] in their
        // own column so the bar sits ABOVE the artwork, not beside it.
        if (opts.parentElement !== center) {
            var dir = '';
            try { dir = getComputedStyle(center).flexDirection || ''; } catch (_) {}
            if (dir.indexOf('row') === 0) {
                var col = this.mk('div', { cls: 'spbx-opts-col' });
                center.insertBefore(col, viewport);
                col.appendChild(opts);              // owned wrapper; move() not needed
                this.move(viewport, col);
            } else {
                this.move(opts, center, { before: viewport });
            }
        }
        this.addClass(opts, 'spbx-opts-inflow');

        // A fully-expanded brush options bar is 104px tall. Kept permanently in
        // flow that drops the artwork 21% BELOW Classic at 1366x768; clipped, it
        // is the "sections chopped out" the owner reported. So: compact at rest
        // (scrollable, nothing lost) with an explicit expand control that lifts
        // it over the canvas while you use it, costing the layout nothing.
        if (!center.querySelector('.spbx-opts-more')) {
            var self = this;
            var more = this.mk('button', {
                cls: 'spbx-opts-more',
                attrs: { type: 'button', 'aria-expanded': 'false',
                         title: 'Show all options for this tool' }
            });
            more.textContent = 'MORE';
            opts.appendChild(more);
            var sync = function () {
                // Only offer expansion when there is genuinely more to see.
                var hidden = opts.scrollHeight - opts.clientHeight > 4;
                more.style.display = (hidden || document.body.classList.contains('spbx-opts-open')) ? '' : 'none';
            };
            this.on(more, 'click', function (e) {
                e.stopPropagation();
                var open = document.body.classList.toggle('spbx-opts-open');
                more.setAttribute('aria-expanded', open ? 'true' : 'false');
                more.textContent = open ? 'LESS' : 'MORE';
                self.refit();
                setTimeout(sync, 60);
            });
            // The bar rebuilds itself per tool, so re-check after every switch.
            this.on(document, 'click', function (e) {
                if (e.target && e.target.closest && e.target.closest('.vtool-btn')) setTimeout(sync, 120);
            }, true);
            setTimeout(sync, 400);
            this.onTeardown(function () { document.body.classList.remove('spbx-opts-open'); });
        }
        return this;
    };

    /**
     * THE BENCH — the one canonical skeleton every experience is built on.
     *
     * Owner, 2026-07-29: "The Source/Live Preview must be bigger. And we need the
     * Zones, Zone Popout, and Layers to ALWAYS be visible. The Combined, RED,
     * GREEN, BLUE also must be visible at all times but they can be smaller...
     * KEEP the main layout we've been rolling with but other than that it's wide
     * open game to change."
     *
     * WHY ONE SKELETON. Twenty bespoke compositions meant twenty separate fights
     * with s = min((rowWidth-8)/2, rowHeight); every pack had to rediscover the
     * geometry and several lost. The owner's instruction to keep the main layout
     * resolves it: fix the skeleton once, make it optimal, and let the packs vary
     * only in look, feel and interaction. Geometry then holds by construction.
     *
     * ARRANGEMENT (measured against the alternatives before building):
     *     [ ZONES        ]                          [ LAYERS   ]
     *     [ ---------    ]   SOURCE | LIVE PREVIEW  [ FINISHES ]
     *     [ ZONE POPOUT  ]   COMBINED R G B  + RENDER
     * Zones and their editor share the left rail (they are the same subject);
     * layers keep the right. All three are permanently on screen, nothing covers
     * anything, and the four channel previews sit under the artwork where — the
     * boxes being width-limited — they cost nothing.
     *
     * Yields s = 694 desktop / 417 laptop / 284 at 1100x800, against Classic's
     * 547 / 270 / 149.
     */
    Ctx.prototype.bench = function (o) {
        o = o || {};
        var left = q('#leftPanel'), right = q('#rightPanel');
        var pop = q('#zoneEditorFloat');
        var container = q('#splitViewContainer');
        var strip = q('#previewTopStrip');
        var bar = q('#previewBottomBar');
        if (!left || !container) { warn('bench: layout not ready'); return this; }

        // Kill the 320px popout column reservation and free the rail widths.
        this.addClass(document.body, 'spbx-popout-float');
        this.addClass(document.body, 'spbx-popout-docked');
        this.addClass(document.body, 'spbx-rails-free');
        this.addClass(document.body, 'spbx-bench');
        this.setVar('--xp-left', o.left || '290px');
        this.setVar('--xp-right', o.right || '210px');

        // ZONES over ZONE POPOUT in the left rail; both permanently visible.
        if (pop) {
            this.move(pop, left);
            this.addClass(pop, 'spbx-bench-insp');
            var tab = q('#zoneFloatExpandTab');
            if (tab) this.move(tab, left);
        }
        this.addClass(left, 'spbx-bench-left');
        if (right) this.addClass(right, 'spbx-bench-right');

        // Channel squares BELOW the artwork (free: the boxes are width-limited),
        // with the action row sharing that strip so it costs no extra band.
        if (strip) {
            this.move(strip, container);
            this.addClass(strip, 'spbx-bench-strip');
            if (bar) {
                this.move(bar, strip);
                this.addClass(bar, 'spbx-relocated');
            }
        }

        this.refit();
        return { left: left, right: right, inspector: pop, strip: strip, bar: bar };
    };

    /**
     * BASE LAYOUT — the safe skeleton every experience starts from.
     *
     * Encodes the two owner rules and the measured geometry once, so a pack
     * only has to express its own idea:
     *   - "SOURCE OR LIVE PREVIEW [must never be] covered up by any of the
     *      popout panels" (owner, 2026-07-29) -> the zone popout is DOCKED,
     *      never floated over the artwork.
     *   - The squares are width-limited with 126-244px of spare height, so the
     *     four channel previews go BELOW the artwork where they cost nothing.
     *   - #previewBottomBar is id-pinned to 76px; relocating it needs
     *     .spbx-relocated or RENDER spills over the car.
     *
     * @param o {left, right, dockTo, channels:'below'|'above',
     *           bar:'float-bottom'|'strip'|'keep', opts:'float'|'keep'}
     */
    Ctx.prototype.baseLayout = function (o) {
        o = o || {};
        this.dockPopout(o.dockTo || '#rightPanel', { tabs: o.tabs });
        this.addClass(document.body, 'spbx-rails-free');
        if (o.left) this.setVar('--xp-left', o.left);
        if (o.right) this.setVar('--xp-right', o.right);

        var container = q('#splitViewContainer');
        var strip = q('#previewTopStrip');
        var bar = q('#previewBottomBar');

        // Channel squares: below by default (free real estate), above only if asked.
        if (container && strip && (o.channels || 'below') === 'below') {
            this.move(strip, container);
        }

        // The action bar.
        if (bar) {
            if (o.bar === 'strip' && strip) {
                this.move(bar, strip);
                this.addClass(bar, 'spbx-relocated');
            } else if (o.bar !== 'keep') {
                this.addClass(bar, 'spbx-float');
                this.addClass(bar, 'spbx-float-bottom');
            }
        }

        // Tool options stay IN FLOW by default. Floating them saved height and
        // cost correctness three times over (see the retreat note above); a pack
        // must now opt in explicitly with opts:'float'.
        var opts = q('#toolOptionsBar');
        if (opts && o.opts === 'float') {
            this.addClass(opts, 'spbx-float');
            this.addClass(opts, 'spbx-float-top');
        }

        // Remember the rail widths this pack asked for, so surplus width can be
        // added on top without losing the pack's intent (see autoWidth below).
        this._railBase = {
            left: parseInt(o.left, 10) || null,
            right: parseInt(o.right, 10) || null
        };   // nulls are filled in by autoWidth() from the live rails
        this.refit();
        return { container: container, strip: strip, bar: bar, opts: opts };
    };

    /* ------------------------------------------------------------------
     * REJECTED: automatic surplus-width reclamation  (tried 2026-07-29)
     *
     * Once a pack reclaims enough vertical chrome the boxes become HEIGHT-
     * limited, and the leftover width is dead — it renders as empty bands
     * either side of the artwork. Tempting to hand it to the rails, which
     * would also fix name truncation ("Car_Blo...", "Everyth...").
     *
     * Built it, measured it, backed it out. It is NOT safely convergent:
     * widening the rails narrows the centre column, which makes in-flow
     * horizontal bars WRAP to a second line, which costs height — and the
     * boxes are height-limited, so they pay for it. Measured on 02 Command:
     * SOURCE fell 393sq -> 345sq while the right rail grew 276 -> 437. The
     * pack got measurably worse in exchange for one less truncated label
     * (12 -> 11).
     *
     * If this is ever revisited it needs a settle loop that re-measures after
     * every step and abandons any change that reduces s — not a single pass.
     * Do not reintroduce the one-pass version.
     * --------------------------------------------------------------- */

    /**
     * Force the app to re-measure the SOURCE / LIVE PREVIEW squares.
     * _sizePreviewSquares memoises on _lastS, so it must be invalidated first.
     * Called after any layout change; also fires resize so canvas fit recalcs
     * (learned the hard way on the 2026-07-28 layout gallery).
     */
    Ctx.prototype.refit = function () { return SPBX.refit(); };

    /** Run every recorded undo, newest first, then restore moved nodes. */
    Ctx.prototype._teardown = function () {
        for (var i = this._undo.length - 1; i >= 0; i--) {
            try { this._undo[i](); } catch (e) { warn('teardown step failed', e); }
        }
        this._undo.length = 0;
        // Restore moved nodes LAST so any class/style undo above still found them.
        this._movedOrigins.forEach(function (origin, el) {
            try {
                if (!origin.parent) return;
                if (origin.next && origin.next.parentNode === origin.parent) {
                    origin.parent.insertBefore(el, origin.next);
                } else {
                    origin.parent.appendChild(el);
                }
            } catch (e) { warn('restore failed', e); }
        });
        this._movedOrigins.clear();
        this._owned.length = 0;
    };

    /* ---------------------------------------------------------------------
     * SPBX — the registry / switcher
     * ------------------------------------------------------------------ */
    var SPBX = {
        version: '1.0.0',
        packs: [],
        byId: {},
        current: null,
        _ctx: null,
        _ready: false,
        _pending: null,

        /** Register an experience pack. */
        register: function (pack) {
            if (!pack || !pack.id) { warn('register: pack needs an id'); return; }
            if (this.byId[pack.id]) { warn('register: duplicate id', pack.id); return; }
            this.byId[pack.id] = pack;
            this.packs.push(pack);
            this.packs.sort(function (a, b) { return String(a.id).localeCompare(String(b.id)); });
            // If the owner's saved choice arrived before its pack file did, apply now.
            if (this._ready && this._pending === pack.id) { this._pending = null; this.apply(pack.id); }
            return pack;
        },

        list: function () {
            return this.packs.map(function (p) {
                return { id: p.id, name: p.name, tagline: p.tagline, paradigm: p.paradigm };
            });
        },

        /**
         * Force the app's square math to recompute, then nudge canvas fit.
         * Safe to call any time; no-ops if the app hasn't booted its own layout.
         */
        refit: function () {
            try {
                var f = window._sizePreviewSquares;
                if (typeof f === 'function') { f._lastS = -1; f._lastFitW = undefined; f(); }
            } catch (_) {}
            try { window.dispatchEvent(new Event('resize')); } catch (_) {}
            // The app re-fits on timers after boot; mirror that so late reflows settle.
            var self = this;
            [60, 200, 500].forEach(function (t) {
                setTimeout(function () {
                    try {
                        var f = window._sizePreviewSquares;
                        if (typeof f === 'function') { f._lastS = -1; f(); }
                    } catch (_) {}
                }, t);
            });
            return this;
        },

        /** Remove the active experience and put the app back to Classic. */
        clear: function (opts) {
            if (this._ctx) {
                var id = this._ctx.id;
                try {
                    if (this._ctx.pack && typeof this._ctx.pack.teardown === 'function') {
                        this._ctx.pack.teardown(this._ctx);
                    }
                } catch (e) { warn('pack teardown hook failed', e); }
                this._ctx._teardown();
                document.body.classList.remove(BODY_FLAG, BODY_FLAG + '-' + id);
                delete document.body.dataset.xp;
                this._ctx = null;
                this.current = null;
            }
            if (!opts || !opts.silent) {
                try { localStorage.setItem(LS_KEY, 'classic'); } catch (_) {}
            }
            this.refit();
            try { window.dispatchEvent(new CustomEvent('spbx:changed', { detail: { id: 'classic' } })); } catch (_) {}
            return this;
        },

        /** Apply an experience by id. 'classic' clears. */
        apply: function (id) {
            if (!id || id === 'classic') return this.clear();
            var pack = this.byId[id];
            if (!pack) {
                // Pack file may not be loaded yet — remember and apply on register.
                this._pending = id;
                warn('apply: unknown pack (deferred)', id);
                return this;
            }
            this.clear({ silent: true });
            var ctx = new Ctx(pack);
            document.body.classList.add(BODY_FLAG, BODY_FLAG + '-' + id);
            document.body.dataset.xp = id;
            try {
                pack.apply(ctx);
            } catch (e) {
                warn('pack apply FAILED — rolling back', id, e);
                ctx._teardown();
                document.body.classList.remove(BODY_FLAG, BODY_FLAG + '-' + id);
                delete document.body.dataset.xp;
                this.refit();
                return this;
            }
            // Universal, not inside baseLayout(): 01 and 02 lay themselves out
            // and never call it.
            try { ctx.placeToolOptions(); } catch (e) { warn('placeToolOptions failed', e); }
            this._ctx = ctx;
            this.current = id;
            try { localStorage.setItem(LS_KEY, id); } catch (_) {}
            this.refit();
            try { window.dispatchEvent(new CustomEvent('spbx:changed', { detail: { id: id } })); } catch (_) {}
            return this;
        },

        /** Cycle to the next/previous registered experience (owner review aid). */
        cycle: function (dir) {
            var ids = ['classic'].concat(this.packs.map(function (p) { return p.id; }));
            var i = ids.indexOf(this.current || 'classic');
            i = (i + (dir || 1) + ids.length) % ids.length;
            return this.apply(ids[i]);
        },

        /* -----------------------------------------------------------------
         * CONTROL INDEX — shared by the Command palette, Terminal and Ask
         * experiences. Scrapes every interactive control in the live app with
         * a human label, WITHOUT touching it. Consumers activate a control by
         * calling .el.click() on the real node, so behaviour is identical to
         * the owner clicking it himself.
         * -------------------------------------------------------------- */
        indexControls: function () {
            var out = [], seen = new Set();
            var nodes = document.querySelectorAll(
                'button, [role="button"], input[type="checkbox"], input[type="radio"], select, a[onclick]'
            );
            Array.prototype.forEach.call(nodes, function (el) {
                if (seen.has(el)) return;
                seen.add(el);
                var label = (el.getAttribute('aria-label') ||
                             (el.textContent || '').trim() ||
                             el.getAttribute('title') ||
                             el.id || '').replace(/\s+/g, ' ').trim();
                if (!label || label.length > 90) {
                    label = (el.getAttribute('title') || el.id || '').replace(/\s+/g, ' ').trim();
                }
                if (!label) return;
                var hint = (el.getAttribute('title') || '').replace(/\s+/g, ' ').trim();
                // Where does this control live? Gives the palette a group name.
                var group = 'App';
                if (el.closest('#spbTopToolbar')) group = 'Tools';
                else if (el.closest('#leftPanel')) group = 'Zones';
                else if (el.closest('#rightPanel')) group = 'Finishes & Layers';
                else if (el.closest('#settingsDropdown')) group = 'Settings';
                else if (el.closest('.header')) group = 'Header';
                else if (el.closest('#previewBottomBar')) group = 'Render';
                else if (el.closest('#zoneEditorFloat')) group = 'Zone Editor';
                out.push({ el: el, label: label, hint: hint, group: group, id: el.id || '' });
            });
            return out;
        },

        /** True once the app's own boot restructure has produced the squares row. */
        isAppReady: function () {
            return !!(document.getElementById('previewSquaresRow') &&
                      document.getElementById('splitSource') &&
                      document.getElementById('splitPreview'));
        },

        /* =====================================================================
         * LAZY PACK LOADING (2026-08-05 QoL loop unit 5)
         *
         * MEASURED: the 20 experience packs are 3,850 KB — **37% of the app's
         * entire 10.3 MB of JavaScript** — and they were loaded by <script> tag
         * on EVERY boot, for a feature where at most ONE is ever active and the
         * default (Classic) uses none. They were also the 20 slowest individual
         * requests in the boot waterfall.
         *
         * Now: Classic loads zero packs, a saved experience loads exactly one,
         * and the full set arrives only if the painter opens the gallery. The
         * engine already had the mechanism for this — apply() parks an unknown
         * id in _pending and register() applies it the moment the file lands —
         * so this is a loader, not a redesign of the flow.
         * ================================================================== */
        MANIFEST: ['01-studio', '02-command', '03-mixingdesk', '04-darkroom', '05-pitwall', '06-carddeck', '07-workbench', '08-blueprint', '09-stages', '10-freeform', '11-terminal', '12-kiosk', '13-lookbook', '14-headsup', '15-nodegraph', '16-twin', '17-arcade', '18-zen', '19-controlroom', '20-ask'],

        /** Inject one pack's script. Resolves when it registers (or fails). */
        ensurePack: function (id) {
            var self = this;
            return new Promise(function (resolve) {
                if (!id || id === 'classic' || self.byId[id]) return resolve(true);
                if (self.MANIFEST.indexOf(id) < 0) return resolve(false);
                var existing = document.querySelector('script[data-xp-pack="' + id + '"]');
                if (existing) {
                    existing.addEventListener('load', function () { resolve(true); });
                    return;
                }
                var el = document.createElement('script');
                el.src = 'js/experiences/xp-' + id + '.js?v=' + (window.__SPBX_PACK_V || 'lazy1');
                el.async = false;                 // preserve execution order
                el.setAttribute('data-xp-pack', id);
                el.onload = function () { resolve(true); };
                el.onerror = function () { warn('pack failed to load', id); resolve(false); };
                document.head.appendChild(el);
            });
        },

        /** Load every pack — used when the gallery opens so it can list them. */
        ensureAllPacks: function () {
            var self = this;
            return Promise.all(this.MANIFEST.map(function (id) { return self.ensurePack(id); }));
        },

        /** Restore the owner's saved choice once the app has finished booting. */
        boot: function () {
            var self = this;
            var tries = 0;
            (function waitForApp() {
                tries++;
                if (self.isAppReady() || tries > 120) {       // ~30s ceiling, then try anyway
                    self._ready = true;
                    var saved = null;
                    try { saved = localStorage.getItem(LS_KEY); } catch (_) {}
                    if (saved && saved !== 'classic') {
                        // Fetch just this one pack, then apply. apply() also
                        // parks it in _pending, so either ordering lands.
                        self.ensurePack(saved).then(function () { self.apply(saved); });
                    }
                    try { window.dispatchEvent(new CustomEvent('spbx:ready')); } catch (_) {}
                    return;
                }
                setTimeout(waitForApp, 250);
            })();
        }
    };

    /* ---------------------------------------------------------------------
     * Base stylesheet the engine itself needs (packs add their own on top).
     * .spbx-reclaimed is the one rule that makes ctx.reclaim() work; it must
     * beat the app's inline styles and !important pins, hence the specificity.
     * ------------------------------------------------------------------ */
    var base = document.createElement('style');
    base.setAttribute('data-spbx', 'engine-base');
    base.textContent = [
        'body.' + BODY_FLAG + ' .spbx-reclaimed{',
        '  display:none !important;',
        '}',
        /* Packs that reveal chrome on demand mark it .spbx-peek instead. */
        'body.' + BODY_FLAG + ' .spbx-peek{',
        '  position:fixed !important; z-index:9200 !important;',
        '}',
        /* Owned scaffolding never inherits the app`s odd inherited transforms. */
        'body.' + BODY_FLAG + ' [data-spbx-owned]{ box-sizing:border-box; }'
    ].join('\n');
    document.head.appendChild(base);

    window.SPBX = SPBX;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { SPBX.boot(); });
    } else {
        SPBX.boot();
    }
})();
