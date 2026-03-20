# Reference-Driven Procedural Patterns & Category Rehab

**Goal:** Get patterns that *feel* like your reference art (flames, tribal, etc.) by writing procedural code inspired by the image — not pixel-exact clones, but same style. Plus: rehab categories where many IDs share one texture so each choice actually looks different.

---

## What’s possible

### 1. Use your PNG as a **reference** (not as the runtime asset)

- You provide a PNG (e.g. a flame or tribal design you like).
- The agent **looks at it** (can read image files) and describes: direction of flow, curve shape, soft vs hard edges, layering, thickness variation, etc.
- The agent **writes or edits procedural code** (a new `texture_*` and optionally `paint_*` in the engine) that aims for that *style*: e.g. “upward sweeping bands, soft falloff, thick at bottom / thin at top” → `texture_flame_sweep` using gradients + noise + curvature.
- **Result:** A new pattern that renders like the other “good” procedurals (scale, rotate, intensity all work) and *approximates* the look of your reference. It will **not** be a pixel-perfect copy; it will be “in the spirit of” the art.

### 2. What we **can’t** do

- **Pixel-exact procedural clone** of an arbitrary PNG. That would require either (a) using the image itself at runtime (your current image pipeline), or (b) some form of image fitting / neural style, which we’re not doing.
- So: **reference-driven = style approximation in code**, not a 1:1 rebuild of every curve.

### 3. Blend of approaches

- **Reference-driven procedural:** “Here’s my ideal flame PNG” → new `texture_flame_*` that mimics that look; wire 2–3 pattern IDs to it so Classic Flames (or Tribal) get a distinct option.
- **Keep image-based where it helps:** We can still add your PNGs as image patterns and keep iterating on why they didn’t look right (tiling, scale, contrast, or pipeline tweaks).
- **Rehab by reducing aliases:** Many pattern IDs currently share the same `texture_fn`. We give some IDs their own (or a new shared) texture so “Flames” and “Tribal” aren’t all the same visual.

---

## Where the big aliasing is (rehab priorities)

**Flames (many share one texture):**  
These all use `texture_lava_flow` + `paint_lava_glow`:  
`blue_flame`, `classic_hotrod`, `fire_lick`, `fireball`, `flame_fade`, `hellfire`, `inferno`, `lava_flow`, `torch_burn`, `tribal_flame`, `wildfire`.

- So **tribal_flame** and **classic_hotrod** look the same under the hood. **Total rehab** for Flames = add 2–3 new texture variants (e.g. sweep, ribbon, sharp tongues) and spread the IDs across them.

**Tribal / ornamental (share celtic or damascus):**  
- `texture_celtic_knot`: `celtic_knot`, `fleur_de_lis`, `gothic_cross`, `hibiscus`, `iron_cross`, `norse_rune`, `retro_flower_power`, `tiki_totem`, `trophy_laurel`.  
- `texture_damascus`: `damascus`, `gothic_scroll`, `paisley`.

- Categories that need **a couple edits**: give 1–2 of these a dedicated texture (e.g. a more “tribal band” style for one ID).  
- **Total rehab**: new texture(s) for “tribal bands” / “scroll” and reassign several IDs.

**Ghost / plasma:**  
- `ghost_flames`, `fractal`, `plasma`, `power_aura`, etc. share `texture_plasma`.  
- Same idea: add a softer or more “flame wisp” variant and point `ghost_flames` (and maybe one other) at it.

---

## Suggested workflow

1. **Pick one reference per “style”**  
   - e.g. one PNG for “classic hot rod flame,” one for “tribal band.”
2. **Agent describes + proposes**  
   - “Your reference has: [description]. I’ll add `texture_flame_sweep` that does [brief spec] and wire `classic_hotrod` and `long_flame_sweep` to it.”
3. **You try it in the app**  
   - Render on a car; check scale/rotation/intensity.
4. **Iterate with words**  
   - “More vertical,” “softer edges,” “thicker bands” → agent tweaks the procedural (no new image needed).
5. **Rehab the category**  
   - Once 2–3 new texture variants exist, spread the flame (or tribal) IDs across them so each name has a distinct look.

---

## Summary

| You want | Approach |
|----------|----------|
| Pattern that *looks like* my PNG but renders like the good procedurals | Reference-driven: you give PNG → agent describes it and writes a procedural that approximates the *style* (not pixel-exact). |
| Exact pixel copy of my PNG | Use image-based pattern pipeline (and keep debugging why PNGs didn’t look right). |
| “Flames” / “Tribal” not all the same | Rehab: add new texture_* variants, point specific IDs to them so each category has 2–3 distinct looks. |
| One category needs only a couple changes | Identify the 1–2 IDs; give them a new or tuned texture; leave the rest as-is. |

The agent **cannot** generate or edit the image itself. It **can** look at your PNG and turn that into **procedural code** that mimics the feel, and it can **repoint** existing pattern IDs to new or tuned textures so your categories feel varied and closer to what you and your clients want.
