"""Lane S - UI shots, part 4: dialogs and side panels (presets, template library, undo history, AI copilot, shortcuts, menus). Group: ui."""
import enc_screens as E
from enc_screens import shot
from enc_screens_ui import crop
from enc_screens_ui3 import menu_shot, clean

DLG = """(t) => { const all = Array.from(document.querySelectorAll('body *')).filter(e => e.children.length < 6 && (e.innerText || '').trim().toLowerCase().startsWith(t.toLowerCase()) && e.offsetParent !== null);
  for (const e of all) { let q = e; while (q && q !== document.body) { const s = getComputedStyle(q), r = q.getBoundingClientRect(); if ((s.position === 'fixed' || s.position === 'absolute') && r.width > 300 && r.height > 250) return [r.left, r.top, r.width, r.height]; q = q.parentElement; } }
  return null; }"""


def zmore(c, text):
    E.tidy(c, 0)
    c.click(".zone-more-btn", 600)
    c.js("([t]) => { const b = Array.from(document.querySelectorAll('#zoneMoreMenu button')).find(b => b.innerText.toLowerCase().includes(t)); if (b) b.click(); return !!b; }", [text])
    c.wait(1600)


@shot("ui", "ui_presets_gallery")
def ui_presets_gallery(c):
    zmore(c, "presets gallery")
    d = c.js(DLG, "Preset Gallery")
    marks = [(1, "*::preset gallery", {"at": "l", "dx": -6}), (2, "*::multi-color show car"), (3, "*::clean", {"at": "l", "dx": -6}), (4, "*::stealth mode")]
    crop(c, "ui_presets_gallery", "The Preset Gallery", "Ready-made zone sets in groups. Click one to load it onto your car; each card shows its zone colours.",
         ["zones.presets_templates", "ui_shell.zones_more_menu", "workflows.first_paint"], d, marks,
         ["Preset Gallery", "A preset card (name, summary, zone colours, zone count)", "A group heading (Show Car, Clean, Aggressive)", "Another preset"],
         "The Preset Gallery dialog listing ready-made zone sets in groups.", pad=4)
    c.esc(); c.wait(500)


@shot("ui", "ui_template_library")
def ui_template_library(c):
    zmore(c, "shokker library")
    marks = [(1, "*::livery template library", {"at": "l", "dx": -6}), (2, "*::racing stripe"), (3, "*::two-tone split"), (4, "button::close", {"at": "bl"})]
    crop(c, "ui_template_library", "The Livery Template Library", "A library of livery layouts (racing stripes, two-tone, GT3, chrome and more). Pick one and paint it with the brush.",
         ["zones.presets_templates", "shokk_drop.shokk_library_files", "ui_shell.zones_more_menu"], [0, 0, 1700, 1000], marks,
         ["Library title and count", "Template card: Racing Stripe", "Template card: Two-Tone Split", "Close"],
         "The Livery Template Library with a grid of template cards.", maxw=1400)
    c.esc(); c.wait(500)


@shot("ui", "ui_undo_history")
def ui_undo_history(c):
    zmore(c, "undo history")
    d = c.js(DLG, "Current State")
    marks = [(1, "*::current state", {"at": "l", "dx": -6}), (2, "*::Zone - Assign finish::", {"at": "l", "dx": -6})]
    marks = [m for m in marks if False] or [(1, "*::current state", {"at": "l", "dx": -8})]
    crop(c, "ui_undo_history", "The Undo History panel", "Every change is listed, newest first, with how long ago it happened. Click a step to go back to it.",
         ["tools.undo_redo", "tools.undo_redo"], d or [1420, 90, 280, 900], marks,
         ["Current state (top of the list)"], "The Undo History panel listing recent changes.", pad=2)
    c.esc(); c.wait(500)


@shot("ui", "ui_ai_panel")
def ui_ai_panel(c):
    E.tidy(c, 0)
    c.js("() => { const x = Array.from(document.querySelectorAll('button')).find(b => /^\s*\u2726?\s*AI\s*$/.test(b.innerText)); if (x) x.click(); return 1; }")
    c.wait(1800)
    marks = [(1, "#spbProAI button::show my layers"), (2, "#spbProAI textarea, #spbProAI input[type=text]"), (3, "#spbProAI button::send"), (4, "#spbProAI button::build it step by step"), (5, "#spbProAI button::encyclopedia")]
    crop(c, "ui_ai_panel", "The AI copilot panel", "The helper that builds paint from words. It starts offline; type what you want or tap a suggestion.",
         ["ai_copilot.panel_tour", "ai_copilot.chat_mode", "ai_copilot.offline_vs_ai"], "#spbProAI", marks,
         ["Quick suggestion chip", "Message box", "Send", "Build it step by step", "Encyclopedia"], "The AI copilot panel with five numbered callouts.", pad=0)
    E.tidy(c, 0)


@shot("ui", "ui_shortcuts_dialog")
def ui_shortcuts_dialog(c):
    E.tidy(c, 0)
    c.js("() => { const b = Array.from(document.querySelectorAll('button')).find(b => /keyboard shortcuts/i.test(b.innerText)); if (b) b.click(); return 1; }")
    c.wait(1200)
    marks = [(1, "*::canvas tools", {"at": "l", "dx": -6}), (2, "*::editing", {"at": "l", "dx": -6}), (3, "*::view & navigation", {"at": "l", "dx": -6}), (4, "*::zone operations", {"at": "l", "dx": -6}), (5, "button::close (esc)")]
    crop(c, "ui_shortcuts_dialog", "Keyboard shortcuts", "Press ? any time for this list: tools, editing, view and zone operations.",
         ["ui_shell.dialogs_reference", "tools.eyedropper_pick", "tools.undo_redo"], [380, 30, 1000, 800], marks,
         ["Canvas tools (B brush, E eraser, P eyedropper...)", "Editing (undo, copy, merge, select all)", "View and navigation (zoom, pan)", "Zone operations (Ctrl+R render, Shift+N new zone)", "Close (Esc)"],
         "The keyboard shortcuts dialog with five numbered callouts.")
    c.js("() => { const b = Array.from(document.querySelectorAll('button')).find(b => /close \(esc\)/i.test(b.innerText)); if (b) b.click(); return 1; }")
    c.wait(500)


@shot("ui", "ui_menu_retouch")
def ui_menu_retouch(c):
    menu_shot(c, "ui_menu_retouch", "#spbRetouchMenu", "The RETOUCH menu", "Brushes that paint on a layer: Color Brush, Recolor, Healing Brush, Smudge and Burn.",
              ["tools.retouch", "tools.brush_eraser"], "The RETOUCH menu open with numbered items.")


@shot("ui", "ui_render_history_menu")
def ui_render_history_menu(c):
    E.tidy(c, 0)
    c.click("#spbRenderHistMenu", 900)
    marks = [(1, "button::gallery"), (2, "button::recent")]
    region = c.union(["#spbRenderHistMenu", "details[open] .spb-tb-pop"], 12)
    crop(c, "ui_render_history_menu", "The RENDER HISTORY menu", "Thumbnails of your recent renders, with the Gallery and Recent lists.",
         ["preview_render.render_history_stats", "ui_shell.render_results_panel"], region, marks, ["Gallery", "Recent"],
         "The render history menu with two numbered callouts.")
    c.click("#spbRenderHistMenu", 400)
