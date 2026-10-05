# Electron HTTP Liveness Probe Plan (ELEC-04)

WIN #49 — plan to replace the TCP-connect-only health checks in
`electron-app/main.js` with a lightweight HTTP liveness probe.

**Status: PLAN ONLY. `main.js` is NOT edited by this document.**

## Problem (ELEC-04)

Per audit ELEC-04: the watchdog + startup health check are **TCP-connect-only**;
a bound-but-wedged Flask passes as healthy.

In `electron-app/main.js` the server is probed by opening a raw `net.Socket`
and treating a successful TCP `connect` as "healthy." A Python/Flask process
that has **bound** the port but is wedged (deadlocked worker, blocked on a lock,
stuck in import, GIL-starved) still accepts the TCP connection — so
`sock.once('connect', ...)` fires, the check passes, and the server is declared
healthy even though no HTTP request will ever complete. The watchdog therefore
never restarts a hung-but-bound server.

## Ground truth (verified by reading the current main.js)

The relevant code is NOT in a single `waitForFlask`/`waitForServer` function.
There are **three** TCP/`net`-based readiness/health touch points:

1. **Startup readiness poll — inside `startServer(port)`** (the `pollInterval`,
   ~lines 1839-1853). Every 250 ms it opens `new net.Socket()` with
   `sock.setTimeout(300)`, and on `connect` sets `serverReady = true` and
   resolves. This is the real "startup gate." It has a 60 s overall timeout
   (~line 1855) that shows an error dialog if the process is dead.

2. **One-shot `/build-check` HTTP probe — in `app.whenReady`** (~line 2627):
   `http.get('http://127.0.0.1:${serverPort}/build-check', ...)`. This already
   uses HTTP, but it is fire-and-forget logging only — its result does not gate
   startup or trigger a restart.

3. **Periodic watchdog — `startWatchdog()`** (~lines 1894-1924). Every
   **120000 ms** it opens `new net.Socket()` with `sock.setTimeout(8000)`;
   on `connect` it resets `_watchdogFailStreak = 0`; on `timeout`/`error` it
   increments the streak and, once `_watchdogFailStreak >= 2`, calls
   `restartServer()`. (`restartServer()` has a lifetime cap of
   `serverRestartCount >= 3`.) Can be disabled with
   `SPB_DISABLE_SERVER_WATCHDOG=1`.

Other verified facts:

- Imports: `const net = require('net');` (line 13) and
  `const http = require('http');` (line 17) are **both already present**.
  `http` is already used (license flow + the `/build-check` probe), so no new
  require is needed.
- Port/host: the server listens on `serverPort` (default `59876`, may be an
  alternate via `SPB_DEV_PORT` / port scan) bound to `127.0.0.1`. Both socket
  sites call `sock.connect(serverPort, '127.0.0.1')` / `sock.connect(port, ...)`.
  **Do not hardcode a port** — reuse `serverPort` (or the `port` arg in
  `startServer`).
- `net` is also used elsewhere (`isPortFree`, ephemeral-port grab in
  `pickServerPort`, ~lines 1729-1768), so the `net` require **must stay** even
  after this change.

## Endpoint to probe

The bundled server (`server_v5.py`, plus `server.py`/`server_routes/`) exposes
(confirmed via grep across `server.py`, `server_v5.py`,
`server_routes/diagnostics.py`):

- `GET /api/ping` -> `pong` (cheap; no engine/registry work).
- `GET /api/health` -> `200 {"status": "ok", ...}` (heavier; touches registry).
- `GET /build-check` -> already probed at startup.

**Use `/api/ping`** for the watchdog and the startup gate: cheapest, no
engine/registry work, ideal for a frequent loop. `/api/health` would also catch
the wedged case but is heavier and could itself stall under load.

> Confirm at implementation time that `/api/ping` is mounted on the
> Electron-bundled `server_v5.py` instance (grep shows it in
> `server.py`/`diagnostics.py`; `server_v5.py` defines `/api/health`). If only
> `/api/health` is present on the running entry, probe that instead. `/build-check`
> is a third already-working fallback.

## Proposed shared helper (new code)

Add one helper near the server-lifecycle section (suggested: just above
`startServer`). It resolves `true` only on a 2xx within the timeout, and `false`
on any timeout / socket error / non-2xx. The body is drained so a
never-finishing body is caught by the request timeout.

```js
// Resolves true only if the server returns a 2xx to GET /api/ping within
// timeoutMs. Any timeout, socket error, or non-2xx resolves false (unhealthy).
function httpPing(port, timeoutMs) {
  return new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, path: '/api/ping', method: 'GET', timeout: timeoutMs },
      (res) => {
        const ok = res.statusCode >= 200 && res.statusCode < 300;
        res.resume(); // drain body so the socket frees
        res.on('end', () => resolve(ok));
        res.on('error', () => resolve(false));
      }
    );
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => { resolve(false); });
    req.end();
  });
}
```

## Exact spots in `electron-app/main.js` to change

Line numbers are approximate (network-drive checkout; Read line numbers drifted
a little). **Anchor on the `new net.Socket()` blocks and the function names** —
those are unambiguous.

### 1. Watchdog — `startWatchdog()` (~lines 1894-1924)  [PRIMARY FIX]

This is the core ELEC-04 fix. The current interval body is:

