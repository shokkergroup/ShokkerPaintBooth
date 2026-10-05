(function (global) {
  'use strict';

  function install(deps) {
    deps = deps || {};
    var doc = deps.document || global.document;
    var win = deps.window || global;
    var consoleApi = deps.console || global.console || { warn: function () {} };
    var setTimeoutFn = deps.setTimeout || global.setTimeout;
    var clearTimeoutFn = deps.clearTimeout || global.clearTimeout;
    var setIntervalFn = deps.setInterval || global.setInterval;
    var clearIntervalFn = deps.clearInterval || global.clearInterval;
    var toastTimer = null;

    function toastClass(msg, isError) {
      var sev = typeof isError === 'string' ? String(isError).toLowerCase() : '';
      if (sev === 'warn') sev = 'warning';
      var isSuccess = typeof msg === 'string' && (msg.charCodeAt(0) === 10003 || msg.toLowerCase().startsWith('saved'));
      var isErr = isError === true || sev === 'error';
      var isWarning = sev === 'warning' || (typeof msg === 'string' && msg.toLowerCase().startsWith('warning'));
      return 'toast show' + (isErr ? ' error' : sev === 'success' || isSuccess ? ' success' : isWarning ? ' warning' : sev === 'info' ? ' info' : '');
    }

    function showToast(msg, isError, details) {
      var toast = doc && doc.getElementById ? doc.getElementById('toast') : null;
      if (!toast) {
        if (consoleApi && consoleApi.warn) consoleApi.warn('[SPB] Toast element not found, message:', msg);
        return;
      }
      toast.className = toastClass(msg, isError);
      toast.innerHTML = '';
      var msgSpan = doc.createElement('span');
      msgSpan.textContent = msg;
      if (details) {
        var detSpan = doc.createElement('div');
        detSpan.textContent = details;
        detSpan.style.cssText = 'font-size:10px; color:rgba(255,255,255,0.6); margin-top:2px;';
        var wrapper = doc.createElement('div');
        wrapper.appendChild(msgSpan);
        wrapper.appendChild(detSpan);
        toast.appendChild(wrapper);
      } else {
        toast.appendChild(msgSpan);
      }
      var closeBtn = doc.createElement('span');
      closeBtn.innerHTML = '&#x2715;';
      // pointer-events:auto guarantees the X stays clickable even if a parent rule
      // ever sets pointer-events:none again. (7.0.5-uxfix)
      closeBtn.style.cssText = 'cursor:pointer; margin-left:12px; font-weight:bold; opacity:0.7; flex-shrink:0; pointer-events:auto;';
      closeBtn.title = 'Dismiss';
      closeBtn.onclick = function (ev) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        // Drop the 'show' class (CSS fades it out + restores pointer-events:none)
        // and clear the inline display so the dismissed toast can't linger or
        // intercept clicks. Cancel the auto-hide timer for this toast.
        toast.className = 'toast';
        toast.style.display = 'none';
        clearTimeoutFn(toastTimer);
      };
      toast.style.display = 'flex';
      toast.style.alignItems = 'center';
      toast.appendChild(closeBtn);
      // [SPB-TOAST-RELOCATE 2026-08-25] anchor above the "+ Add Zone" stack (bottom-LEFT);
      // helper lives in paint-booth-2-state-zones.js and carries the EASY-mode fallback
      if (win._spbToastAnchorAboveZones) win._spbToastAnchorAboveZones(toast);
      clearTimeoutFn(toastTimer);
      toastTimer = setTimeoutFn(function () { toast.className = 'toast'; }, 60000);
    }

    var renderNotify = {
      _originalTitle: doc ? doc.title : '',
      _flashTimer: null,
      playSound: function (success) {
        try {
          var AudioCtor = win.AudioContext || win.webkitAudioContext;
          var ctx = new AudioCtor();
          var osc = ctx.createOscillator();
          var gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = success ? 'sine' : 'square';
          osc.frequency.setValueAtTime(success ? 880 : 220, ctx.currentTime);
          if (success) osc.frequency.setValueAtTime(1175, ctx.currentTime + 0.12);
          gain.gain.setValueAtTime(success ? 0.15 : 0.1, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (success ? 0.35 : 0.3));
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + (success ? 0.35 : 0.3));
        } catch (_) {}
      },
      flashTitle: function (msg) {
        if (!doc) return;
        if (this._flashTimer) clearIntervalFn(this._flashTimer);
        var on = true;
        var self = this;
        this._flashTimer = setIntervalFn(function () {
          doc.title = on ? msg : self._originalTitle;
          on = !on;
        }, 800);
        var stop = function () {
          clearIntervalFn(self._flashTimer);
          self._flashTimer = null;
          doc.title = self._originalTitle;
          if (win.removeEventListener) win.removeEventListener('focus', stop);
        };
        if (win.addEventListener) win.addEventListener('focus', stop);
        setTimeoutFn(stop, 30000);
      },
      browserNotify: function (title, body) {
        if (!doc || doc.hasFocus()) return;
        var NotificationApi = win.Notification || global.Notification;
        if (!NotificationApi) return;
        if (NotificationApi.permission === 'granted') {
          new NotificationApi(title, { body: body, icon: 'shokker' });
        } else if (NotificationApi.permission !== 'denied') {
          NotificationApi.requestPermission();
        }
      },
      onRenderComplete: function (success, elapsed, zoneCount) {
        this.playSound(success);
        if (doc && !doc.hasFocus()) {
          if (success) {
            this.flashTitle('Render done! (' + elapsed + 's)');
            this.browserNotify('Shokker Render Complete', zoneCount + ' zones rendered in ' + elapsed + 's');
          } else {
            this.flashTitle('Render failed!');
            this.browserNotify('Shokker Render Failed', 'Check the Paint Booth for details');
          }
        }
      }
    };

    if (doc && doc.addEventListener) {
      doc.addEventListener('click', function () {
        var NotificationApi = win.Notification || global.Notification;
        if (NotificationApi && NotificationApi.permission === 'default') NotificationApi.requestPermission();
      }, { once: true });
    }

    global.showToast = showToast;
    global.RenderNotify = renderNotify;
    return { showToast: showToast, RenderNotify: renderNotify, toastClass: toastClass };
  }

  global.SPBZoneToastNotificationControls = { install: install };
})(typeof window !== 'undefined' ? window : globalThis);
