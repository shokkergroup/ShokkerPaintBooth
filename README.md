# Shokker Paint Booth (SPB)

> The painter's painter for iRacing — real materials, real preview, real paint.

Shokker Paint Booth is a purpose-built livery painter for iRacing that paints *paint*. Not pixels. Not flat colors. Paint — with metallics that flake, chrome that bends light, carbon fiber that weaves, anodized aluminum that shifts across the body, and candy coats that glow. All previewed in real time on a 3D-aware canvas, all exported in the exact TGA + spec map format iRacing expects.

If you have ever hand-painted a spec map in Photoshop at 2 a.m. wondering whether `G=120` was "matte enough," SPB was built for you.

---

## Screenshot

![Shokker Paint Booth main window](assets/screenshot-placeholder.png)

> *(Replace with a real screenshot before each release. Recommended: `assets/screenshot-main.png` @ 1920x1080.)*

---

## Top 10 Feature Highlights

1. **Real-time PBR preview** — A 3D-aware car-shape preview renders as you paint. What you see is what ships to iRacing.
2. **Zone-level spec control** — One panel can be matte, the next mirror chrome — side by side, pixel-accurate.
3. **192 spec overlay patterns** across 19 PBR categories (brushed, hammered, peened, flaked, woven, and more).
4. **Monolithic finishes** — one-click base + pattern + spec bundles like COLORSHOXX, MORTAL SHOKK, PARADIGM, and ATELIER.
5. **Pattern-per-channel control** — different pattern on color vs. spec map (unique to SPB).
6. **30+ new finishes** in v6.1 including candy coats, chameleon shifts, and neon underground.
7. **Finish Mixer + pattern strength zones** — blend finishes and gate pattern intensity by region.
8. **PSD import** — load Photoshop layers directly; groups flatten intelligently.
9. **TGA export** at 2048x2048 — the exact format iRacing wants, with spec map baked and ready.
10. **Live Preview** — render history polling keeps the preview in sync while you iterate.

See [SPB_FEATURES.md](SPB_FEATURES.md) for the full feature catalog.

---

## Installation

1. Download `Setup.exe` from the latest release.
2. Run it. Windows SmartScreen may warn — click **More info → Run anyway**.
3. Launch **Shokker Paint Booth** from the Start Menu.

Full install guide: [SPB_GUIDE.md](SPB_GUIDE.md).

> SPB is Windows-only. iRacing is Windows-only. No Mac/Linux builds are planned.

---

## Quickstart

Render your first livery in five minutes with the step-by-step walkthrough: [SPB_QUICKSTART.md](SPB_QUICKSTART.md).

TL;DR:
1. Launch SPB (Silverado demo PSD auto-loads).
2. Select a layer → Add a zone → Lock zone to layer.
3. Eyedropper a color → pick a finish → press **RENDER**.

---

## Development

SPB is an Electron desktop app with a Python Flask render server embedded via `pyserver`.

### Run from source

```bash
# Clone
git clone https://github.com/shokkergroup/shokker-paint-booth.git
cd shokker-paint-booth

# Install JS deps
cd electron-app
npm install

# Start in dev mode (spawns embedded Python server)
npm run start
```

The Python render server lives at `electron-app/server/` and starts automatically on a free port. Static assets (`paint-booth-*.js`, `.css`, `.html`) are served directly from the Electron main window.

For full dev onboarding see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

---

## Build

To produce a distributable `Setup.exe`:

```bash
cd electron-app
npm run build
```

This invokes `electron-builder` which packages the Electron shell, Python server (via `pyinstaller`), assets, and NSIS installer. Output lands in `electron-app/dist/`.

Full build guide: [docs/BUILD.md](docs/BUILD.md).

---

## Contributing

We welcome PRs, bug reports, and livery testers. Before contributing please read [CONTRIBUTING.md](CONTRIBUTING.md) — it covers the **3-copy sync rule** (critical!), file ownership, code style, and PR process.

Also read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — we aim to be the friendliest iRacing community on Discord.

For security issues, see [SECURITY.md](SECURITY.md).

---

## License

See [LICENSE.txt](LICENSE.txt) for licensing information. The SPB source is currently **private / experimental** during the Gold-to-Platinum phase; a public license is TBD before Platinum GA.

Third-party acknowledgements and credits: [AUTHORS.md](AUTHORS.md).

---

## Documentation Map

**User-facing:**
- [SPB_GUIDE.md](SPB_GUIDE.md) — the complete user guide
- [SPB_QUICKSTART.md](SPB_QUICKSTART.md) — 5-minute walkthrough
- [SPB_FEATURES.md](SPB_FEATURES.md) — every feature, documented
- [SPB_WORKFLOW_EXAMPLES.md](SPB_WORKFLOW_EXAMPLES.md) — recipe book
- [SPB_KEYBOARD_SHORTCUTS.md](SPB_KEYBOARD_SHORTCUTS.md) — cheat sheet
- [SPB_SPEC_MAP_GUIDE.md](SPB_SPEC_MAP_GUIDE.md) — R/G/B/A spec map deep dive
- [SPB_TROUBLESHOOTING.md](SPB_TROUBLESHOOTING.md) — common issues
- [SPB_FAQ.md](SPB_FAQ.md) — frequently asked questions
- [SPB_RELEASE_NOTES.md](SPB_RELEASE_NOTES.md) — what's new per version

**Developer-facing:**
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — dev setup
- [docs/BUILD.md](docs/BUILD.md) — building Setup.exe
- [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md) — shipping a release
- [docs/DEBUGGING.md](docs/DEBUGGING.md) — debug tips
- [docs/PERFORMANCE.md](docs/PERFORMANCE.md) — perf tuning
- [docs/TESTING.md](docs/TESTING.md) — test strategy
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to contribute
- [CHANGELOG.md](CHANGELOG.md) — version history

---

## Credits

Shokker Paint Booth is built and maintained by the **Shokker Group**. Lead engineer: Ricky Whittenburg. Full credit list in [AUTHORS.md](AUTHORS.md).

Community: Join the [SPB Discord](https://discord.gg/shokker) to share liveries, file bugs, and get early builds.

---

*Paint the paint. Not the pixel.*
