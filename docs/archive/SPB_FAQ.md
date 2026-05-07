# Shokker Paint Booth — Frequently Asked Questions

> If you can't find your answer here, check the full [SPB_GUIDE.md](SPB_GUIDE.md) or hop into our Discord.

---

## Installation & Setup

### Q: Does SPB work on Mac or Linux?
**A:** No — Windows only. iRacing itself is Windows-only, so building cross-platform doesn't move the needle. We won't be supporting other OSes.

### Q: Do I need a powerful PC?
**A:** Recommended specs match iRacing's: any modern quad-core CPU, 16 GB RAM, a discrete GPU. SPB renders on the CPU (with optional GPU acceleration), so a fast multi-core CPU helps the most. SSD strongly recommended for fast paint loading.

### Q: Why does Windows SmartScreen warn me when installing?
**A:** The Gold-to-Platinum experimental build is unsigned. Click **More info → Run anyway**. Stable releases will be code-signed.

### Q: Where does SPB store its data?
**A:** Local app data folder under your Windows user profile. Renders go to your iRacing paints folder via Live Link.

---

## Loading Paint

### Q: Why won't my paint load?
**A:** Three usual suspects: (1) the file path has special characters or is on a network drive — try copying it to your local Documents folder first. (2) The file is open in Photoshop with a write lock — close it. (3) The format isn't PSD/TGA/PNG — convert it.

### Q: What file format should I use?
**A:** **PSD** if you can. PSD preserves your layer tree, which lets SPB do layer-restricted zones cleanly. TGA and PNG work but are flat — every zone has to use color matching only.

### Q: What paint dimensions are supported?
**A:** **2048×2048** is the iRacing standard and works fastest. SPB will load larger paints (4096×4096, 8192×8192) but rendering is slower and memory use is higher. Smaller paints (1024×1024) load instantly.

### Q: Can I import from Trading Paints?
**A:** Not directly — Trading Paints uses its own preset format. But if you have your **PSD source file**, drop that into SPB and you're good.

### Q: My PSD has 200 layers. Will SPB handle it?
**A:** Yes, but Live Preview will slow as you stack layer effects. Group similar layers and merge non-editable ones if you can.

### Q: Where should I save my paint files?
**A:** Anywhere. Many users put them in their iRacing paints folder for tidiness. SPB remembers your last-loaded paint across launches.

---

## Zones & Finishes

### Q: Why is my number still yellow when I assigned a finish?
**A:** You set the **color match** but not the **finish**. Open the zone, scroll down to the Finish picker, and click a base or monolithic. Color match alone tells SPB *what* to paint, not *how*.

### Q: Why does a stripe bleed through into another region?
**A:** The stripe layer needs its own zone with **layer restriction** turned on. Without restriction, the zone hits any pixel matching the color, regardless of which layer it's on.

### Q: What's the difference between a Base and a Pattern?
**A:** A **Base** is the foundation material (the paint itself — gloss, matte, chrome, anodized, etc.). A **Pattern** is a texture overlay on top (carbon weave, plaid, hex). Every zone has one base; patterns are optional.

### Q: What's the difference between a Base and a Monolithic finish?
**A:** A **Base** is one ingredient. A **Monolithic** (COLORSHOXX, MORTAL SHOKK, PARADIGM) bundles base + pattern + spec settings into one premium finish. Pick a monolithic when you want the full look in one click.

### Q: Can a single zone have multiple colors?
**A:** Yes. Click `+ Add Color` inside the zone to add another color match. Useful for multi-color sponsor regions.

### Q: Can a zone use multiple finishes?
**A:** No, one finish per zone. If you need two finishes in overlapping pixels, make two zones and order them by priority.

### Q: How do I make Zone 1 win over Zone 2?
**A:** Drag Zone 1 above Zone 2 in the zone panel. Top of stack = highest priority.

### Q: What does "Remaining" do?
**A:** Paints any pixel not already claimed by a higher-priority zone. Perfect for "fill the rest with body color."

### Q: What does "Everything" do?
**A:** Paints the entire canvas. Usually you put it at the bottom of your stack as a fallback layer.

---

## Layers

### Q: How do I make a layer transparent?
**A:** Click the eye icon to hide it entirely, or drag the **Opacity slider** in the layer row.

### Q: What's the difference between selecting a layer and restricting a zone to a layer?
**A:** Selecting (right panel) controls where your **drawing tools** paint. Restricting (zone settings) controls where the **finish engine** paints. They are independent. Use the gold **🔒 Lock Active Zone to This Layer** button to set both at once.

### Q: Can I rename a layer?
**A:** Yes — double-click the layer name in the right panel.

### Q: Can I add a new layer?
**A:** Yes, right-click in the layer panel and choose `+ New Layer`.

### Q: How do I duplicate a layer?
**A:** Right-click the layer → Duplicate. Or use Mirror Clone for symmetric duplicates.

---

## Tools & Editing

### Q: How do I undo?
**A:** `Ctrl+Z`. `Ctrl+Shift+Z` (or `Ctrl+Y`) to redo. Note: undo history does **not** survive app restart, so save a `.shokker` preset at major milestones.

### Q: How big is the undo stack?
**A:** Currently unbounded — keep an eye on memory if you do thousands of strokes between saves.

