# Tutorial 5 — Spec Map Mastery

**Estimated time:** 12 minutes
**Prerequisites:** [Tutorial 4 — Finishes Deep Dive](04_finishes_deep_dive.md). Tutorial 3 (Zones) is also required.
**Skill level:** Intermediate to advanced. The most technical tutorial in the series, but worth every minute.

A spec map is the second image SPB exports alongside your color paint. It's invisible in the live preview by default, and most users never look at it. But the spec map is the difference between a paint that looks like cardboard and a paint that looks like a real car. Spend twelve minutes here and you'll never have a "why does my chrome look like gray plastic" question again.

## What you'll learn

- What a spec map is, in plain English
- The four channels (R, G, B, A) and what each one means
- The Iron Rules — the small list of "always" and "never" that prevent broken paint
- The inverted clearcoat gotcha (this trips up everyone)
- How to use the channel inspector to debug spec maps

---

## Step 1 — What's a spec map?

When you hit RENDER, SPB writes two files:

- `car_<id>.tga` — the **color paint**. Tells the renderer what color each pixel is.
- `car_spec_<id>.tga` — the **spec map**. Tells the renderer what *material* each pixel is.

Color is the hue. Spec is the feel. Same red color can be glossy candy, matte rally, mirror chrome, or dusty primer — and the only difference between those four is the spec map.

iRacing (and most modern games) use a Physically Based Rendering (PBR) pipeline that combines both textures with the camera position and the world lighting to produce the final pixel you see. Without a correct spec map, the renderer doesn't know how the surface should respond to light, and your paint looks wrong even when the color is perfect.

## Step 2 — The four channels

A spec map is a regular image with four 8-bit channels: R, G, B, A. Each channel encodes one material property:

| Channel | Property | 0 means | 255 means |
|---|---|---|---|
| **R** | Metallic | Dielectric (paint, plastic) | Pure metal (chrome, steel) |
| **G** | Roughness | Mirror smooth | Diffused/matte |
| **B** | Clearcoat | Max gloss (yes, really — see Step 4) | No clearcoat / dull |
| **A** | Specular Mask | Special-case override | Default behavior |

Yes, blue being **inverted** is weird. Yes, every newcomer trips on it. Step 4 has the full story.

## Step 3 — Iron Rules

These are the "always" and "never" rules. Memorize them.

**Always:**
- Match metallic + clearcoat sensibly. Chrome (R=255) should have B near 16 (max gloss), not 200.
- Use SPB's bases — they encode correct R/G/B for you. The picker is a shortcut for not having to think about this.
- Sanity-check by rendering and looking under a moving light. If the surface "doesn't move" with the camera, the spec map is wrong.

**Never:**
- Crank G (roughness) to 255 expecting "more shine." That's backwards. 255 is *more matte*.
- Set B to 255 thinking "max clearcoat." That's *no clearcoat*. (See Step 4.)
- Hand-paint spec maps in Photoshop without reference. Use SPB's bases or copy from `SPB_SPEC_MAP_GUIDE.md`.

If you only remember one Iron Rule, make it: **B is inverted. 16 = max gloss. 255 = dull.**

## Step 4 — The inverted clearcoat gotcha

This is so important it gets its own step.

Clearcoat is the glossy clear layer over automotive paint. More clearcoat = more gloss. Intuitively, you'd expect a 0-255 channel where 0 = none and 255 = max. iRacing did the opposite.

**B = 0 to 15:** No clearcoat (dull, no glassy reflection on top).
**B = 16:** **Maximum clearcoat / gloss.** This is the "deep show-car wet-look" value.
**B = 17 to 255:** Clearcoat fades back out, with 255 being effectively no clearcoat at all.

Yes, this means the *one specific value of 16* is the sweet spot for max gloss. SPB encodes this correctly under the hood — when you pick a glossy base, the spec map's B channel gets 16, not 255. But if you're ever editing a spec map by hand, this is the gotcha that will eat your day.

