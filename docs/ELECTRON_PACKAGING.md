# Electron Packaging Hygiene (Plan / Recommendations)

> **Status:** Documentation only. This file describes the current packaging
> state and a safe, non-destructive pre-release plan. It does **not** execute a
> build and does **not** change `package.json`, `VERSION.txt`, `.gitignore`, or
> any engine/finish/render code. Everything below is a *recommendation* for a
> human to apply deliberately and review.
>
> **Audit reference:** ELEC-07 (reproducible build / lockfile + code-signing),
> as tracked in `SPB_ALPHA_AUDIT.md`.
> **Documented:** 2026-05-30

---

## 1. Version truth: the three sources do not agree

There is no single source of truth for the application version today. The three
version-bearing locations were inspected and report different (or missing)
values:

| Source                         | Field / form         | Current value                      |
| ------------------------------ | -------------------- | ---------------------------------- |
| `VERSION.txt`                  | whole file (string)  | `6.3.0-alpha (Spring Catalogue)`   |
| `package.json` (repo root)     | `"version"`          | **absent — no `version` field**    |
| `electron-app/package.json`    | `"version"`          | `6.3.0`                            |

What this means in practice:

- The version electron-builder stamps into the installer and the
  `Shokker Paint Booth V6` app metadata comes from **`electron-app/package.json`
  = `6.3.0`** (it also feeds the installer filename via
  `ShokkerPaintBoothV6-${version}-Setup.exe` and the differential-update
  `latest.yml`).
- `VERSION.txt` says `6.3.0-alpha (Spring Catalogue)`. The numeric core (`6.3.0`)
  matches the Electron app, but the human-readable suffix (`-alpha (Spring
  Catalogue)`) lives only in `VERSION.txt` and is **not** reflected in the
  shipped build.
- The repo-root `package.json` has **no `version` field at all**, so it cannot
  act as a tiebreaker and would report `undefined` / `1.0.0` defaults to any
  tooling that reads it.

So the numbers are not in open conflict (both numeric sources are `6.3.0`), but
the **representation is fragmented**: three files, three formats, one missing
field. The risk is drift the next time someone bumps one without the others.

### Recommendation: one canonical version source

Make **`electron-app/package.json` `"version"` the single source of truth for
the numeric release version**, because that is the value electron-builder
actually ships (installer name, app metadata, auto-update `latest.yml`). Then
derive the rest:

1. Bump the version in **`electron-app/package.json`** only.
2. Regenerate `VERSION.txt` from it — keep the numeric core identical
   (`6.3.0`) and append any human channel/codename suffix
   (e.g. `6.3.0-alpha (Spring Catalogue)`) as a presentation detail. Never let
   `VERSION.txt`'s numeric core diverge from `electron-app/package.json`.
3. If the repo-root `package.json` is ever meant to carry a version, add a
   `"version"` field and set it from the same source; otherwise leave it without
   one rather than letting it hold a stale third number.

> The rule: **bump in exactly one place (`electron-app/package.json`), then
> propagate.** Do not hand-edit the numeric version in multiple files
> independently. (A tiny, reviewed release helper could read
> `electron-app/package.json` and rewrite `VERSION.txt` — that is the kind of
> propagation to add later; it is intentionally **not** implemented here.)

---

## 2. Missing `electron-app/package-lock.json` (ELEC-07)

Lockfile status as inspected:

- **`electron-app/package-lock.json` is absent.** The Electron app has no
  committed lockfile, so its dependency tree (electron `33.4.11`,
  electron-builder `^25.1.8`, electron-updater `^6.8.3`, plus all transitive
  deps) is not pinned.
- A `package-lock.json` exists at the **repo root**, but the root `.gitignore`
  ignores `package-lock.json` globally — so it is **not committed** and does not
  help reproducibility either.

Because the Electron app installs from loose ranges with no committed lockfile,
two builds on two machines (or on two dates) can resolve to **different**
transitive trees. That makes the desktop installer non-reproducible — the
substance of audit item **ELEC-07** ("No reproducible build on a clean clone"
in `SPB_ALPHA_AUDIT.md`).

### Recommendation: commit a lockfile and use `npm ci`

1. **Stop git-ignoring the lockfiles you need.** The current root `.gitignore`
   contains a blanket `package-lock.json` rule. To get reproducible Electron
   builds, that rule must not swallow the Electron app's lockfile. Either remove
   the blanket ignore, or add a negation so the Electron lockfile is tracked,
   e.g.:

   ```gitignore
   # keep the Electron app lockfile tracked for reproducible builds
   !electron-app/package-lock.json
   ```

2. **Generate and commit `electron-app/package-lock.json`.** Run `npm install`
   once inside `electron-app/`, review the resulting lockfile, and commit it.
3. **Use `npm ci` in the release path, not `npm install`.** `npm ci` installs
   strictly from the committed lockfile, fails fast if `package.json` and the
   lockfile disagree, and yields a reproducible dependency tree across machines
   and CI. Reserve `npm install` for *intentional* dependency updates (which
   rewrite the lockfile and should be a reviewed change).

> This is the concrete fix for ELEC-07's reproducibility half. The code-signing
> half is covered in the checklist below.

---

## 3. Safe pre-release packaging checklist

Run through this before producing a desktop installer. None of these steps touch
engine paint/spec math, finish data, or render output — they are purely
packaging hygiene.

