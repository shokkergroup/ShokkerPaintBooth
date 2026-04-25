# Building the SPB Setup.exe

> How to produce a distributable NSIS installer from source.

This guide covers a full production build. For dev-mode runs, see [DEVELOPMENT.md](DEVELOPMENT.md).

---

## Prerequisites

- All of [DEVELOPMENT.md](DEVELOPMENT.md) prerequisites
- **PyInstaller** (`pip install pyinstaller`)
- **NSIS 3.x** (bundled via `electron-builder` — no separate install)
- **~15 GB free disk** (the build is large during packaging)

Optional:
- **Windows code-signing certificate** (for signed installers; Platinum GA only)

---

## The Build in One Command

```bash
cd electron-app
npm run build
```

This runs the chain:

1. `copy-server-assets.js` — mirrors root Python + JS assets into `electron-app/server/`.
2. `pyinstaller` — packages the Python server into `server/pyserver/`.
3. `electron-builder` — bundles Electron + server + UI into an NSIS installer.
4. Output lands in `electron-app/dist/Shokker Paint Booth Setup X.Y.Z.exe`.

Expected build time: **5–12 minutes** on modern hardware. The PyInstaller step is the long pole.

---

## Step-By-Step (For Debugging a Build)

### Step 1 — Sync server assets

```bash
cd electron-app
node copy-server-assets.js
```

This copies:
- Root `*.py` files into `electron-app/server/`
- Root `paint-booth-*.js`, `*.css`, `*.html` into `electron-app/server/` (for the Flask static route)
- `engine/` tree (recursive) into `electron-app/server/engine/`

Verify the copy:
```bash
diff -r engine/ electron-app/server/engine/  # should be empty
```

### Step 2 — PyInstaller bundle

```bash
cd electron-app/server
pyinstaller --onedir --noconsole --name pyserver server.py
```

Output: `electron-app/server/dist/pyserver/` containing `pyserver.exe` + `_internal/` folder with the Python runtime and dependencies.

Move `_internal/` contents to where `electron-app` expects (see `package.json` `extraResources` for the mapping).

### Step 3 — Electron Builder

```bash
cd electron-app
npm run build:electron
```

This invokes `electron-builder` (configured in `package.json` under the `"build"` key). It:

- Packages `main.js`, `preload.js`, `license-preload.js`, and `license.html`
- Bundles the PyInstaller output as an extra resource
- Signs (if cert is present) and timestamps
- Compiles an NSIS installer

---

## Output Layout

After a successful build:

```
electron-app/dist/
├── Shokker Paint Booth Setup 6.2.0.exe       ← the installer
├── win-unpacked/                              ← unpacked app (for debugging)
│   ├── Shokker Paint Booth.exe
│   ├── resources/
│   │   └── pyserver/                          ← bundled Python
│   └── ... (Electron internals)
└── builder-effective-config.yaml              ← resolved config
```

Install the `Setup.exe` on a clean Windows machine to smoke-test.

---

## Common Build Failures

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: numpy` in pyinstaller | Missing hidden import | Add `--hidden-import=numpy` or a `.spec` file entry |
| `EPERM: operation not permitted` | Antivirus locking a dist file | Add `electron-app/dist/` to AV exclusions |
| `electron-builder` can't find `icon.ico` | Wrong path | Check `build.win.icon` in `package.json` |
| Installer opens but app won't start | Server spawn failure | Check `main.js` spawn path; inspect `%APPDATA%\Shokker Paint Booth\logs\` |
| `Cannot find module 'X'` at runtime | Missing from `extraResources` | Add to `build.extraResources` in `package.json` |
| 500 MB+ installer | Debug symbols included | Ensure `--noconsole` and `--strip` in pyinstaller |

---

## Signing (Platinum GA Only)

During Gold-to-Platinum we ship unsigned installers. Windows SmartScreen warns users, which we document in [../SPB_GUIDE.md](../SPB_GUIDE.md#installation).

For the Platinum GA release we will:

1. Purchase a DigiCert or Sectigo code-signing cert.
2. Configure `CSC_LINK` and `CSC_KEY_PASSWORD` env vars (or Windows cert store).
3. `electron-builder` auto-signs if a cert is present.
4. Timestamping via RFC3161 endpoint.

Documented more fully in the release runbook: [RELEASE_PROCESS.md](RELEASE_PROCESS.md).

---

## Build Artifacts to Ignore

`.gitignore` already excludes:

- `electron-app/dist/`
- `electron-app/node_modules/`
- `*.exe`, `*.pdb`, `*.dll`
- `server.build/`, `server.dist/`, `server.onefile-build/`
- `_pybuild_work/`, `_pybuild_work_ag/`

Never commit installer binaries. Release artifacts live on GitHub Releases + PayHip.

---

## Verifying the Build

After installing the Setup.exe:

1. Launch SPB from Start Menu.
2. The Silverado demo should auto-load.
3. Make a zone, pick a finish, press **RENDER**.
4. Verify render completes without error.
5. Export TGA — file should be 2048x2048 and open cleanly in Photoshop.
6. Check `%APPDATA%\Shokker Paint Booth\logs\` for any ERROR-level entries.

If all six pass, you have a good build.

---

## Reducing Build Size

The current Setup.exe is ~180 MB. To reduce:

- Exclude optional numpy MKL blobs (saves ~30 MB)
- Strip unused matplotlib backends (not currently pulled, just in case)
- Use UPX compression on `pyserver.exe` (saves ~10 MB but slows startup)
- Prune unused PSD sample files from `assets/`

Past 150 MB gets into diminishing returns — painters' machines have the disk.

---

## See Also

- [DEVELOPMENT.md](DEVELOPMENT.md) — dev loop (not build)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md) — what to do after a successful build
- [TESTING.md](TESTING.md) — what to test on a fresh install
- `electron-app/BUILD.md` — the in-repo build quick-reference (maintained by build agent)
