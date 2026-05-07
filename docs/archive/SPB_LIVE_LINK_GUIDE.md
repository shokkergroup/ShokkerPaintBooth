# SPB Live Link Guide

Live Link is Shokker Paint Booth's auto-export workflow. Once enabled, every render of your paint, helmet, or suit is written directly to your iRacing custom paint folder using the correct filename and folder layout — no manual save, no manual copy, no chance of dropping a file in the wrong place. This guide covers everything: what Live Link is, how to set it up, how to use it across multiple cars, how to verify it's working, and how to recover when something goes wrong.

## 1. What Live Link Is

Live Link is a SPB feature that:

1. Watches for completed renders in the booth (paint export, helmet export, suit export).
2. Writes the resulting TGA(s) — both diffuse and spec — directly to your iRacing custom paint folder.
3. Uses iRacing's expected filename convention (`car_<id>.tga`, `helmet_<id>.tga`, `suit_<id>.tga`, plus their `_spec_` companions).
4. Overwrites any existing file at that path.

Live Link does not modify iRacing or hook into the running iRacing process. It is purely a file-write convenience that puts files where iRacing expects them. iRacing picks up the new files the next time it scans the folder — typically the next time you load a session or a garage view.

## 2. How to Enable It

Live Link is controlled from SPB's settings panel:

1. Open **Settings** (gear icon, top right).
2. Open the **iRacing Integration** section.
3. Click **Choose Folder** and point at your iRacing user folder. The default is:
   ```
   %USERPROFILE%\Documents\iRacing\
   ```
   If you've redirected your iRacing documents folder, point at the redirected path.