- [ ] **Version bump in one place.** Update the version in
      `electron-app/package.json` only (Section 1), then propagate the numeric
      core into `VERSION.txt`. Confirm the numeric cores match before building.
- [ ] **Lockfile tracked and present.** Ensure `electron-app/package-lock.json`
      exists, is **not** swallowed by the blanket `package-lock.json` ignore
      (Section 2), and is committed. If absent, run one `npm install` in
      `electron-app/`, review the diff, and commit the lockfile.
- [ ] **Reproducible install.** In `electron-app/`, run `npm ci` (not
      `npm install`) so dependencies come strictly from the lockfile. Treat any
      `npm ci` failure as a real lockfile / `package.json` mismatch to fix — do
      not bypass it.
- [ ] **Clean the workspace first.** Remove stale `electron-app/dist-*`
      directories from previous runs (there are several on disk today:
      `dist-contributor`, `dist-contributor-portable`, and two
      `dist-sandbox-*` dirs). Build artifacts must be regenerated, never reused.
      (Deleting these is a human action — not performed by this doc.)
- [ ] **Build the installer.** From `electron-app/`, run `npm run build`
      (which runs the `copy-server` prebuild, then
      `electron-builder --win --x64`). Output lands in `electron-app/dist/`.
- [ ] **Code signing (ELEC-07).** Builds are currently **UNSIGNED** (confirmed
      in the audit and `SPB_UPDATE_SYSTEM.html`). Unsigned Windows (NSIS)
      installers trigger SmartScreen "Windows protected your PC" warnings and
      undermine the electron-updater `verifyUpdateCodeSignature` flow. Before
      public distribution:
      - Acquire an Authenticode / EV (or OV) code-signing certificate
        (e.g. DigiCert or Sectigo, per `electron-app/BUILD.md`).
      - Configure electron-builder signing (`win.certificateFile` +
        `certificatePassword`, or the `CSC_LINK` / `CSC_KEY_PASSWORD` env vars).
      - Certificate material and passwords are **secrets** — pass them via
        environment / CI secret store, never commit them. (`.gitignore` already
        ignores `*.key`, `*.license`, `.env*`, `credentials.json`, `secrets.yaml`.)
      - This doc does not configure signing; it records that signing is required
        and that credentials stay out of the repo.
- [ ] **Verify auto-update wiring (if publishing).** `npm run publish` uses the
      GitHub provider (`owner: ShokkerGroup`, `repo: ShokkerPaintBooth`) and
      `differentialPackage: true`. Confirm the GitHub token is supplied via env,
      not committed, before publishing.
- [ ] **Do not commit build artifacts.** Confirm no `dist-*` / `dist/` output is
      staged for commit (see below).
- [ ] **Tag / record the release version** matching the single source of truth
      so the shipped installer's version is traceable.

---

## Artifacts that must NOT be committed

These are generated outputs or local/secret material. Keep them out of version
control:

- `electron-app/dist/`, `electron-app/dist-contributor*/`,
  `electron-app/dist-sandbox-*/`, `electron-app/out/` — electron-builder output
  (NSIS `.exe`, unpacked app, blockmaps, `latest.yml`, etc.).
- `node_modules/` (root and `electron-app/`).
- Build logs: `electron-app/_build_*.txt`, `electron-app/_build_*.log`,
  `electron-app/npm_build_log.txt`, `electron-app/rebuild_log.txt`,
  `*.log`, `build_log*.txt`.
- Code-signing certificates, `.pfx` / `.p12` files, signing passwords, GitHub
  publish tokens, and any `CSC_*` / `.env` files.

### `.gitignore` status (good baseline, one gap)

The current root `.gitignore` already handles the Electron build output well:

```gitignore
node_modules/
electron-app/dist/
electron-app/dist-sandbox-*/
electron-app/dist-contributor*/
electron-app/node_modules/
electron-app/_build_*.txt
electron-app/_build_*.log
electron-app/out/
package-lock.json
yarn.lock
pnpm-lock.yaml
```

So the `dist-*` directories present on disk today are **ignored, not tracked** —
that is the correct baseline. The single gap for reproducibility is the blanket
`package-lock.json` ignore, which also blocks the Electron lockfile that
ELEC-07 wants committed. See Section 2 for the recommended negation.

> Note: do **not** blanket-add `dist-*/` at the repo root — the existing
> Electron-scoped rules are already correct and more precise. The only change
> recommended here is allowing `electron-app/package-lock.json` to be tracked.

---

## Quick reference: current state snapshot (inspected 2026-05-30)

- `VERSION.txt` = `6.3.0-alpha (Spring Catalogue)`
- root `package.json` = **no `version` field**
- `electron-app/package.json` version = `6.3.0` (this is what electron-builder ships)
- `electron-app/package-lock.json` = **absent** (ELEC-07)
- root `package-lock.json` = present on disk but **git-ignored** (not committed)
- `electron-app/dist-*` dirs present on disk (4) but **git-ignored** (good)
- Builds are **UNSIGNED** today (code-signing pending, ELEC-07)
- electron `33.4.11`, electron-builder `^25.1.8`, electron-updater `^6.8.3`
- Build: `npm run build` → `electron-builder --win --x64`; output `electron-app/dist/`
- Publish: GitHub provider (`ShokkerGroup/ShokkerPaintBooth`), differential updates on
