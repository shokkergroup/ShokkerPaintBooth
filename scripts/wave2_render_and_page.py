# -*- coding: utf-8 -*-
"""Render the REDESIGN WAVE 2 review swatches + build SPB_AUDIT_wave2.html.
Covers all 44 rebuilds: 29 PRIZM + 2 LFR finishes, 6 LFR patterns, 7 spec
overlays. Swatches render through the SAME pipeline as the live wiring
(1024 work grid -> upscale -> native finishing pass)."""
import os, sys, time, json
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import engine.expansions.redesign_wave2_2026 as W
from engine.color_science import feature_fineness, mip_survival
from spb_audit_page_builder import build_page

S, SW = 2048, 1024
OUT = os.path.join(ROOT, "thumbnails", "audit", "wave2")
os.makedirs(OUT, exist_ok=True)

INFO = {
 "prizm_adaptive": ("Prizm Adaptive", "finish", "Octopus camouflage: thousands of tiny skin plates that FLIP between two rival palettes by their own grain direction — the surface re-camouflages as you move. Dense papillae micro-bumps."),
 "prizm_alien_skin": ("Prizm Alien Skin", "finish", "Living exo-membrane GROWN by reaction-diffusion: glossy coral-labyrinth ridges over a violet pore-speckled membrane, bioluminescent cyan pulses along every crest."),
 "prizm_arctic": ("Prizm Arctic", "finish", "Pack-ice mosaic: ~2600 slim anisotropic ice shards with tight internal striations, frost ferns etched along every seam, trapped-air sparkle throughout."),
 "prizm_aurora_shift": ("Prizm Aurora Shift", "finish", "Aurora storm: thousands of sheared light strands with fine ray striations, rippling green-teal-magenta over a star-thick night sky."),
 "prizm_black_rainbow": ("Prizm Black Rainbow", "finish", "Obsidian depths cut by razor strange-attractor filigree burning in emissive spectrum colors; dense prismatic micro-flake keeps the black alive."),
 "prizm_blood_moon": ("Prizm Blood Moon", "finish", "Eclipsed regolith: a fully-cratered surface with sun-lit rims, fine ejecta dendrites, mineral glass-bead glints, umbral blood gradient crimson-amber."),
 "prizm_candy_paint": ("Prizm Candy Paint", "finish", "Kustom candy apple: deep Beer-Lambert crimson poured over a FULL engine-turned silver bed — scattered jittered guilloche rosettes + dense metal flake."),
 "prizm_chrome_rose": ("Prizm Chrome Rose", "finish", "Liquid rose-gold chrome: tight refraction-caustic mesh streaking across hammered poured metal, rose-champagne, hairline polish swirl."),
 "prizm_copper_flame": ("Prizm Copper Flame", "finish", "Engraved fire: banknote hatching whose line weight follows licking flame tongues — polished copper with teal heat-patina pooling in burnt valleys."),
 "prizm_cosmos": ("Prizm Cosmos", "finish", "A living galaxy: strange-attractor spiral arms of star-stuff, 30k pin-stars, rose/indigo nebula breathing between the arms."),
 "prizm_dark_matter": ("Prizm Dark Matter", "finish", "Gravitational lensing: a brilliant caustic light-web warped around pitch-black void lace, every void rimmed in violet Cherenkov glow."),
 "prizm_deep_space": ("Prizm Deep Space", "finish", "Long-exposure sky: 1500 concentric star-trail arcs sweeping around an unseen pole, gold/blue/white trails with hot heads over cosmic dust."),
 "prizm_duochrome": ("Prizm Duochrome", "finish", "True duochrome twill: a fine herringbone weave where every warp thread is teal and every weft magenta — the color flip IS the fabric."),
 "prizm_ember": ("Prizm Ember", "finish", "Dying campfire crust: charred plates split by a glowing crack network breathing orange-gold heat, spark streaks drifting off the hottest seams."),
 "prizm_fire_ice": ("Prizm Fire & Ice", "finish", "Two rivers interleaved: warm currents flowing one way, glacial the other, woven through alternating bands — frost sparkle where they touch."),
 "prizm_galaxy_dust": ("Prizm Galaxy Dust", "finish", "Golden-angle stardust: phyllotaxis spirals of micro-spangles at three nested scales, violet dust lanes drifting between the seed-spirals."),
 "prizm_holographic": ("Prizm Holographic", "finish", "Holo trading-foil: a mosaic of micro-prism tiles, each etched with a hairline diffraction grating at its own angle — every tile its own rainbow."),
 "prizm_iridescent": ("Prizm Iridescent", "finish", "Draining soap film: swirling fine thin-film bands with drain streaks and black film holes on a pale pearl base."),
 "prizm_midnight": ("Prizm Midnight", "finish", "Nocturne sea: deep indigo swells crossed by hairline moon-silver engraving that follows the water, rare glints riding the crests."),
 "prizm_mystichrome": ("Prizm Mystichrome", "finish", "Liquid color-travel chrome: teal-violet-magenta-gold sweep with molten metal flow-streaks combed along the travel gradient."),
 "prizm_neon": ("Prizm Neon", "finish", "Buzzing neon alley: dense glowing glass-tube script loops (white-hot cores, colored halos) over a dark micro-brick wall."),
 "prizm_oceanic": ("Prizm Oceanic", "finish", "Sunlit reef floor: true refraction caustics dancing over turquoise-abyss depth, micro-foam flecks riding the bright web."),
 "prizm_phoenix": ("Prizm Phoenix", "finish", "Rising firebird plumage: long arcing plume strands with fine barb hatching, ember roots burning to white-gold tips, spark dust."),
 "prizm_solar": ("Prizm Solar", "finish", "The photosphere: boiling granulation cells, crisp sunspot pores with penumbrae, white-hot magnetic loop arcs leaping between regions."),
 "prizm_spectrum": ("Prizm Spectrum", "finish", "Laser-etched spectrum guilloche: a dense scatter of fine jittered engine-turn rosettes, each refracting its own slice of the rainbow."),
 "prizm_sunset_strip": ("Prizm Sunset Strip", "finish", "Retro-chrome dusk: warm gradient sky swept by narrow mirror-chrome bands at scattered angles, micro scanline shimmer — 80s boulevard."),
 "prizm_titanium": ("Prizm Titanium", "finish", "Torch-anodized titanium: brushed metal grain blooming through the anodize spectrum (straw-bronze-violet-cobalt), grinder arcs biting in."),
 "prizm_toxic_waste": ("Prizm Toxic Waste", "finish", "Bubbling biohazard sludge: reaction-diffusion foam, rim-lit rising bubbles, acid drips cutting the crust — violent green on black."),
 "prizm_venom": ("Prizm Venom", "finish", "Serpent armor: brick-packed keeled diamond scales, iridescent green-black with venom-yellow lattice flashes, every keel catching light."),
 "lfr_old_glory_flux": ("Old Glory Flux", "finish", "The flag as pure energy: scarlet and bone current-ribbons streaming through a shared wind, weaving over/under, star-spangled indigo eddies."),
 "lfr_we_the_people": ("We The People", "finish", "The parchment itself: dense copperplate engraving flowing like handwriting, iron-gall ink on foxed vellum, gold illumination curls."),
 "lfr_bunting_scallop": ("Bunting Scallop", "pattern", "Layered bunting swags: overlapping scallop fans with fine pleat hatching and sagging cords, scattered at several angles."),
 "lfr_firework_radial": ("Firework Radial", "pattern", "Dense peony fireworks: full rings of drooping spark rays with dot terminals and strobe rings, sizes nested so the sky is FULL."),
 "lfr_ribbon_weave": ("Ribbon Weave", "pattern", "True over-under satin ribbon lattice: two interlaced ribbon families, each striped with a sheen line and edge shading."),
 "lfr_star_lattice": ("Star Lattice", "pattern", "Stars made of stars: 5-point outlines whose strokes are strings of micro-stars, at three nested scales — a constellation lattice."),
 "lfr_stencil_stars": ("Stencil Stars", "pattern", "Spray-stencil stars: crisp filled cutouts, overspray halo speckle, paint drips running off random edges."),
 "lfr_stripe_drift": ("Stripe Drift", "pattern", "Pinstriper's drift: fine parallel pinstripes flowing around invisible discs (potential flow) — stripes part and rejoin like water."),
 "spec_lfr_corridor_sheen": ("Corridor Sheen (spec)", "spec overlay", "Micro-pleated satin corridors: three independent angle families of FINE pleat banding; cross-grain satin; corridor pooling."),
 "spec_lfr_firework_radial": ("Firework Radial (spec)", "spec overlay", "Micro-burst glint field: dense radial spark spokes; signed smoke rings; afterglow pools around burst hearts."),
 "spec_lfr_sparkler_embers": ("Sparkler Embers (spec)", "spec overlay", "Sparkler in the dark: thousands of micro-star pins; crackle branch twigs; drifting ember decay pools."),
 "spec_lfr_starfield_scatter": ("Starfield Scatter (spec)", "spec overlay", "Deep night starfield, rebuilt FAST (old one hung): multi-magnitude stars with diffraction spikes; nebula grain; constellation corridors."),
 "spec_lfr_torch_flicker": ("Torch Flicker (spec)", "spec overlay", "Torch flame anisotropy: fine flame-tongue hatching licking one way; heat-shimmer ripple; torch pool glow."),
 "crackle_network": ("Crackle Network (spec)", "spec overlay", "Hierarchical crackle, rebuilt FAST (old one hung for minutes): two nested anisotropic crack webs + micro-twigs."),
 "spec_abalone_crack_inlay": ("Abalone Crack Inlay (spec)", "spec overlay", "Nacre shards with interference banding along each shard's grain, dark grout channels — rebuilt fast."),
}


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 22), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (7, bgr.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def ai_rating(paint, mip, fine):
    f = paint.mean(2); bands = 0.0
    for sg in (1.5, 6.0, 24.0):
        lo = cv2.GaussianBlur(f, (0, 0), sg); bands += min(float(np.abs(f - lo).mean()) / 0.04, 1.0); f = lo
    clip = float(((paint <= 0.002) | (paint >= 0.998)).mean())
    return int(np.clip(round(22 + bands * 12 + mip * 14 + fine * 22 - clip * 25), 1, 100))


def crop(a):
    return (np.clip(a[768:1280, 768:1280], 0, 1) * 255).astype(np.uint8)


meta = []
print("=== REDESIGN WAVE 2 (%d items) ===" % len(INFO))
for fid, (name, kind, desc) in INFO.items():
    t0 = time.perf_counter()
    if kind == "finish":
        pf, sf = W.DESIGNS[fid]
        paint = np.clip(pf(SW, SW, 42), 0, 1).astype(np.float32)
        M, R, Cc = sf(SW, SW, 42)
        spec = np.clip(np.stack([M, R, Cc], -1) / 255.0, 0, 1).astype(np.float32)
        paint = cv2.resize(paint, (S, S), interpolation=cv2.INTER_LINEAR)
        paint = W._native_finish(paint, 42)
        spec = cv2.resize(spec, (S, S), interpolation=cv2.INTER_LINEAR)
    elif kind == "pattern":
        tex = np.asarray(W._W2_PAT_TEX[fid](S, S, 42), np.float32)
        lo, hi = W._W2_PAT_COLOR[fid]
        metal = lo[None, None, :] + (hi - lo)[None, None, :] * tex[..., None]
        base = np.full((S, S, 3), 0.5, np.float32)
        paint = base * (1 - tex[..., None]) + metal * tex[..., None]
        spec = np.clip(np.stack([20 + 230 * tex, 180 - 120 * tex, 30 + 130 * tex], -1) / 255.0, 0, 1)
    else:
        out = np.asarray(W.W2_SPEC_OVERLAYS[fid]((S, S), 42, 1.0), np.float32)
        spec = np.clip(out, 0, 1)
        paint = spec * np.float32([1.0, 1.0, 1.0])[None, None, :]   # overlays ARE the artifact
    dt = time.perf_counter() - t0
    fin = feature_fineness(paint, full_size=S); mip = mip_survival(paint)
    g = paint.mean(2)
    hf = np.abs(g - cv2.GaussianBlur(g, (0, 0), 4.0))
    cov = float((hf > 0.012).mean())
    ai = ai_rating(paint, mip, fin.get("fine_fraction", 0.5))
    print("%-28s ai%3d cov %.2f char %5.1f  %.2fs" % (fid, ai, cov, fin["char_px"], dt))
    left_lbl = "canvas design (1:1 crop of 2048)" if kind != "spec overlay" else "overlay as RGB (R=M G=R B=Cc)"
    img = np.hstack([label(cv2.cvtColor(crop(paint), cv2.COLOR_RGB2BGR), left_lbl),
                     np.full((512, 4, 3), 24, np.uint8),
                     label(cv2.cvtColor(crop(spec), cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc")])
    cv2.imwrite(os.path.join(OUT, fid + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    meta.append({"id": fid, "name": name, "kind": kind, "desc": desc,
                 "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})

json.dump(meta, open(os.path.join(ROOT, "scripts", "wave2_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE = ('<span class="flag">\U0001F30A REDESIGN WAVE 2 — the full rollout</span> '
         '<span style="color:var(--dim);font-weight:400">(29 PRIZM + 2 LFR finishes, 6 LFR patterns, 7 spec overlays)</span>')
SUB = ("Everything still busted, rebuilt from the drawing board with NEW art engines: strange attractors, "
       "reaction-diffusion growth, photon caustics, flow-field advection, harmonograph guilloche, anisotropic "
       "crystal growth, banknote engraving, branching dendrites. Every design is wired LIVE — assign it in the "
       "booth and judge it on the car. LEFT = canvas (1:1 crop of 2048), RIGHT = married spec "
       "(red=metallic, green=roughness, blue=clearcoat). The 48 spec overlays you rated REMOVE are gone from the catalog. "
       "<b>SUBMIT THIS ONE</b> saves a card.")

build_page("wave2", TITLE, SUB, meta, OUT, os.path.join(ROOT, "SPB_AUDIT_wave2.html"), accent="#7ce8ff")
print("WROTE SPB_AUDIT_wave2.html (%d cards)" % len(meta))
