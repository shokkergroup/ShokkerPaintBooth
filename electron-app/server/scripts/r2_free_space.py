"""
SPB R2 space cleanup - SAFE BY CONSTRUCTION.
Lists the bucket, then deletes ONLY release objects whose version is OLDER than 8.0.3.
NEVER deletes latest.yml, NEVER deletes 8.0.3 (the currently-live feed) or 8.0.4 or newer.
Reads creds from the environment (set by the caller). Prints a full audit of what it does.
"""
import os
import re
import sys

try:
    import boto3
    from botocore.config import Config as BotoConfig
except ImportError:
    sys.exit("boto3 not installed. Run:  py -3 -m pip install boto3")

KEEP_FLOOR = (8, 0, 3)  # this version and anything newer is protected; latest.yml always protected

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


def parse_version(key):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", key)
    return tuple(int(x) for x in m.groups()) if m else None


resp = s3.list_objects_v2(Bucket=bucket)
objs = resp.get("Contents", [])
print(f"\nBucket '{bucket}' currently holds {len(objs)} object(s):")
total = 0
to_delete = []
for o in objs:
    key, size = o["Key"], o["Size"]
    total += size
    v = parse_version(key)
    protected = key.lower().endswith(".yml") or v is None or v >= KEEP_FLOOR
    if not protected:
        to_delete.append(key)
    vstr = ("v" + ".".join(map(str, v))) if v else "no-version"
    print(f"   [{'KEEP  ' if protected else 'DELETE'}] {size/1e9:6.3f} GB  {key}   ({vstr})")
print(f"   ----> total in bucket: {total/1e9:.2f} GB of 10 GB free tier")

if not to_delete:
    print("\nNothing older than 8.0.3 to remove. Bucket left as-is.")
    sys.exit(0)

print(f"\nDeleting {len(to_delete)} old object(s) (all older than the live 8.0.3):")
for key in to_delete:
    s3.delete_object(Bucket=bucket, Key=key)
    print(f"   deleted  {key}")

resp2 = s3.list_objects_v2(Bucket=bucket)
total2 = sum(o["Size"] for o in resp2.get("Contents", []))
print(f"\nFreed {(total-total2)/1e9:.2f} GB. Bucket now at {total2/1e9:.2f} GB - room for the 3.67 GB payload.")
