"""r2_test_key.py - prove the R2 credentials work, WITHOUT changing anything.

Created 2026-08-09 (owner: "I want it where I never have to look for the freaking
tokens"). The whole point of storing a long-lived token is that you stop thinking
about it - but then you need a way to answer "is my saved key still good?" without
kicking off a 5 GB deploy to find out.

This does a read-only ListObjectsV2 against the bucket and prints what is up there.
It never writes, never deletes, never touches latest.yml.

Reads the same env vars deploy_r2.py uses (R2_ENDPOINT, R2_ACCESS_KEY_ID,
R2_SECRET_ACCESS_KEY, R2_BUCKET) so spb_release.ps1 -TestKey can populate them from
the DPAPI-encrypted store and call this.

Exit codes:  0 = key works   1 = key rejected / missing   2 = unexpected error
"""

from __future__ import annotations

import os
import sys

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError, EndpointConnectionError, NoCredentialsError
except ImportError:
    print("FAIL: boto3 is not installed for this Python. Run:  py -3 -m pip install boto3")
    sys.exit(2)


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

    missing = [n for n, v in (("R2_ENDPOINT", endpoint),
                              ("R2_ACCESS_KEY_ID", access),
                              ("R2_SECRET_ACCESS_KEY", secret)) if not v]
    if missing:
        print("FAIL: missing " + ", ".join(missing))
        return 1

    # Never print the secret. A 4-char tail is enough to tell two tokens apart.
    print(f"endpoint : {endpoint}")
    print(f"bucket   : {bucket}")
    print(f"key id   : ...{access[-4:]} ({len(access)} chars)")
    print(f"secret   : ...{secret[-4:]} ({len(secret)} chars, not shown)")
    print()

    # Shape check BEFORE the network call. R2 access keys are 32 hex chars and secrets
    # are 64; a bad copy-paste (truncated, doubled, or with a stray character) is the
    # most common real failure, and R2's own reply for it is a cryptic
    # "Credential access key has length 33, should be 32". Say it plainly instead.
    shape_problems = []
    if len(access) != 32:
        shape_problems.append(f"Access Key ID is {len(access)} characters; R2 IDs are exactly 32")
    if len(secret) != 64:
        shape_problems.append(f"Secret Access Key is {len(secret)} characters; R2 secrets are exactly 64")
    for label, val in (("Access Key ID", access), ("Secret Access Key", secret)):
        if val != val.strip():
            shape_problems.append(f"{label} has leading/trailing whitespace")
        elif not all(c in "0123456789abcdefABCDEF" for c in val):
            shape_problems.append(f"{label} contains non-hex characters (partial paste?)")
    if shape_problems:
        print("FAIL: the stored credentials are malformed - this is a paste problem,")
        print("      not a permissions problem:")
        for p in shape_problems:
            print(f"        - {p}")
        print()
        print("      Re-copy BOTH values from Cloudflare and run:  .\\spb_release.ps1 -SaveKey")
        print("      (Cloudflare shows the secret only once - if you lost it, delete that")
        print("       token and create a new one; see docs/R2_TOKEN_SETUP.md)")
        return 1

    # Same checksum workaround deploy_r2.py needs: botocore >=1.36 adds CRC32 trailers
    # that R2's S3 endpoint rejects. Harmless for a list, kept identical so this test
    # exercises the SAME client construction the real upload uses.
    cfg_kwargs = dict(retries={"max_attempts": 3, "mode": "standard"}, region_name="auto")
    try:
        cfg = BotoConfig(request_checksum_calculation="when_required",
                         response_checksum_validation="when_required", **cfg_kwargs)
    except TypeError:
        cfg = BotoConfig(**cfg_kwargs)

    try:
        s3 = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access,
                          aws_secret_access_key=secret, config=cfg)
        resp = s3.list_objects_v2(Bucket=bucket, MaxKeys=100)
    except NoCredentialsError:
        print("FAIL: boto3 rejected the credentials before sending (blank/!malformed).")
        return 1
    except EndpointConnectionError as e:
        print(f"FAIL: cannot reach the endpoint - {e}")
        print("      Check R2_ENDPOINT and your internet connection.")
        return 1
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "?")
        if code == "InvalidArgument":
            print(f"FAIL: R2 rejected the credential shape - {e}")
            print("      Re-copy both values from Cloudflare and run:  .\\spb_release.ps1 -SaveKey")
        elif code in ("InvalidAccessKeyId", "SignatureDoesNotMatch", "AccessDenied",
                      "Unauthorized", "403"):
            # "Unauthorized" is what R2 actually returns for a well-formed key that has
            # been deleted/expired, or whose permissions don't cover this bucket - i.e.
            # the most likely real-world failure once a long-lived token is in use.
            print(f"FAIL: R2 rejected the key ({code}). The key pair LOOKS valid, so this")
            print("      is a permissions/lifetime problem, not a typo:")
            print("        - the token may have been deleted or expired in Cloudflare")
            print("        - or it lacks 'Object Read & Write' on bucket '" + bucket + "'")
            print("        - or it was created for a different Cloudflare account")
            print()
            print("      Make a new token (docs/R2_TOKEN_SETUP.md walks the clicks), then:")
            print("        .\\spb_release.ps1 -SaveKey")
        elif code in ("NoSuchBucket", "404"):
            print(f"FAIL: bucket '{bucket}' does not exist for this account.")
        else:
            print(f"FAIL: {code} - {e}")
        return 1
    except Exception as e:  # pragma: no cover - defensive
        print(f"FAIL: unexpected error - {type(e).__name__}: {e}")
        return 2

    objs = resp.get("Contents", []) or []
    total = sum(o["Size"] for o in objs)
    print("OK - the key works. Bucket is readable.")
    print()
    if not objs:
        print("Bucket is empty.")
    else:
        print(f"{len(objs)} object(s), {human(total)} total"
              + (" (first 100 shown)" if resp.get("IsTruncated") else ""))
        print()
        # Biggest first - the payloads are what eat the 10 GB free tier.
        for o in sorted(objs, key=lambda x: -x["Size"])[:15]:
            print(f"  {human(o['Size']):>10}  {o['Key']}")
        if len(objs) > 15:
            print(f"  ... and {len(objs) - 15} more")
        print()
        FREE_TIER = 10 * 1024 ** 3
        pct = total / FREE_TIER * 100
        print(f"Free tier usage: {human(total)} of 10.0 GB ({pct:.0f}%)")
        if pct > 80:
            print("  WARNING: near the 10 GB ceiling - delete payloads older than the")
            print("  live release before staging a new one (keep the live one: rollback).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
