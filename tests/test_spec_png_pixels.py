"""Stored material bytes must survive alpha0/1 and every PNG row filter."""
import base64
import json
import struct
import subprocess
import zlib
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('channels', [3, 4])
def test_raw_spec_decoder_preserves_channels_across_all_filters(tmp_path, channels):
    width, height = 7, 5
    rows = [bytes((x * 31 + y * 47) % 256 for x in range(width * channels)) for y in range(height)]
    if channels == 4:
        rows = [bytes(v if x % 4 != 3 else [0, 1, 127, 255][(x // 4) % 4] for x, v in enumerate(row)) for row in rows]

    def paeth(a, b, c):
        p = a + b - c
        return min((a, b, c), key=lambda v: abs(p - v))

    filtered = bytearray()
    for y, row in enumerate(rows):
        filtered.append(y)  # exercise PNG filters0 through4 independently
        for x, value in enumerate(row):
            a = row[x - channels] if x >= channels else 0
            b = rows[y - 1][x] if y else 0
            c = rows[y - 1][x - channels] if y and x >= channels else 0
            prediction = [0, a, b, (a + b) // 2, paeth(a, b, c)][y]
            filtered.append((value - prediction) & 255)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    compressed = zlib.compress(filtered)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6 if channels == 4 else 2, 0, 0, 0))
    png += chunk(b'IDAT', compressed[:9]) + chunk(b'IDAT', compressed[9:]) + chunk(b'IEND', b'')
    path = tmp_path / 'material.png'
    path.write_bytes(png)
    expected = Image.open(path).convert('RGBA').tobytes()  # independent PNG decoder
    script = """
const fs=require('node:fs'),api=require('./js/canvas/zone/spec-png-pixels.js');
api.decode(fs.readFileSync(process.argv[1])).then(p=>process.stdout.write(JSON.stringify({width:p.width,height:p.height,data:Buffer.from(p.data).toString('base64')}))).catch(e=>{console.error(e);process.exitCode=1});
"""
    actual = json.loads(subprocess.check_output(['node', '-e', script, str(path)], cwd=ROOT, text=True))
    assert (actual['width'], actual['height']) == (width, height)
    assert base64.b64decode(actual['data']) == expected