```js
watchdogTimer = setInterval(() => {
  if (!serverProcess) return;
  const sock = new net.Socket();
  sock.setTimeout(8000);
  sock.once('connect', () => { sock.destroy(); _watchdogFailStreak = 0; });   // <- false "healthy"
  const onFail = (reason) => { sock.destroy(); if (!serverProcess) return;
    _watchdogFailStreak++; debugLog(...); if (_watchdogFailStreak >= 2) { _watchdogFailStreak = 0; restartServer(); } };
  sock.once('timeout', () => onFail('timeout'));
  sock.once('error',   () => onFail('error'));
  sock.connect(serverPort, '127.0.0.1');
}, 120000);
```

**Change:** replace the socket with `httpPing`, preserving the `_watchdogFailStreak`
logic, the `>= 2` threshold, the `restartServer()` call, the 120000 ms interval,
and the `if (!serverProcess) return` guards:

```js
watchdogTimer = setInterval(() => {
  if (!serverProcess) return;
  httpPing(serverPort, 8000).then((healthy) => {
    if (!serverProcess) return;
    if (healthy) { _watchdogFailStreak = 0; return; }
    _watchdogFailStreak++;
    debugLog(`[Watchdog] Health check failed (HTTP /api/ping); streak=${_watchdogFailStreak}`);
    if (_watchdogFailStreak >= 2) {
      debugLog('[Watchdog] Two consecutive failures — restarting server');
      _watchdogFailStreak = 0;
      restartServer();
    }
  });
}, 120000);
```

Keep the 8000 ms probe timeout (matches the old `sock.setTimeout(8000)`). The
existing **2-consecutive-failure** streak already debounces a single slow probe,
so no extra guard is needed.

### 2. Startup readiness poll — inside `startServer(port)` (~lines 1839-1853)  [SECONDARY]

This is the startup gate (there is no separate `waitForServer`). Current:

```js
const pollInterval = setInterval(() => {
  const sock = new net.Socket();
  sock.setTimeout(300);
  sock.once('connect', () => { sock.destroy(); clearInterval(pollInterval);
    serverReady = true; updateTrayServerStatus(true); resolve(port); });
  sock.once('error',   () => sock.destroy());
  sock.once('timeout', () => sock.destroy());
  sock.connect(port, '127.0.0.1');
}, 250);
```

**Change (optional but recommended for consistency):** make readiness mean
"answers HTTP," not "accepts TCP," so the splash does not clear on a wedged
server. Keep the 250 ms cadence and the outer 60 s timeout untouched; guard
against overlapping in-flight probes with a simple boolean:

```js
let probing = false;
const pollInterval = setInterval(() => {
  if (probing) return;
  probing = true;
  httpPing(port, 1000).then((healthy) => {
    probing = false;
    if (!healthy) return;
    clearInterval(pollInterval);
    serverReady = true; updateTrayServerStatus(true); resolve(port);
  });
}, 250);
```

Use a short per-probe timeout here (e.g. 1000 ms) since this loop runs every
250 ms during startup.

### 3. `/build-check` probe in `app.whenReady` (~line 2627)  [NO CHANGE NEEDED]

Already HTTP-based and informational only. Leave as-is, or optionally switch its
path to `/api/ping` for consistency. Not required for ELEC-04.

### 4. `net` require — DO NOT REMOVE

Unlike a naive reading, `net` stays: `isPortFree()` and the ephemeral-port grab
in `pickServerPort()` (~lines 1729-1768) still use `net.createServer()`.

## Behavior change summary

| Scenario | Old (TCP connect) | New (HTTP /api/ping) |
|---|---|---|
| Server fully up | healthy | healthy (2xx) |
| Port not yet bound | unhealthy (connect refused) | unhealthy (connect error) |
| Bound but wedged (ELEC-04) | **healthy (false positive)** | **unhealthy (timeout) -> 2 strikes -> restartServer()** |
| Returns 500 / error | healthy (TCP fine) | unhealthy (non-2xx) -> restart |

## Edge cases / caveats for implementation

- **Restart storms.** The probe is stricter than TCP. Mitigation already exists:
  the watchdog needs **2 consecutive** misses, `restartServer()` is capped at
  `serverRestartCount >= 3`, and the 120 s interval is generous. Keep all three.
- **Overlapping probes.** Both loops become Promise-based; the watchdog interval
  (120000) far exceeds its probe timeout (8000) so no stacking. The startup loop
  needs the `probing` boolean guard shown above because 250 ms < 1000 ms timeout.
- **Port source of truth.** Pass `serverPort` / `port` into `httpPing`; never a
  literal — the app can run on an alternate port.
- **Probe timeout mechanism.** `httpPing` relies on the `http.request` `timeout`
  option + the `'timeout'` event (we `req.destroy()` then resolve `false`).
  That is exactly what converts a bound-but-wedged server into an unhealthy
  result.
- **Watchdog disable switch.** `SPB_DISABLE_SERVER_WATCHDOG=1` still applies —
  the change is inside the same `setInterval` body, so the early return is
  untouched.

## Verification (when implemented — out of scope for this doc)

- `node --check electron-app/main.js` after edits.
- Manual: launch the app, confirm the window loads (startup probe passes).
- Negative test: suspend the Python child / block its event loop and confirm the
  watchdog logs `Health check failed (HTTP /api/ping)` and restarts after ~2
  intervals, whereas the old TCP check would have stayed "healthy."

## Scope / rules

This document changes nothing. Implementing it edits only
`electron-app/main.js`. Note `electron-app/main.js` is **not** in the
`scripts/sync-runtime-copies.js` runtime manifest (that manifest covers
`paint-booth-*` UI/runtime files, not `main.js`); there is a separate top-level
`main.js` at repo root. Confirm which `main.js` is authoritative for the
Electron build before editing, and edit only that one.
