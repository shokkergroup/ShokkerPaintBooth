"""r2_picker_previews.py - put the picker hover previews on R2, and prove they are there.

[11.0.2 slim download 2026-10-16, Claude] Owner: "Keep everything offline except the
big hover previews, about 7 GB." The installer ships the grid cards (<key>_256.png)
but not the 1024x512 masters (<key>.png, ~3.4 GB). The app fetches a master the
first time that finish is hovered (server_routes/preview_cdn.py). This script is
how those masters reach the bucket:

  upload  For every card the PACKAGED app ships, upload its master unless the bucket
          already has it. Names are content hashes, so an existing object is never
          rewritten and a re-run only sends what is new. Needs R2_* env (spb_release.ps1
          -UseStoredKey loads them; this script never prints a credential).
  check   No credentials. Reads a sample of masters back from the PUBLIC url the app
          uses. spb_release.ps1 runs it before activation.

Exit code is non-zero on any problem, with one verdict line.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import random
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_CARD = re.compile(r'([0-9a-f]{64})_256\.png')
CACHE_CONTROL = 'public, max-age=31536000, immutable'


def _cdn():
    # Load the app's own module so the bucket path can never drift from what the app asks for.
    spec = importlib.util.spec_from_file_location('preview_cdn', ROOT / 'server_routes' / 'preview_cdn.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bucket_prefix(base_url):
    # https://pub-....r2.dev/picker-previews/faithful_split_v1/ -> picker-previews/faithful_split_v1/
    return base_url.split('://', 1)[1].split('/', 1)[1]


def shipped_keys(cards_dir):
    return sorted(m.group(1) for m in (_CARD.fullmatch(p.name) for p in Path(cards_dir).iterdir()) if m)


def master_ok(path):
    from PIL import Image
    try:
        with Image.open(path) as im:
            return im.format == 'PNG' and im.size == (1024, 512)
    except (OSError, ValueError):
        return False


def existing_names(s3, bucket, prefix):
    names = set()
    for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket, Prefix=prefix):
        names.update(obj['Key'][len(prefix):] for obj in page.get('Contents', ()))
    return names


def upload(cards_dir, masters_dir, *, s3, bucket, prefix, dry_run=False, workers=6, out=print):
    keys = shipped_keys(cards_dir)
    if not keys:
        out('FAIL: no grid cards found in ' + str(cards_dir))
        return 1
    bad = [k for k in keys if not master_ok(Path(masters_dir) / (k + '.png'))]
    if bad:
        out(f'FAIL: {len(bad)} shipped card(s) have no valid 1024x512 master, e.g. {bad[0]}.png - rebake first')
        return 1
    have = existing_names(s3, bucket, prefix) if s3 is not None else set()
    todo = [k for k in keys if k + '.png' not in have]
    size = sum((Path(masters_dir) / (k + '.png')).stat().st_size for k in todo)
    out(f'Previews : {len(keys)} shipped, {len(keys) - len(todo)} already in the bucket, {len(todo)} to send ({size / 1e9:.2f} GB)')
    if dry_run or not todo:
        out('PREVIEWS DRY RUN - nothing sent' if dry_run else 'PREVIEWS OK - bucket already complete')
        return 0

    def send(key):
        s3.upload_file(str(Path(masters_dir) / (key + '.png')), bucket, prefix + key + '.png',
                       ExtraArgs={'ContentType': 'image/png', 'CacheControl': CACHE_CONTROL})
        return key

    failed, done = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(send, k): k for k in todo}
        for future in as_completed(futures):
            try:
                future.result()
                done += 1
            except Exception as exc:   # report every failure, keep sending the rest
                failed.append((futures[future], type(exc).__name__))
            if (done + len(failed)) % 200 == 0:
                out(f'  {done + len(failed)}/{len(todo)} ...')
    if failed:
        out(f'FAIL: {len(failed)} upload(s) failed, e.g. {failed[0][0]}.png ({failed[0][1]}). Re-run: it resumes.')
        return 1
    out(f'PREVIEWS OK - sent {done}, bucket now has all {len(keys)}')
    return 0


def check(cards_dir, *, base_url, sample=40, fetch=None, out=print):
    keys = shipped_keys(cards_dir)
    if not keys:
        out('FAIL: no grid cards found in ' + str(cards_dir))
        return 1
    picked = sorted(set(random.Random(len(keys)).sample(keys, min(sample, len(keys))) + [keys[0], keys[-1]]))

    def head(key):
        request = urllib.request.Request(base_url + key + '.png', method='HEAD',
                                         headers={'User-Agent': 'ShokkerPaintBooth-release'})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return response.status == 200 and int(response.headers.get('Content-Length') or 0) > 0
        except (urllib.error.URLError, OSError, ValueError):
            return False
    fetch = fetch or head
    missing = [k for k in picked if not fetch(k)]
    if missing:
        out(f'FAIL: {len(missing)}/{len(picked)} hover previews are not public yet, e.g. {base_url}{missing[0]}.png')
        return 1
    out(f'PREVIEWS PUBLIC OK - {len(picked)}/{len(picked)} sampled masters readable at {base_url}')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('mode', choices=('upload', 'check'))
    parser.add_argument('--cards', required=True, help='faithful_split_v1 folder of the PACKAGED app')
    parser.add_argument('--masters', help='faithful_split_v1 folder that still holds the masters (upload)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--sample', type=int, default=40)
    args = parser.parse_args(argv)
    base = _cdn().base_url()
    if args.mode == 'check':
        return check(args.cards, base_url=base, sample=args.sample)
    if not args.masters:
        parser.error('upload needs --masters')
    s3 = None
    bucket = os.environ.get('R2_BUCKET', 'shokkerpaintbooth').strip()
    if not args.dry_run or os.environ.get('R2_SECRET_ACCESS_KEY'):
        endpoint = os.environ.get('R2_ENDPOINT', '').strip()
        access = os.environ.get('R2_ACCESS_KEY_ID', '').strip()
        secret = os.environ.get('R2_SECRET_ACCESS_KEY', '').strip()
        if not (endpoint and access and secret):
            print('FAIL: R2 credentials are not loaded. Run through spb_release.ps1 -UseStoredKey.')
            return 1
        import boto3
        from botocore.config import Config
        s3 = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret,
                          region_name='auto', config=Config(retries={'max_attempts': 5, 'mode': 'standard'}))
    return upload(args.cards, args.masters, s3=s3, bucket=bucket, prefix=bucket_prefix(base), dry_run=args.dry_run)


if __name__ == '__main__':
    sys.exit(main())
