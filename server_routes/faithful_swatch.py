"""One current, full-detail master for picker chips and their enlargement."""
import hashlib
import io
import json
from pathlib import Path
from threading import BoundedSemaphore

from PIL import Image
from engine.atomic_io import atomic_write_bytes, file_lock

_RENDERS = BoundedSemaphore(2)


def faithful_paths(cache_dir, identity, size=256):
    key = hashlib.sha256(json.dumps(['faithful-v1', *identity]).encode()).hexdigest()
    master = Path(cache_dir) / 'faithful_split_v1' / (key + '.png')
    return master, master.with_name(key + '_' + str(size) + '.png')


def faithful_split_bytes(*, cache_dir, identity, size, render, cache_allowed=True,
                         legacy_identity=None, read_allowed=True, allow_render=True):
    # Owner 2026-09-15: small previews must depict the SAME finish as enlargement.
    # Never consult legacy 48px snapshots, stale warm files, or the fast painter.
    path, sized_path = faithful_paths(cache_dir, identity, size)
    # Owner 2026-09-17: bake once; disk reads do not require write permission.
    # Persist the picker-sized derivative too, avoiding repeated PNG decoding.
    if read_allowed and size != 512 and sized_path.is_file():
        return sized_path.read_bytes()
    with file_lock(path):
        raw = None
        candidate = path
        if read_allowed and not path.is_file() and legacy_identity is not None:
            old_key = hashlib.sha256(json.dumps(['faithful-v1', *legacy_identity]).encode()).hexdigest()
            candidate = path.with_name(old_key + '.png')
        if read_allowed and candidate.is_file():
            try:
                raw = candidate.read_bytes()
                with Image.open(io.BytesIO(raw)) as im:
                    im.load()
                    if im.size != (1024, 512):
                        raw = None
            except (OSError, ValueError):
                raw = None
        if raw is not None and candidate != path and cache_allowed:
            atomic_write_bytes(path, raw)
        if raw is None:
            # Owner 2026-10-02: category browsing must NEVER launch a renderer.
            if not allow_render:
                raise FileNotFoundError('Current picker bake missing; run scripts/bake_faithful_picker.py')
            with _RENDERS:
                raw = render(512)
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                if im.size != (1024, 512):
                    raise ValueError('Full-detail swatch must be 1024 x 512')
            if cache_allowed:
                atomic_write_bytes(path, raw)
    if size == 512:
        return raw
    with Image.open(io.BytesIO(raw)) as im:
        # Resize each material separately: no paint/spec colour bleed at the seam.
        out = Image.new('RGB', (size * 2, size))
        for side in range(2):
            tile = im.crop((side * 512, 0, (side + 1) * 512, 512))
            out.paste(tile.resize((size, size), Image.Resampling.BOX), (side * size, 0))
        buf = io.BytesIO()
        out.save(buf, 'PNG')
        result = buf.getvalue()
        if cache_allowed:
            atomic_write_bytes(sized_path, result)
        return result
