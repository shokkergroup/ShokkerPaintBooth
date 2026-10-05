"""r2_upload_progress.py - how far along is an in-flight R2 multipart upload?

Created 2026-08-10. A 4.9 GB payload takes a long time on residential upload, and a
multipart upload is INVISIBLE in the bucket listing until CompleteMultipartUpload runs -
so "is it working or hung?" has no obvious answer. This asks R2 for the open multipart
uploads and counts the parts that have actually landed.

Read-only: ListMultipartUploads + ListParts. Never uploads, aborts, or deletes anything.

Usage:  py -3 scripts/r2_upload_progress.py [expected_bytes]
        (expected_bytes optional - lets it print a real percentage)

Exit: 0 = at least one upload in flight (or none, printed as such)   1 = credential/other error
"""

from __future__ import annotations

import os
import sys

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError
except ImportError:
    print("boto3 not installed for this Python.")
    sys.exit(1)


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def main() -> int:
    endpoint = os.environ.get("R2_ENDPOINT", "").strip()
    access = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    bucket = os.environ.get("R2_BUCKET", "shokkerpaintbooth").strip()
    if not (endpoint and access and secret):
        print("Missing R2 credentials in the environment.")
        return 1

    expected = None
    if len(sys.argv) > 1:
        try:
            expected = int(sys.argv[1])
        except ValueError:
            pass

    cfg_kwargs = dict(retries={"max_attempts": 3, "mode": "standard"}, region_name="auto")
    try:
        cfg = BotoConfig(request_checksum_calculation="when_required",
                         response_checksum_validation="when_required", **cfg_kwargs)
    except TypeError:
        cfg = BotoConfig(**cfg_kwargs)
    s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access,
                      aws_secret_access_key=secret, config=cfg)

    try:
        mp = s3.list_multipart_uploads(Bucket=bucket)
    except ClientError as e:
        print(f"Could not list multipart uploads: {e}")
        return 1

    uploads = mp.get("Uploads", []) or []
    if not uploads:
        print("No multipart upload in flight.")
        print("  -> either it finished (check the bucket listing) or it never started.")
        return 0

    for u in uploads:
        key = u["Key"]
        uid = u["UploadId"]
        done = 0
        count = 0
        marker = 0
        try:
            while True:
                parts = s3.list_parts(Bucket=bucket, Key=key, UploadId=uid,
                                      PartNumberMarker=marker, MaxParts=1000)
                chunk = parts.get("Parts", []) or []
                for p in chunk:
                    done += p["Size"]
                    count += 1
                if not parts.get("IsTruncated"):
                    break
                marker = parts.get("NextPartNumberMarker", 0)
        except ClientError as e:
            print(f"{key}: could not list parts - {e}")
            continue

        print(f"UPLOADING: {key}")
        print(f"  parts completed : {count}")
        print(f"  bytes landed    : {human(done)}")
        if expected and expected > 0:
            pct = done / expected * 100
            bar_len = 40
            filled = int(bar_len * min(pct, 100) / 100)
            print(f"  progress        : [{'#' * filled}{'.' * (bar_len - filled)}] {pct:.1f}%")
            print(f"  of expected     : {human(expected)}")
            remaining = expected - done
            if remaining > 0:
                print(f"  remaining       : {human(remaining)}")
        print(f"  started         : {u.get('Initiated')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