### Q: Can I customize keyboard shortcuts?
**A:** Not yet. We have a request open for a key remap UI; vote for it on Discord.

### Q: How do I rotate the canvas view?
**A:** Use the **View → Rotate** tool, or just rotate the paint with `View → Rotate 90° CW`.

### Q: Can I use a drawing tablet?
**A:** Yes — pen pressure is supported on the brush tools.

---

## Rendering & Live Preview

### Q: Why is the Live Preview blank?
**A:** Three causes: (1) no zones added yet, (2) no paint loaded, (3) the render server crashed — restart SPB.

### Q: How do I refresh Live Preview?
**A:** Press `F5` or click the 🔄 button in the preview header.

### Q: Why does the preview look slightly different from in-sim?
**A:** iRacing uses real-time GI and track lighting that SPB can't fully replicate in a static preview. Spec map and color values are accurate; lighting context isn't.

### Q: Where are my rendered files saved?
**A:** Your iRacing paints folder. For the demo Silverado, that's `Documents\iRacing\paint\trucks\silverado2019\car_<custid>.tga`. Other cars go to their respective car folders.

### Q: Can I preview in iRacing without restarting the sim?
**A:** Yes. Render in SPB, then switch to iRacing's Paint screen and reload the car. The new TGA picks up immediately.

### Q: Render takes forever — why?
**A:** Large paint dimensions (4K+), heavy layer effects, or many zones. Reduce to 2048×2048 if you don't need higher res.

---

## Saving & Sharing

### Q: Does SPB auto-save?
**A:** Yes, every change you make is persisted to local state. Your last-loaded paint also auto-restores on launch.

### Q: Can I share my preset with friends?
**A:** Yes — click **Save SHOKK**. It writes a `.shokker` file containing your zones, finishes, and layer effects. Send it to a friend, they drop it into SPB.

### Q: What's the difference between Export Config and Save SHOKK?
**A:** Export Config writes a smaller `.json` with just zones + finishes (no layer effects, no embedded thumbnails). Save SHOKK is the full preset bundle.

### Q: Can I export to PNG/JPG instead of TGA?
**A:** Render output is iRacing-format TGA by default (that's what the sim wants). Use a third-party converter if you need a JPG for social media.

---

## Spec Maps & PBR

### Q: How do spec maps work?
**A:** The spec map is a separate file iRacing reads alongside your color paint. Its RGB channels encode metallic-ness (R), roughness (G), and clearcoat (B). SPB writes this for you based on your zone finishes.

### Q: What's the iRacing spec map naming convention?
**A:** `car_spec_<custid>.tga` for most cars. Some newer cars also use `car_metallic_<custid>.tga` for a separate metallic layer. SPB handles the naming.

### Q: What's PBR?
**A:** Physically Based Rendering. A lighting model that simulates how real materials reflect light. iRacing uses PBR, so the spec map is what makes a chrome bumper look like chrome instead of a flat grey paint.

### Q: Why is the B channel inverted?
**A:** iRacing convention. Lower B value = more clearcoat gloss. `B=16` is max gloss, `B=255` is no clearcoat. We didn't pick it; we just respect it.

### Q: Can I edit the spec map manually?
**A:** Yes — open the rendered TGA in any image editor. But almost always it's faster to tweak your zone's Custom Spec settings in SPB and re-render.

---

## Performance

### Q: Why does the app feel sluggish?
**A:** Common causes: (1) too many active zones (50+), (2) heavy layer effects on many layers, (3) Live Preview at high resolution, (4) too-large paint dims. Try `F5` to refresh the preview, close other apps, and consider downsizing your paint.

### Q: Live Preview keeps lagging behind my edits.
**A:** The preview polls the render server. If your machine is busy, it falls behind. Press `F5` to force a fresh render.

### Q: Can I disable Live Preview?
**A:** Yes — `View → Toggle Live Preview`. Useful when doing heavy pixel-level edits where you don't need feedback every stroke.

---

## General

### Q: How do I report a bug?
**A:** Discord (QR code in the install folder), or email the support address in the About dialog. Include: SPB version (Help → About), what you did, what you expected, what happened, and the contents of `server_log.txt` if available.

### Q: How often does SPB update?
**A:** Frequently. We're in the Gold-to-Platinum experimental phase, with multiple releases per month. Check the in-app changelog or `CHANGELOG.md` in the install folder.

### Q: Is there a free version?
**A:** SPB is a paid product, but the install includes a sandbox mode with the demo Silverado so you can try the full feature set before committing.

### Q: Can I use SPB commercially (e.g. for a sim racing team)?
**A:** Yes. Renders are yours to keep and use however you like.

### Q: Will SPB work with future iRacing cars?
**A:** Yes — SPB reads any PSD/TGA at iRacing's standard dimensions. New cars work as soon as you have their paint kit.

### Q: Does SPB do helmet or suit paints?
**A:** Yes — same workflow. Drop in the helmet paint kit, build zones, render. Files go to the appropriate iRacing paints subfolder.

### Q: Can I paint multiple cars in one session?
**A:** One paint loaded at a time. Use Save SHOKK to save your work, then load the next car's paint.

### Q: Where can I see what other people have painted?
**A:** Discord community channel and the showcase page on the Shokker website.

---

If your question isn't answered here, drop it in Discord — we update this doc regularly with new questions.
