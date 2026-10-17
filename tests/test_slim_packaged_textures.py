"""11.0.2 slim: packaged textures become lossless WebP under their .png names only when decode-identical."""
import io, sys, uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import slim_packaged_textures as spt  # noqa: E402


def _png(arr, mode):
    buf = io.BytesIO()
    Image.fromarray(arr, mode).save(buf, 'PNG')
    return buf.getvalue()


def _detail(shape):
    # photo-like field + fine noise: WebP lossless beats PNG on it (like the real textures)
    i, j = np.mgrid[0:shape[0], 0:shape[1]]
    base = np.stack([np.sin(i / 9) * np.cos(j / 13), np.sin(j / 7 + i / 23), np.cos(i / 17) * np.sin(j / 5)], -1)
    noise = np.random.default_rng(7).integers(-3, 4, base.shape)
    out = np.clip(127 + 100 * base + noise, 0, 255).astype(np.uint8)
    return out[..., :shape[2]] if len(shape) == 3 else out[..., 0]


def test_rgb_png_becomes_identical_webp():
    src = _png(_detail((256, 256, 3)), 'RGB')
    out = spt.convert(src)
    assert out is not None and spt.is_webp(out[:12]) and len(out) < len(src)
    with Image.open(io.BytesIO(src)) as a, Image.open(io.BytesIO(out)) as b:
        assert (a.mode, a.size, a.tobytes()) == (b.mode, b.size, b.tobytes())


@pytest.mark.parametrize('mode', ['L', 'P'])
def test_grayscale_and_palette_keep_their_png(mode):
    arr = _detail((128, 128))
    img = Image.fromarray(arr, 'L')
    if mode == 'P':
        img = img.convert('P')
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    assert spt.convert(buf.getvalue()) is None


def test_apply_refuses_source_trees_and_rewrites_packaged_copy(tmp_path, monkeypatch):
    work = tmp_path / uuid.uuid4().hex
    tex = work / 'server' / 'assets' / 'reference_textures' / 'x'
    tex.mkdir(parents=True)
    src = _png(_detail((256, 256, 3)), 'RGB')
    (tex / 'a.png').write_bytes(src)
    monkeypatch.setattr(sys, 'argv', ['x', 'apply', '--server', str(work / 'server'), '--cache', str(work / 'cache'), '--workers', '1'])
    spt.main()
    assert spt.is_webp((tex / 'a.png').read_bytes()[:12])
    monkeypatch.setattr(sys, 'argv', ['x', 'apply', '--server', str(ROOT), '--workers', '1'])
    with pytest.raises(SystemExit):
        spt.main()
