# Authors & Credits

Shokker Paint Booth is the work of many hands, eyes, and late-night iRacing sessions. This file acknowledges the humans, AI agents, open-source projects, and livery artists who made SPB possible.

---

## Core Team

| Role | Name | Contact |
|---|---|---|
| Founder / Lead Engineer | Ricky Whittenburg | ricky@shokkergroup.com |
| Shokker Group | (entity) | https://shokkergroup.com |

## Contributors

Contributors are listed in alphabetical order once they have a merged PR. Add yourself at the bottom of the table when you contribute.

| GitHub handle | Area |
|---|---|
| *(open a PR adding your handle)* | *(feature / fix area)* |

## AI Development Agents

SPB's Gold-to-Platinum phase was accelerated by a team of specialized AI agents running under Claude Code. Their contributions are tracked in `memory/heartbeats_history.md` and reflected in the git log. Agent roles include:

- **Render / Engine Agent** — paint_v2 finish development and spec map tuning
- **UI Agent** — `paint-booth-*.js` state management and canvas tooling
- **Server Agent** — Flask render API and build system
- **Docs Agent** — `SPB_*.md` user-facing documentation
- **QA / Audit Agent** — `QA_REPORT.md` and finish quality audits
- **Release Agent** — `CHANGELOG.md` and tagged release coordination

## Livery Artists & Beta Testers

Thanks to the painters who stress-tested pre-release builds, reported bugs, and painted liveries we used in promotional material. Full list maintained on the Discord `#hall-of-fame` channel; public name adds happen with permission.

---

## Open-Source Dependencies

SPB stands on the shoulders of giants. Major runtime dependencies:

### Python side
- **numpy** — array math, the backbone of the render engine
- **Pillow (PIL)** — image I/O and PSD parsing
- **Flask** — HTTP render server
- **psd-tools** — PSD layer extraction
- **opencv-python** — filtering and resampling
- **scipy** — signal processing for pattern generation

### JavaScript / Electron side
- **Electron** — desktop shell
- **electron-builder** — NSIS installer packaging
- **PyInstaller** — Python server bundling

### Research & reference
- iRacing paint kit community — for the spec map RGBA semantics that every painter had to reverse-engineer the hard way
- Disney BRDF / Unreal PBR documentation — the theoretical basis of our roughness + metallic + clearcoat model
- Substance Designer community — for pattern generator inspiration

See `THIRD_PARTY_LICENSES.txt` (generated at build time) for the full license texts of bundled components.

---

## Special Thanks

- The iRacing livery community on Discord, Reddit, and Trading Paints — you asked for this tool.
- Every painter who ever hand-painted a spec map in Photoshop at 2 a.m. — we felt your pain, and built this for you.
- The folks who open-sourced their PSD paint kits so we had a demo Silverado to ship with.

---

## Adding Yourself

If you contribute to SPB via a merged PR, feel free to add yourself (or request addition) to the Contributors table. Please include:

- Your GitHub handle or preferred public name
- The area you contributed in (one phrase)
- Optional: a link to your livery gallery, website, or Trading Paints profile

We want this file to accurately reflect the community. Thank you for helping build SPB.