Reference values for the canonical materials (from `SPB_SPEC_MAP_GUIDE.md`):

| Material | R | G | B |
|---|---|---|---|
| Chrome mirror | 255 | 0 | 16 |
| Glossy paint | 0 | 30 | 16 |
| Metallic paint | 200 | 60 | 16 |
| Satin | 0 | 130 | 100 |
| Matte | 0 | 220 | 15 |
| Carbon weave | 50 | 100 | 16 |

## Step 5 — The channel inspector

SPB has a built-in tool for visually debugging spec maps. Open it from `View → Channel Inspector` (or `Ctrl+Shift+I`).

![Step 5 — Channel inspector open](docs/img/tutorial-05-step5.png)

You get four small thumbnails — one per channel — showing the spec map decomposed. Hover any pixel on the main canvas and the inspector shows the R/G/B/A values at that exact location.

This is gold for debugging:

- "Why does this part look matte?" → Check G. If it's high (200+), there's your answer.
- "Why isn't my chrome reflecting?" → Check R. If it's not 255, it isn't fully metallic.
- "Why does it look dusty everywhere?" → Check B. If it's high (200+), clearcoat is suppressed.

Spend a minute exploring the inspector with different finishes applied. You'll start to develop intuition for what "good spec" looks like in each channel.

## Step 6 — A is rarely used

The alpha channel (specular mask) is technically supported but rarely used. iRacing's renderer treats A=255 as "use the spec map normally" and A<255 as "fade the spec effect by this amount." Most SPB finishes leave A at 255.

If you're not building unusual cosmetic effects, you can ignore A entirely. SPB doesn't currently expose a UI for editing A directly — and that's fine, because in production work it almost never matters.

---

## Try it yourself

Build a side-by-side comparison that drives the lessons home:

1. Add **Zone 1**: cover the front half of the truck (use a layer-locked zone for the Hood + Front Doors layers). Set color to silver (`#C0C0C0`). Pick base **chrome_mirror**.
2. Add **Zone 2**: cover the back half of the truck (Bed + Rear Doors layers). Set color to silver (`#C0C0C0`) — same color! Pick base **matte_clean**.
3. RENDER.

In iRacing (or in the Live Preview if you're not running the sim), the front half should look like polished chrome. The back half should look like matte-painted aluminum. **Same color hex code. Different spec maps. Totally different material.**

Now open the channel inspector. Hover the chrome half — you should see R near 255, G near 0, B at 16. Hover the matte half — R near 0, G near 220, B at 15. Two different materials, encoded in three numbers.

You now understand spec maps better than 90% of liveries on the internet.

---

## Troubleshooting

**My chrome looks like gray plastic.** B is wrong. Open the channel inspector, hover the chrome region. If B is anywhere except near 16, the chrome base wasn't applied correctly. Re-pick **chrome_mirror** and re-render.

**My matte black looks too glossy.** B is too low. Pick **matte_clean** explicitly — don't try to "fake matte" with a low-saturation gloss.

**Channel inspector shows the right values but in-sim looks wrong.** iRacing has its own track lighting that can dramatically change perceived material. Test in multiple tracks — daytime Daytona is a different look than night Bristol.

**The spec map looks "noisy" or speckled.** That's pattern overlay (carbon weave, scales, etc.) bleeding into spec. This is correct — patterns intentionally vary the spec to look realistic. If you don't want it, drop the pattern strength.

**I want a custom material that no SPB base provides.** Use **PD Liquid Metal** as a base, then mix in a spec pattern overlay (Tutorial 4). For truly unusual materials, edit the spec map TGA in Photoshop after export — but use the channel inspector to set your reference values first.

---

## Next up

[Tutorial 6 — Sponsor Placement](06_sponsor_placement.md). Enough technical theory. Next we get back to making things pretty — placing sponsor logos, mirror-cloning them across the truck, and dressing them up with stroke and drop shadow.
