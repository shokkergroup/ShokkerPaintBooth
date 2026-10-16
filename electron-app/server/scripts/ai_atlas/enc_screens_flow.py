"""Lane S - the first-paint flow as real screens: loaded paint, a zone added, render, recipe card, saved files. Group: flow."""
import time
import enc_screens as E
from enc_screens import shot
import enc_screens_pairs as P
from enc_screens_ui import crop

FLOW_ARTS = ["workflows.first_paint", "workflows.what_is_shokker", "workflows.one_flat_sheet"]


def close_card(c):
    c.js("() => { try { closeRenderResults(); } catch (e) {} return 1; }"); c.wait(500)


@shot("flow", "flow_step1_loaded")
def flow_step1_loaded(c):
    close_card(c)
    P.clear(c); P.shotpic(c); E.tidy(c, 0)
    marks = [(1, "#paintFile"), (2, "#outputDir"), (3, "#splitSource", {"at": "tl"}), (4, "button::add zone"), (5, "#btnRender")]
    crop(c, "flow_step1_loaded", "Step 1: your paint is loaded", "Load your paint with Source Paint, set the iRacing car folder, then add zones. Nothing is changed yet.",
         FLOW_ARTS + ["workflows.loading_paint", "workflows.user_id_and_folder"], [0, 0, 1700, 1000], marks,
         ["SOURCE PAINT box (your PSD or TGA)", "IRACING CAR FOLDER box", "Your paint, untouched", "+ Add Zone", "RENDER (not yet)"],
         "The Shokker window with a paint loaded and no zones yet, with five numbered callouts.", maxw=1400)


@shot("flow", "flow_step2_zone_added")
def flow_step2_zone_added(c):
    close_card(c)
    P.clear(c); P.add(c, name="Red body", finish="base::candy", color="#d4111f"); P.shotpic(c); E.tidy(c, 0)
    marks = [(1, "#zone-card-0"), (2, "#sectionBase0 .swatch-trigger"), (3, "#sectionColor0 .section-header"), (4, "#splitPreview", {"at": "tl"})]
    crop(c, "flow_step2_zone_added", "Step 2: a zone added", "A zone is a card in the left column. Its settings open in the popout and the live preview changes at once.",
         FLOW_ARTS + ["zones.what_is_a_zone", "zones.popout_panel"], [0, 0, 1700, 1000], marks,
         ["The new zone card", "Base material (the finish)", "COLOR and APPLY AREA: which pixels it covers", "LIVE PREVIEW updates"],
         "The window with one zone added and the live preview showing a red body.", maxw=1400)


def _set_folder(c):
    c.js("() => { try { toggleLiveLink(false); } catch (e) {} const x = document.getElementById('liveLinkCheckbox'); if (x) x.checked = false; const o = document.getElementById('outputDir'); if (o) { o.value = ''; o.dispatchEvent(new Event('input', { bubbles: true })); o.dispatchEvent(new Event('change', { bubbles: true })); } return 1; }")


def _do_render(c):
    P.clear(c)
    for spec in reversed(E.PROJECT):
        P.add(c, **spec)
    P.shotpic(c); E.tidy(c, 0)
    c.js("() => { safeDoRender(); return 1; }")


def _wait_card(c, secs=90):
    for _ in range(secs // 2):
        c.wait(2000)
        if c.js("() => { const m = document.getElementById('recipeCardStage'); return !!(m && m.offsetParent !== null); }"):
            c.wait(1800)
            return True
    return False


@shot("flow", "flow_step5_rendering")
def flow_step5_rendering(c):
    close_card(c)
    _set_folder(c)
    _do_render(c)
    c.wait(2500)
    marks = [(1, "#btnRender")]
    im = c.grab([0, 0, 1700, 1000], marks)
    E.emit("flow_step5_rendering", "Step 5: RENDER", "Press RENDER (or Ctrl+R). The button shows RENDERING for a few seconds while the app builds the paint and the spec map.", "ui",
           FLOW_ARTS + ["preview_render.render_button", "preview_render.preview_vs_render"], im, "The window while a render is running, with the RENDER button marked.",
           ["RENDER button (shows RENDERING while it works)"], maxw=1400)
    _wait_card(c)
    c.js("() => { try { closeRenderResults(); } catch (e) {} return 1; }")


@shot("flow", "flow_step6_recipe_card")
def flow_step6_recipe_card(c):
    close_card(c)
    _set_folder(c)
    _do_render(c)
    assert _wait_card(c), "no recipe card"
    marks = [(1, "button::Copy Card"), (2, "button::Share Recipe"), (3, "button::Save to keep"), (4, "button::Recent renders"), (5, "button::CLOSE"), (6, "#renderStatusBanner", {"at": "tl"})]
    im = c.grab([0, 0, 1700, 1000], marks)
    E.emit("flow_step6_recipe_card", "Step 6: the render recipe card", "When the render lands, this card shows what was made, the paint and the spec map. Set the iRacing car folder in the header and the banner confirms where the files were saved; with no folder set it warns you, as here.", "ui",
           FLOW_ARTS + ["preview_render.render_button", "preview_render.render_history_stats", "preview_render.output_files", "ui_shell.render_results_panel", "preview_render.where_files_go"], im,
           "The render recipe card full screen with six numbered callouts.",
           ["Copy Card", "Share Recipe", "Save to keep", "Recent renders", "CLOSE", "Status banner (here: no iRacing folder set yet)"], maxw=1400)
    c.js("() => { try { closeRenderResults(); } catch (e) {} return 1; }")