4. SPB validates the folder by checking that `paint\`, `helmets\`, and `suits\` subfolders exist (or can be created).
5. Toggle **Live Link** to **On**.
6. Set your **iRacing Customer ID** in the field below — this is the number used in `<iracing_id>` filename slots.
7. Save.

Once Live Link is on, every export from the booth (Ctrl+E or "Export" button) writes both to SPB's local export folder *and* to the iRacing folder.

## 3. iRacing Folder Configuration

SPB needs read+write access to:

- `<iracing_root>\paint\<car_folder>\` — for car paints (the per-car folder is created automatically if missing).
- `<iracing_root>\helmets\` — for helmet files.
- `<iracing_root>\suits\` — for suit files.

If any of these folders don't exist, SPB creates them on first export. If SPB can't create the folders (permissions issue, read-only drive), Live Link will surface an error and disable itself rather than silently failing.

For users who maintain multiple iRacing accounts on the same machine, you can save multiple Live Link configurations (one per profile) and switch between them using the profile dropdown in the settings panel.

## 4. Auto-Copy on Render

When Live Link is enabled, every "Export" action triggers:

1. SPB renders the diffuse texture to its own export folder.
2. SPB renders the spec map alongside.
3. SPB copies both files into the iRacing folder, using the correct filename pattern.
4. (Optional) SPB shows a toast confirming the export ("Paint dropped to iRacing folder").

The copy is atomic — SPB writes to a temp file then renames, so iRacing never sees a half-written file even if you trigger an export while iRacing is reading the folder.

## 5. File Naming and Overwriting

Live Link uses iRacing's exact filename conventions:

- Car: `car_<iracing_id>.tga` and `car_spec_<iracing_id>.tga`
- Helmet: `helmet_<iracing_id>.tga` and `helmet_spec_<iracing_id>.tga`
- Suit: `suit_<iracing_id>.tga` and `suit_spec_<iracing_id>.tga`

If a file already exists at the destination path, Live Link **overwrites it**. This is intentional — most users want their latest design in iRacing without manually deleting the old one. If you want to preserve old paints, use SPB's project save (which is independent of Live Link) before re-exporting.

For non-default exports (sharing a paint with another driver who has a different `<iracing_id>`), Live Link supports an "Export As" mode that lets you override the ID for one specific export without changing your saved profile.

## 6. Multi-Car Mode

If you paint multiple cars, Live Link handles per-car folder routing automatically:

1. SPB knows which car the current paint targets (you select it when starting a paint project).
2. On export, SPB writes the file to `<iracing_root>\paint\<car_folder>\` where `<car_folder>` is the iRacing per-car directory name (`stockcars2_chevyss`, `dallaraf3`, etc.).
3. Helmet and suit files always go to `helmets\` and `suits\` since iRacing uses one folder per asset type for those.

You can have an active paint project per car simultaneously. Live Link writes to the correct per-car folder based on which project triggered the export.

## 7. Folder Permissions Issues

The most common Live Link failure is a permissions problem. Symptoms:

- "Permission denied" toast on export.
- Live Link silently disables itself.
- Files appear in SPB's export folder but not in the iRacing folder.

Fixes:

1. **Run SPB as a normal user, not as Administrator** — counterintuitively, running SPB as Admin and iRacing as a normal user can cause permissions mismatches because the Documents folder is per-user.
2. **Check that the iRacing folder isn't read-only** — right-click → Properties → unchecked Read-Only.
3. **Check antivirus / Windows Defender Controlled Folder Access** — these features sometimes block writes to Documents folders. Add SPB to the allowlist.
4. **OneDrive backup conflicts** — if your Documents folder is in OneDrive, OneDrive may lock files briefly during sync. SPB will retry once; if the retry fails it surfaces an error.
5. **Symlinked iRacing folder** — symlinks work but require both the target and the symlink to allow writes.

## 8. Verification Steps

After enabling Live Link and doing an export, verify:

1. SPB shows the "Paint dropped" toast on export.
2. Open File Explorer, navigate to your iRacing folder, and confirm the file timestamp is recent.
3. Check that both diffuse (`car_<id>.tga`) and spec (`car_spec_<id>.tga`) are present.
4. Open file properties — file size should be roughly what you'd expect (a 2048×2048 24-bit TGA is ~12 MB).
5. Launch iRacing, go to garage for that car — the paint should show on the car preview.
6. Repeat for helmet and suit if you exported a full kit.

If any step fails, see Troubleshooting below.

## 9. Troubleshooting Live Link

**Symptom: Live Link toggle won't turn on.**
- Cause: SPB can't validate the iRacing folder.
- Fix: Re-pick the folder, ensure it points at the iRacing root (the folder containing `paint`, `helmets`, `suits`).

**Symptom: Export succeeds but iRacing doesn't show the new paint.**
- Cause: iRacing scans for files at session-load time. If iRacing was already running and at a session, it won't see new files until you reload.
- Fix: Exit to the iRacing main menu, re-enter the car selection — the paint should appear.

**Symptom: Export writes to SPB's local folder but not the iRacing folder.**
- Cause: Live Link is disabled or the folder path is invalid.
- Fix: Check Settings → iRacing Integration → confirm folder path and Live Link toggle.

**Symptom: Filename in iRacing folder doesn't match what you expect.**
- Cause: iRacing customer ID is wrong in SPB's profile.
- Fix: Settings → set the correct iRacing customer ID, re-export.

**Symptom: Spec map didn't write.**
- Cause: The current finish doesn't have a spec map (rare but possible with very old SPB project files).
- Fix: Re-pick a finish from the modern finish picker; the spec map will be regenerated.

**Symptom: Paint shows in iRacing but with wrong colors / wrong shine.**
- Cause: This is rarely a Live Link issue — it's almost always a spec map or color-space issue. See `SPB_IRACING_INTEGRATION.md` sections 6 and 8.

## 10. Disabling Live Link

To turn Live Link off:

1. Settings → iRacing Integration → toggle Live Link to **Off**.
2. SPB will continue to export to its local folder; iRacing folder writes stop immediately.
3. To re-enable later, just toggle back on — your folder path and customer ID are remembered.

You can also temporarily skip Live Link for a single export by holding Shift while clicking the Export button. This is useful when you want to save a work-in-progress without overwriting the version iRacing is currently using.

## 11. Best Practices

- **Set Live Link up once, then forget it.** The whole point is invisible auto-export.
- **Use SPB project saves for versioning.** Live Link always overwrites the iRacing file. If you want a "v2" of your paint to compare against "v1", save the SPB project at v1 first.
- **Don't paint while iRacing is in a session.** It works, but you have to exit and re-enter the car to see changes. Save the iteration cycle for between sessions.
- **Keep a backup of the iRacing custom paint folders.** Live Link's overwrite behavior plus the inevitable "I changed my mind" means you'll occasionally want yesterday's paint back. A weekly copy to a backup folder takes seconds and saves hours.
- **Test on a new paint first.** When you first enable Live Link, do a single throwaway export to verify the path and the iRacing pickup before throwing months of work at it.
- **Use the kit-export pack for sharing.** When sending a paint+helmet+suit kit to a teammate, SPB's pack export bundles all six TGAs into one ZIP — much easier than asking the recipient to grab six files from your iRacing folder.

Live Link removes the most error-prone step in iRacing painting (manual file copy with manual filename construction). Once you've used it for a session, the manual workflow feels like a step backward.
