"""[11.0.2 slim download 2026-10-16] Hover masters reach R2 once; release checks they are public."""
import importlib.util
import io
import uuid
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('r2_picker_previews', ROOT / 'scripts' / 'r2_picker_previews.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
PREFIX = 'picker-previews/faithful_split_v1/'


def png(size):
    buf = io.BytesIO()
    Image.new('RGB', size, (90, 10, 200)).save(buf, 'PNG')
    return buf.getvalue()


def tree(tmp_path, n=3, master_size=(1024, 512)):
    cards = tmp_path / ('cards-' + uuid.uuid4().hex)
    masters = tmp_path / ('masters-' + uuid.uuid4().hex)
    cards.mkdir()
    masters.mkdir()
    keys = [format(i, '064x') for i in range(n)]
    for k in keys:
        (cards / (k + '_256.png')).write_bytes(png((512, 256)))
        (masters / (k + '.png')).write_bytes(png(master_size))
    (cards / 'notes.txt').write_text('ignored')
    return cards, masters, keys


class FakeS3:
    def __init__(self, existing=()):
        self.objects = {PREFIX + k + '.png' for k in existing}
        self.sent = []

    def get_paginator(self, _):
        objects = self.objects

        class Pages:
            def paginate(self, Bucket, Prefix):
                yield {'Contents': [{'Key': key} for key in sorted(objects) if key.startswith(Prefix)]}
        return Pages()

    def upload_file(self, path, bucket, key, ExtraArgs):
        assert ExtraArgs['ContentType'] == 'image/png' and 'immutable' in ExtraArgs['CacheControl']
        self.sent.append(key)
        self.objects.add(key)


def test_prefix_matches_the_app():
    assert tool.bucket_prefix(tool._cdn().base_url()) == PREFIX


def test_upload_sends_only_what_the_bucket_lacks(tmp_path):
    cards, masters, keys = tree(tmp_path)
    s3 = FakeS3(existing=keys[:1])
    lines = []
    assert tool.upload(cards, masters, s3=s3, bucket='b', prefix=PREFIX, out=lines.append) == 0
    assert sorted(s3.sent) == [PREFIX + k + '.png' for k in keys[1:]]
    assert tool.upload(cards, masters, s3=s3, bucket='b', prefix=PREFIX, out=lines.append) == 0
    assert len(s3.sent) == 2 and 'already complete' in lines[-1]


def test_upload_refuses_when_a_master_is_wrong(tmp_path):
    cards, masters, _ = tree(tmp_path, master_size=(512, 256))
    s3 = FakeS3()
    lines = []
    assert tool.upload(cards, masters, s3=s3, bucket='b', prefix=PREFIX, out=lines.append) == 1
    assert s3.sent == [] and lines[-1].startswith('FAIL')


def test_dry_run_sends_nothing(tmp_path):
    cards, masters, _ = tree(tmp_path)
    s3 = FakeS3()
    assert tool.upload(cards, masters, s3=s3, bucket='b', prefix=PREFIX, dry_run=True, out=lambda _: None) == 0
    assert s3.sent == []


def test_check_fails_when_any_sampled_master_is_missing(tmp_path):
    cards, _, keys = tree(tmp_path, n=5)
    lines = []
    assert tool.check(cards, base_url='https://x/', fetch=lambda k: True, out=lines.append) == 0
    assert tool.check(cards, base_url='https://x/', fetch=lambda k: k != keys[-1], out=lines.append) == 1
    assert lines[-1].startswith('FAIL')
