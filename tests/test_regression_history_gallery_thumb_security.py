from pathlib import Path


def _gallery_body():
    src = Path("paint-booth-5-api-render.js").read_text(encoding="utf-8")
    start = src.index("function buildGalleryHTML()")
    end = src.index("function closeHistoryGallery", start)
    return src[start:end]


def test_history_gallery_grid_prefers_persisted_thumbnail():
    body = _gallery_body()
    assert "entry.thumb || entry.paint_url" in body
    assert 'src="${_gridThumb}"' in body


def test_history_gallery_compare_escapes_zone_summaries():
    body = _gallery_body()
    assert "_compareASummary = _esc" in body
    assert "_compareBSummary = _esc" in body
    assert "${renderHistory[historyCompareA]?.zones_summary" not in body
    assert "${renderHistory[historyCompareB]?.zones_summary" not in body


def test_history_gallery_actions_never_embed_entry_strings_in_inline_js():
    body = _gallery_body()
    assert "historyShareRender(${idx})" in body
    assert "historyDownloadPaint(${idx})" in body
    assert "historyShowChannels(${idx})" in body
    assert "historyShowHistogram(${idx})" in body
    assert "copyRenderShareLink('${entry." not in body
    assert "downloadRenderFile('${entry." not in body
    assert "showSpecChannels('${entry." not in body
    assert "showRenderHistogram('${entry." not in body
    assert 'value="${_esc(query || \'\')}"' in body


def test_thumbnail_and_history_metadata_are_persisted_after_async_bake():
    src = Path("paint-booth-5-api-render.js").read_text(encoding="utf-8")
    assert "const RENDER_HISTORY_STORAGE_KEY" in src
    assert "function persistRenderHistory()" in src
    assert "function restorePersistedRenderHistory()" in src
    thumb_start = src.index("_histEntry.thumb = _tc.toDataURL")
    thumb_tail = src[thumb_start : thumb_start + 600]
    assert "persistRenderHistory()" in thumb_tail
    assert "thumb: thumb.length <= 250000" in src
