"""
Deletes the STALE staged 8.0.4 payload + stub from R2 so the fresh (larger, store-compressed)
upload can't transiently exceed the 10 GB free tier mid-multipart. SAFE: the live feed
(latest.yml) still points at 8.0.3, so nothing references these objects; they are being
replaced by the new upload immediately after. NEVER touches 8.0.3 or latest.yml.
"""
import os
import sys

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:
    sys.exit("boto3 not installed. Run:  py -3 -m pip install boto3")

endpoint = os.environ.get("R2_ENDPOINT", "").strip()
ak = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
sk = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
bucket = os.environ.get("R2_BUCKET", "shokkerpaintbooth").strip()
if not (endpoint and ak and sk):
    sys.exit("Missing R2 credentials in the environment.")

s3 = boto3.client(
    "s3", endpoint_url=endpoint, aws_access_key_id=ak, aws_secret_access_key=sk,
    config=BotoConfig(request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
)

TARGETS = [
    "shokker-paint-booth-v6-8.0.4-x64.nsis.7z",
    "ShokkerPaintBoothV8-8.0.4-Web-Setup.exe",
]
for key in TARGETS:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        s3.delete_object(Bucket=bucket, Key=key)
        print(f"   purged stale staged object: {key}")
    except Exception:
        print(f"   not present (fine): {key}")
print("Stale 8.0.4 staging cleared - fresh upload has full headroom. 8.0.3 + latest.yml untouched.")
