"""Next-beta customer-surface gates requested by the owner on 2026-07-18."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unreliable_features_are_absent_from_the_customer_shell_but_preserved():
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
    electron = (ROOT / "electron-app" / "main.js").read_text(encoding="utf-8")
    tutorial = (ROOT / "js" / "spb-guided-mode.js").read_text(encoding="utf-8")

    assert '<script src="js/features/smart-separate.js' not in html
    assert '<script src="js/features/smart-separate-studio.js' not in html
    assert 'data-testid="btn-shokk-forge"' not in html
    assert "{ label: 'Open Shokker Forge'" not in electron
    assert "{ label: 'Open Spec Sculpt Lab'" not in electron
    assert "{ label: 'Open SPEC SCULPT'" in electron
    assert "{ label: 'Open Original SPEC SCULPT'" in electron
    assert "SMART SEPARATE" not in tutorial and "Auto-build layers" not in tutorial

    assert (ROOT / "js" / "features" / "smart-separate.js").is_file()
    assert (ROOT / "js" / "features" / "smart-separate-studio.js").is_file()
    assert (ROOT / "forge-page.html").is_file()
    assert "function openShokkForgeWindow()" in electron
    assert "function openSpecSculptWindow()" in electron


def test_customer_spec_entry_opens_the_guided_shell_not_the_legacy_lab():
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
    sculpt = (ROOT / "js" / "features" / "spb-easy-sculpt.js").read_text(encoding="utf-8")

    assert 'data-testid="btn-spec-sculpt"' in html
    assert "window.spbEasy&amp;&amp;window.spbEasy.openSculpt()" in html
    assert 'data-testid="btn-sculpt-my-paint"' not in html
    assert ">SPEC SCULPT</button>" in html
    assert "runWebCommand('spec-sculpt')" not in html
    assert "SHOW_LEGACY_SPEC_LAB = true" in sculpt
    assert "OPEN ORIGINAL SPEC SCULPT" in sculpt
    assert "function openGuidedSpecSculpt()" in (ROOT / "electron-app" / "main.js").read_text(encoding="utf-8")
    assert (ROOT / "spec-sculpt.html").is_file(), "The internal control room must not be deleted."


def test_by_color_source_picker_has_a_keyboard_path():
    easy = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")
    easy_css = (ROOT / "css" / "spb-easy-mode-20260716.css").read_text(encoding="utf-8")

    assert 'id="spbEasyPickCanvas" tabindex="-1" role="button"' in easy
    assert "if (event.key !== 'Enter' && event.key !== ' ') return;" in easy
    assert "els.pickCanvas.tabIndex = 0" in easy
    assert "els.pickCanvas.focus({ preventScroll: true })" in easy
    assert "var keepColor = $('spbEasyKeepColor')" in easy and "keepColor.focus()" in easy
    assert "#spbEasyPickCanvas:focus-visible" in easy_css
    assert "body.spb-easy-on { overflow: hidden !important; }" in easy_css


def test_by_color_remove_chip_handles_embedded_browser_text_targets():
    easy = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")

    assert "e.target.nodeType === 3 ? e.target.parentElement : e.target" in easy
    assert "target.closest('[data-zx]')" in easy
    assert "e.preventDefault()" in easy and "e.stopPropagation()" in easy
    assert "removeColorZone(parseInt(x, 10))" in easy


def test_by_color_reuses_validated_spec_sculpt_source_before_disk_fallback():
    easy = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")

    assert "window.spbEasySculpt.getState()" in easy
    assert "var sculptUrl = sculptState && sculptState.sourceUrl" in easy
    assert "sculptImage.src = sculptUrl" in easy
    assert easy.index("sculptImage.src = sculptUrl") < easy.index("fetch(serverBase() + '/preview-tga'")


def test_finish_search_deduplicates_cross_listed_looks_without_removing_browse_families():
    easy = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")

    assert "var parts = [], searchSeen = {};" in easy
    assert "if (!_searchText) return true;" in easy
    assert "if (searchSeen[id]) return false;" in easy
    assert "searchSeen[id] = true;" in easy


def test_easy_save_requires_server_hash_verification():
    easy = (ROOT / "js" / "spb-easy-mode.js").read_text(encoding="utf-8")
    server = (ROOT / "server.py").read_text(encoding="utf-8")

    assert "out.verified === true" in easy
    assert '"verified": True' in server
    assert "Copy verification failed for {dst_name}" in server
    assert "dst_sha256 != src_sha256" in server
