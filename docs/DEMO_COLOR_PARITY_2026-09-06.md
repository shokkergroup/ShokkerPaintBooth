# Demo .13 — Cherry Polka selection and darkness repair

Owner report: main app selects Cherry Polka as both Base Material and special
Base Color. Demo .12 selected finish-own; manually selecting special with Color
Lab enabled produced an almost-black result despite HSB 0 and strengths 100%.

## Causes established

1. `demo/frontend/js/app.js` explicitly chose `baseColorMode='finish'` after an
   unlocked material selection. Main's `js/zones/zone-finish-assignment-controls.js`
   automatically assigns special colors for applicable materials instead.
2. Color Lab's stored/default Depth was 65%. Enabling it passed `.65` into the
   candy absorption function. HSB zero does not neutralize that separate effect.
   At this depth its exponent is 1.665 and the candy result fully replaces the
   selected color. Cherry Polka is already dark red, so the added absorption
   crushes it. The underlying shipped special capture itself is correct.
3. Simply setting Depth to zero was insufficient: the old Color Lab blend
   returned the source-responsive material at zero, rather than the selected
   special/solid/gradient. Demo's neutral endpoint now preserves the selection.

## Resulting behavior

- An unlocked ordinary Base Material pick chooses its matching special color
  and resets Depth, Flip and Underglow to zero. HSB and strengths are retained.
- LOCK preserves the existing Base Color mode/source/color/gradient and effects.
- Enabled Color Lab with zero effects is identical to Color Lab off. Depth remains
  an intentional candy-darkening control. Reset is now zero rather than 65%.
- Manually choosing finish-own keeps its existing source-responsive rendering.
  The Fracture shortcut explicitly keeps this route when unlocked; locked colors
  remain locked. No source artwork, finish formula, main-app code or spec recipe changed.
- Saved sessions keep explicit effects on reload. Reselect the material unlocked,
  or reset the three effects, to get the new neutral starting color. There is no
  forced rewrite of old saved looks.

## Evidence and scope

`_demo_color_parity_work/verify_cherry.py` generates a disposable four-color source,
compares actual shipped captures with current main-engine color-source generation,
and exercises actual demo preview/render endpoints with disposable TGA output.

| Size | Old depth 65% mean RGB | Corrected mean RGB | Max error against main special RGB |
|---|---:|---:|---:|
| 1024 | 7.2412 | 34.9741 | 0 |
| 2048 | 7.1031 | 34.5984 | 0 |

The 2048 mean RGB reduction was 79.47%. This is an RGB statistic, not a measured
perceptual brightness or in-game lighting claim. The before/after spec arrays
are identical. The 1024 HTTP preview and 2048 exported TGA match their native
special captures exactly. Report: `_demo_color_parity_work/cherry-proof.json`.

Actual browser UI testing uses the bundled ARCA starter, Zone 1 restricted to
BASE01 with Remaining coverage, in an isolated demo .13 backend on port 59916.
It verifies automatic special selection with Color Lab already enabled, visible
red pattern, locked Cherry color surviving a Chrome material change, manual
finish-own selection, deliberate depth 65 darkening, and reselect resetting to 0.
Captures `cherry-neutral-ui.png`, `cherry-finish-own-ui.png`, `cherry-depth65-ui.png`
are real UI captures of that build. No night-light/viewer test is claimed here.
The main-app comparison is **actual engine output**, not a native main-app playtest.

Release checks and installer receipt are recorded alongside this evidence when
complete. The website remains a guide captured against demo .12; this repair does
not silently relabel those captures or publish a new product listing.

## Regression coverage

- Executed frontend selection function for all five color modes, lock on/off,
  preserving adjustments; Fracture source-route and locked-solid checks.
- Neutral exact RGB including near-black and partial color strength; deliberate
  candy depth remains effective and reversible.
- Real-capture release gate covers all 30 materials/color sources at both sizes,
  finish-own, special and solid, Lab off/on neutral, PNG/TGA round trips and spec.
- Demo API tests use per-test temporary directories; the former shared root
  fixture contaminated the file-browser assertion with previous tests' files.

No finish renderer was rebuilt; finish design/M7 gates are not applicable to this
selection/compositing fix. Curated captures and main runtime mirrors are unchanged.

## Why previous checks missed it

The prior release color gate tested Color Lab **off** (including ignoring legacy
depth/flip/glow fields without opt-in). It did not test an ordinary material pick
with Color Lab already checked, or the zero-depth endpoint. This release adds
both UI state transitions and neutral-Lab RGB/spec assertions across the actual
shipped captures. Avoid correcting this kind of failure by brightening a curated
finish recipe: its authored special capture was already correct.

The isolated native development shell encountered the backend host allowlist
while its test-port environment was incomplete; the backend configuration was
corrected without weakening validation. Native helper windows were closed. Actual
UI checks were completed in the browser, not claimed as a packaged native test.

## Completed local release verification

- **121 focused tests pass.** Full log: `_demo_color_parity_work/tests.log`.
- **360 native-capture color checks pass** (180 Lab off + 180 enabled/neutral),
  including exact PNG/TGA and unchanged spec. `demo/color-fidelity-report.json`.
- Reviewed snapshot inventory verification and packaged `demo_server.py --check`
  pass. Packaged Python + packaged compositor + packaged material assets produce
  exact Cherry Polka preview/export; `packaged-verification/proof.json`.
- Source/stage/unpacked hashes match for every changed runtime file;
  `_demo_color_parity_work/payload-hashes.json`.
- `electron-demo/dist/ShokkerPaintBooth-SHOKK-DEMO-1.0.0-demo.13-Setup.exe` built
  successfully: **723,916,419 bytes**, SHA-256
  `6682286D31B50CA12BE5269F0E917B0995F0CF10A3AB9FB9356A7D29B4883CF7`.
- Authenticode status is **NotSigned**. This is a local installer, not a signed
  public release. No installation over the owner's active demo, clean-profile
  installer certification, itch.io upload or update-feed publication was performed.
  Follow the signing/clean-profile/starter-rights checks in `electron-demo/README.md`
  before a public release. Build log saying "signing" is not signature evidence.

Retain `_demo_color_parity_work/` as load-bearing release evidence and the running
local review backend. Personal paint files were never output targets.
