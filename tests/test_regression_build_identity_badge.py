from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_header_badge_exposes_runtime_identity_without_devtools():
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
    badge_block = html[html.index('id="liveBuildBadge"'):html.index('id="gpuStatusBadge"')]

    assert "source_hash" in badge_block
    assert "server_hash" in badge_block
    assert "started_at" in badge_block
    assert "external_writes_disabled" in badge_block
    assert "dataset.sourceHash" in badge_block
    assert "sourceHash.slice(0, 8)" in badge_block
