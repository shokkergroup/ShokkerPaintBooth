# SPB iRacing Integration Guide

Shokker Paint Booth is built to be the best paint authoring tool for iRacing. This guide covers everything an iRacing user needs to know about how SPB exports paints, where iRacing looks for them, what filename conventions to follow, and how to verify a paint is rendering correctly in-sim.

## 1. How SPB Integrates with iRacing

SPB is a standalone authoring tool. It does not modify iRacing's installation, does not hook into iRacing's process, and does not require iRacing to be running. Integration happens at one specific point: when you export (or auto-export via Live Link), SPB writes one or more TGA files to your iRacing custom paint folder. iRacing picks them up the next time it scans the folder — typically when you next launch a session.

This is the same workflow the in-game paint kit uses, and the same workflow Trading Paints, paint shop tools, and direct-from-Photoshop authors use. SPB does not require a special plugin in iRacing — if iRacing can see the files, it will load them.

## 2. iRacing File System Overview

By default, iRacing stores user-generated content under your Documents folder:

```
%USERPROFILE%\Documents\iRacing\
```

Inside that folder, the relevant subdirectories are:

- `paint\` — car paint files. Subfolders here are per-car-model (e.g. `paint\porsche911cup\`, `paint\stockcars2_chevyss\`).
- `helmets\` — driver helmet files. Single flat folder for all helmets.
- `suits\` — driver suit files. Single flat folder for all suits.
- `replays\`, `setups\`, `screenshots\` — unrelated to painting but commonly seen alongside.

iRacing scans these folders at session-load time. New files are picked up next session; replacing an existing file requires restarting any running session.

## 3. Custom Paint Folder Location

The default location is:

```
%USERPROFILE%\Documents\iRacing\
```

If you've moved your iRacing documents folder (some users put it on a faster SSD), the custom paint folders are wherever you redirected the parent Documents\iRacing path. SPB's settings panel has an "iRacing Folder" picker that points to whatever path you choose — the Live Link feature uses this path to know where to drop files.

If you maintain multiple iRacing accounts on the same machine, you can point SPB at a different per-account folder for each profile. The folder structure inside is identical regardless of account.

## 4. Car / Trucks / Open-Wheelers Folder Differences

All car paints live under `paint\<car_folder>\`, but the per-car folder names differ:

- **Stock cars** — `stockcars2_chevyss`, `stockcars2_fordmustang`, `stockcars2_toyotacamry`, etc.
- **Trucks** — `truck2022_silverado`, `truck2022_tundra`, etc.
- **Formula / open-wheelers** — `dallaraf3`, `formularenault35`, `superformulasf23`, etc.
- **Sports cars / GT** — `audir8gt3`, `mercedesamggt3`, `ferrari296gt3`, etc.

iRacing's UI does not show these folder names — it shows car names. SPB maintains an internal mapping of car-display-name → folder-name and writes to the correct folder automatically. You don't need to know the folder names, but if you're troubleshooting, knowing where iRacing actually looks is essential.

## 5. Filename Conventions

iRacing's filename rules are strict and case-sensitive in some places:

### Car paint
- `car_<iracing_id>.tga` — diffuse paint
- `car_spec_<iracing_id>.tga` — spec map (mandatory in modern iRacing)
- `car_num_<iracing_id>.tga` — optional custom car number layer

### Custom car number config
- `car_num_<iracing_id>.txt` (or `.psd` for Photoshop sources) — controls number font, color, and placement when iRacing renders the car number on top of the paint

### Helmet
- `helmet_<iracing_id>.tga`
- `helmet_spec_<iracing_id>.tga`

### Suit
- `suit_<iracing_id>.tga`
- `suit_spec_<iracing_id>.tga`

`<iracing_id>` is your iRacing customer ID (a number). SPB's exporter pulls this from your saved profile so you don't have to type it every export. For special-use exports (sharing with another driver), SPB lets you override the ID at export time.

## 6. Spec Map Mandatory Rules in iRacing

Modern iRacing (since the PBR shader migration) requires a spec map for every paint. If you skip it, the car will render with default plastic shine — usually wrong for whatever finish you intended. SPB exports the spec map automatically alongside the diffuse, but if you import an external paint that lacks a spec, you should immediately author one in SPB before going on track.

The spec map channel meaning:

- **R = Metallic** — 0 is fully dielectric (paint, plastic), 255 is fully metallic (chrome, raw aluminum).
- **G = Roughness** — 0 is mirror-smooth, 255 is fully matte.
- **B = Clearcoat** — *inverted* — 0–15 means no clearcoat, 16 means maximum gloss clearcoat, 255 means dull / no clearcoat. This is the most-confused field in iRacing painting.
- **A = Specular Mask** — rarely used; safe to leave fully opaque.

Common values:

- Glossy show-car paint: R=0, G=85, B=16
- Satin / matte: R=0, G=200, B=200
- Chrome: R=255, G=0, B=16
- Brushed metal: R=200, G=120, B=80

SPB exposes these as friendly finish presets — you don't normally need to set raw RGB values, but knowing the math helps when you're troubleshooting why a paint looks wrong in-sim.

## 7. Live Preview vs In-Game Appearance

SPB's preview uses a representative skybox and PBR shader to approximate iRacing's lighting. It is close, but not identical, because iRacing applies:

- **Tone mapping** — a global contrast / saturation curve that varies slightly per track.
- **Per-track skybox / sun position** — a paint that looks great at Daytona may look slightly different at Spa.
- **HDR exposure** — bright sunlight blows out highlights more aggressively in iRacing than in the booth.
- **Anti-aliasing and texture filtering** — iRacing's MSAA settings smooth things differently than SPB's preview.

For critical paints, do a test session in iRacing before publishing. SPB's "iRacing lighting" preview toggle gets within ~90% of in-sim appearance, which is enough for normal authoring but not enough for final checks.

## 8. Color Space Differences (iRacing's Tone Mapping)

iRacing's tone mapping desaturates colors slightly compared to a flat sRGB preview. Practical adjustments:

- **Vivid reds/oranges** look about 10% less saturated in-sim. Push them slightly past where they look right in the booth.
- **Deep blues** can look slightly purple under certain track lighting.
- **Pure whites** stay bright but lose some of the "punch" they have in the booth.
- **Pure blacks** crush — detail in dark zones can disappear. Raise dark zones a few points if you want detail to stay readable.

These are tendencies, not absolutes. The single best calibration is to export your paint, load it at your home track, and compare. SPB's "calibration mode" lets you save per-track tone curves to push your in-booth preview closer to a specific track's in-sim look.

## 9. Trading Paints Integration (Separate Platform)

[Trading Paints](https://www.tradingpaints.com) is a third-party paint distribution platform. It works with iRacing by installing a small uploader/downloader that watches the iRacing custom paint folder. Drivers upload paints; other users with Trading Paints installed automatically download paints when they enter sessions with those cars.

SPB does not directly integrate with Trading Paints, but SPB-exported paints work with Trading Paints out of the box because they follow iRacing's filename conventions. To share an SPB paint via Trading Paints:

1. Export the paint from SPB to your iRacing custom paint folder (or use Live Link).
2. Open Trading Paints.
3. Upload the paint via the Trading Paints UI — it will pick up both the diffuse and the spec from the iRacing folder.
4. Tag the paint, add a description, publish.

Note that Trading Paints expects helmet and suit files at the standard iRacing paths too — anything SPB exports will be picked up correctly.

## 10. Custom Car Number Config (.psd vs .tga)

iRacing renders car numbers in two ways:

- **Default** — iRacing draws the car number on top of the paint at runtime, using a default font, color, and placement.
- **Custom number layer** — you provide `car_num_<iracing_id>.tga` (a transparent number layer) and `car_num_<iracing_id>.txt` (font/color/placement config). iRacing composites your number layer onto the paint at runtime.

The `.txt` config file controls font, color, outline, and placement. SPB's number-style picker writes this file automatically when you customize the number. The `.psd` variant is supported by iRacing's official paint kit but rarely used by external tools — SPB sticks with `.tga + .txt`.

## 11. iRacing UI Showing Custom Paints

In iRacing, custom paints appear in:

- **Car selection** — your custom paint shows on your car preview.
- **Garage** — full preview before going on track.
- **In-sim** — your car renders with your paint (and other drivers see it if they have your paint downloaded via Trading Paints, or if they've manually copied your TGA).
- **Spectator/replay** — custom paints render correctly in replays and broadcasts.

iRacing's UI does *not* explicitly tell you "custom paint loaded successfully." If your paint shows up in the car preview, it loaded correctly. If you see the default scheme, iRacing didn't find your file — usually a filename or folder mismatch.

## 12. Backup and Sharing Paints

Best practice for long-term paint management:

1. **Keep SPB project files** — these preserve zone settings, pattern choices, and the original palette. If you only have the TGA, you can re-edit the diffuse but not the underlying zone structure.
2. **Back up the iRacing custom paint folders** — copy `Documents\iRacing\paint`, `helmets`, `suits` to a backup drive periodically. Reinstalling iRacing or moving machines is otherwise painful.
3. **Share both diffuse and spec** — sharing only the diffuse loses the spec map and the receiver's car will render with wrong shine.
4. **Use SPB's pack export** — packages a complete kit (car + helmet + suit) into a single ZIP with all six TGAs and a manifest, ready to send to a teammate or upload to a sharing platform.

## 13. Verification Checklist

Before declaring a paint "done":

- [ ] Diffuse exported to correct car folder.
- [ ] Spec map exported alongside diffuse.
- [ ] Filename matches `<asset>_<iracing_id>.tga` exactly.
- [ ] Loaded a test session — paint shows on car preview.
- [ ] Drove a lap — colors look right under track lighting.
- [ ] Checked replay camera — paint reads from broadcast distance.
- [ ] Checked spec — chrome zones reflect, matte zones stay matte.
- [ ] Helmet and suit (if part of a kit) also load and look coordinated.
- [ ] (Optional) Uploaded to Trading Paints for the rest of the league to see.

If every box checks, the paint is ready to publish.
