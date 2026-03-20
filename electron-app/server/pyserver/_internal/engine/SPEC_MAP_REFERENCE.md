# Spec Map Channel Reference (iRacing-compatible PBR)

When generating or authoring spec maps (M, R, CC), use these ranges. Output is 0–255 per channel; the renderer/iRacing uses them as follows.

## Channels

| Channel | Role | 0 | 255 |
|--------|------|---|-----|
| **Red (M)** | **Metallic** | Non-metallic (dielectric), dark | Very metallic, chrome-like |
| **Green (R)** | **Roughness** | Smooth, glossy, shiny (strong reflection) | Rough, matte (weak reflection) |
| **Blue (CC)** | **Clearcoat** | — | — |

## Clearcoat (blue) — important

- **16 = max clearcoat** (most glossy/wet clearcoat).
- **17–255** = progressively less clearcoat (more dull).
- **Do not use 0–15.** In iRacing (and for consistency here), 0–15 can behave as dull or legacy; always output clearcoat in **16–255** only.

So: when you want “maximum clearcoat”, set CC = 16; when you want duller, use higher values up to 255.

## Implementation note

When generating spec maps in code (e.g. `spec_*.py`), **clamp CC to 16–255** so we never output 0–15 for clearcoat.
