# Spec Map Channel Reference (iRacing-compatible PBR)

When generating or authoring spec maps (M, R, CC), use these ranges. Output is 0–255 per channel; the renderer/iRacing uses them as follows.

## Channels

| Channel | Role | 0 | 255 |
|--------|------|---|-----|
| **Red (M)** | **Metallic** | Non-metallic (dielectric), dark | Very metallic, chrome-like |
| **Green (R)** | **Roughness** | Smooth, glossy, shiny (strong reflection) | Rough, matte (weak reflection) |
| **Blue (CC)** | **Clearcoat** | — | — |

## Clearcoat (blue) — important

- **0 exactly = clearcoat disabled.** This is a distinct, valid no-coat state in the
  iRacing contract and in SPB's shared iron-rule helper. The normal multi-zone
  full-render finalizer currently raises non-authored `0` to `16`, however, so a
  recipe that depends on true zero must verify the final exported TGA. SHOKK
  authored-set pixels have a specific zero-preservation exemption.
- **1–15 = no-coat / legacy band in iRacing; do not author these intermediate
  bytes in SPB.** Resize or antialiasing can create them, and SPB raises active
  values in this band to `16`. Use exact `0` on a verified path or use `16–255`.
- **16 = max active clearcoat** (most glossy/wet clearcoat).
- **17–255** = progressively less clearcoat; `255` has no clearcoat reflectivity.

So: when you want maximum active clearcoat, set CC = 16; when you want a weaker
coat, use higher values up to 255. Blue `255` is the raw-byte maximum but the
clearcoat-effect minimum.

## Implementation note

When generating spec maps in code (e.g. `spec_*.py`), preserve an intentional
exact `0` only when the selected export path supports it. Otherwise clamp active
clearcoat to **16–255**. Never leave accidental values in **1–15**. Also enforce
roughness `>=15` wherever metallic is `<240`; chrome-tier pixels (`M>=240`) may
legitimately use roughness below `15`.
