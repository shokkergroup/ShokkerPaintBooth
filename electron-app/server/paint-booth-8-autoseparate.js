/* ============================================================================
 * Auto-Separate (main Paint Booth) — 2026-06-26
 * Brings Spec Sculpt's flat-TGA decal detection into the main app: when a FLAT
 * livery (TGA/PNG/JPEG) is loaded, an "Auto-Separate" button opens a modal that
 * splits the paint into NUMBERS / SPONSORS / PAINT via /api/auto-separate-livery,
 * with tolerance sliders. PURELY ADDITIVE + fully self-contained: it injects its
 * own button + modal and never modifies existing functions, so it cannot break
 * the rest of the app (the whole module is guarded). The deeper "make these into
 * editable zones" step is intentionally separate — this is the preview/tune pass.
 * ========================================================================== */
(function () {
  'use strict';
  if (window.__autoSepInstalled) return;
  window.__autoSepInstalled = true;

  function $(id) { return document.getElementById(id); }

  function injectButton() {
    try {
      var panel = $('paintPreviewLoaded');
      if (!panel || $('btnAutoSepMain')) return;
      var btn = document.createElement('button');
      btn.id = 'btnAutoSepMain';
      btn.type = 'button';
      btn.className = 'btn btn-sm';
      btn.textContent = '🪓 Auto-Separate';
      btn.title = 'Split this FLAT livery into Numbers / Sponsor logos / Paint (best-effort, no PSD needed). Tune with the sliders.';
      btn.style.cssText = 'cursor:pointer;font-size:11px;padding:4px 10px;white-space:nowrap;';
      btn.addEventListener('click', openModal);
      var row = panel.querySelector('div');
      (row || panel).appendChild(btn);
    } catch (e) { /* never break the app */ }
  }

  function buildModal() {
    if ($('autoSepModal')) return $('autoSepModal');
    var m = document.createElement('div');
    m.id = 'autoSepModal';
    m.style.cssText = 'position:fixed;inset:0;z-index:99999;display:none;background:rgba(2,4,8,0.78);' +
      'backdrop-filter:blur(3px);align-items:center;justify-content:center;';
    m.innerHTML =
      '<div style="background:#0e1016;border:1px solid #2a2f3a;border-radius:14px;max-width:920px;width:94%;' +
      'max-height:92vh;overflow:auto;padding:18px 20px;box-shadow:0 24px 70px rgba(0,0,0,.7);color:#e8eaf0;font-family:Segoe UI,Arial,sans-serif;">' +
      '<div style="display:flex;align-items:center;gap:10px;">' +
      '<h2 style="margin:0;font-size:17px;">🪓 Auto-Separate — Numbers · Sponsors · Paint</h2>' +
      '<span id="autoSepMsg" style="margin-left:auto;font-size:12px;color:#9aa3b2;"></span>' +
      '<button id="autoSepClose" style="background:#1b2030;border:1px solid #2a2f3a;color:#cfd5e3;border-radius:8px;padding:5px 11px;cursor:pointer;">Close</button></div>' +
      '<p style="font-size:12px;color:#9aa3b2;margin:8px 0 12px;">Best-effort split of a <b>flat</b> livery — the car <span style="color:#ff8a8a;">NUMBERS</span>, the ' +
      '<span style="color:#8ab8ff;">SPONSOR</span> logos/wordmarks, and the <span style="color:#9affb0;">BASE PAINT</span>. Tune the tolerance, then Separate.</p>' +
      '<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">' +
      '<button id="autoSepRun" style="background:linear-gradient(135deg,#7c8bff,#b478ff);border:none;color:#fff;border-radius:9px;padding:9px 18px;font-weight:700;cursor:pointer;">🪓 Separate</button>' +
      '<label style="font-size:12px;color:#cfd5e3;display:flex;align-items:center;gap:6px;cursor:pointer;"><input type="checkbox" id="autoSepLiveM"> live</label>' +
      '<span style="font-size:11px;color:#9aa3b2;">Sensitivity</span><input type="range" id="autoSepSens" min="30" max="200" value="100" style="width:120px;">' +
      '<span id="autoSepSensV" style="font-size:11px;color:#9aa3b2;width:34px;">1.0×</span>' +
      '<span style="font-size:11px;color:#9aa3b2;">Number size</span><input type="range" id="autoSepNum" min="40" max="250" value="100" style="width:120px;">' +
      '<span id="autoSepNumV" style="font-size:11px;color:#9aa3b2;width:34px;">1.0×</span></div>' +
      '<div id="autoSepFrac" style="font-size:12px;margin:2px 0 8px;color:#9aa3b2;"></div>' +
      '<img id="autoSepOverlay" alt="" style="display:none;width:100%;max-width:560px;border-radius:10px;border:1px solid #2a2f3a;">' +
      '<div id="autoSepMasksM" style="display:none;gap:10px;margin-top:10px;flex-wrap:wrap;">' +
      '<div style="text-align:center;"><div style="font-size:11px;color:#ff8a8a;margin-bottom:3px;">Numbers</div><img id="autoSepMN" style="width:150px;border-radius:7px;border:1px solid #2a2f3a;background:#05070a;"></div>' +
      '<div style="text-align:center;"><div style="font-size:11px;color:#8ab8ff;margin-bottom:3px;">Sponsors</div><img id="autoSepMS" style="width:150px;border-radius:7px;border:1px solid #2a2f3a;background:#05070a;"></div>' +
      '<div style="text-align:center;"><div style="font-size:11px;color:#9affb0;margin-bottom:3px;">Paint</div><img id="autoSepMP" style="width:150px;border-radius:7px;border:1px solid #2a2f3a;background:#05070a;"></div></div>' +
      '<p style="font-size:11px;color:#6b7385;margin:12px 0 0;">Tip: raise <b>Sensitivity</b> to catch more, lower it to keep only the clearest decals. Raise <b>Number size</b> if sponsor text is being tagged as a number.</p>' +
      '</div>';
    document.body.appendChild(m);
    m.addEventListener('click', function (e) { if (e.target === m) hideModal(); });
    $('autoSepClose').addEventListener('click', hideModal);
    $('autoSepRun').addEventListener('click', runSeparate);
    var lt = null;
    function sliders() {
      $('autoSepSensV').textContent = ((parseInt($('autoSepSens').value, 10) || 100) / 100).toFixed(1) + '×';
      $('autoSepNumV').textContent = ((parseInt($('autoSepNum').value, 10) || 100) / 100).toFixed(1) + '×';
      if ($('autoSepLiveM').checked) { clearTimeout(lt); lt = setTimeout(runSeparate, 400); }
    }
    $('autoSepSens').addEventListener('input', sliders);
    $('autoSepNum').addEventListener('input', sliders);
    return m;
  }

  function hideModal() { var m = $('autoSepModal'); if (m) m.style.display = 'none'; }
  function openModal() { buildModal().style.display = 'flex'; }

  function _canvasBlob() {
    return new Promise(function (resolve, reject) {
      var c = $('paintCanvas');
      if (!c || !c.width) { reject(new Error('Load a paint first')); return; }
      try { c.toBlob(function (b) { b ? resolve(b) : reject(new Error('canvas read failed')); }, 'image/png'); }
      catch (e) { reject(e); }
    });
  }

  function runSeparate() {
    var msg = $('autoSepMsg'); if (msg) msg.textContent = 'Separating…';
    var sens = (parseInt($('autoSepSens').value, 10) || 100) / 100;
    var nsz = (parseInt($('autoSepNum').value, 10) || 100) / 100;
    _canvasBlob().then(function (blob) {
      var fd = new FormData();
      fd.append('image', blob, 'livery.png');
      fd.append('sensitivity', String(sens));
      fd.append('number_size', String(nsz));
      return fetch('/api/auto-separate-livery', { method: 'POST', body: fd });
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (!j || !j.success) throw new Error((j && j.error) || 'separate failed');
      var ov = $('autoSepOverlay'); if (ov && j.overlay) { ov.src = j.overlay; ov.style.display = 'block'; }
      if (j.detected && j.masks) {
        $('autoSepMN').src = j.masks.numbers; $('autoSepMS').src = j.masks.sponsors; $('autoSepMP').src = j.masks.paint;
        $('autoSepMasksM').style.display = 'flex';
        var f = j.fractions || {};
        $('autoSepFrac').innerHTML = '<span style="color:#ff8a8a;">Numbers ' + Math.round((f.numbers || 0) * 100) + '%</span> · ' +
          '<span style="color:#8ab8ff;">Sponsors ' + Math.round((f.sponsors || 0) * 100) + '%</span> · ' +
          '<span style="color:#9affb0;">Paint ' + Math.round((f.paint || 0) * 100) + '%</span>';
        if (msg) msg.textContent = '✓ separated';
      } else {
        $('autoSepMasksM').style.display = 'none'; $('autoSepFrac').textContent = '';
        if (msg) msg.textContent = (j.message || 'Nothing confidently separated — raise Sensitivity.');
      }
    }).catch(function (e) { if (msg) msg.textContent = 'Failed: ' + (e.message || e); });
  }

  function boot() {
    injectButton();
    // re-inject if the panel is (re)created later (defensive, cheap)
    try {
      var obs = new MutationObserver(function () { injectButton(); });
      obs.observe(document.body, { childList: true, subtree: true });
    } catch (e) {}
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
