"""Fail-closed R2 stage/activation orchestration for deploy_r2.py."""
import json
import os
import subprocess
import sys

import deploy_r2 as contract


def prepare(argv):
    values = contract.release_inputs(argv)
    hold, only, check, root, art_dir, feed_version, evidence_path = values
    mode = "prestage" if hold else "activate"
    contract.run_preflight(root, mode, evidence_path)
    version, records = contract.validate_release_contract(root, art_dir, evidence_path)
    if version != feed_version:
        raise ValueError(f"evidence version {version} does not match latest.yml {feed_version}")
    return hold, only, check, art_dir, evidence_path, version, records


def _print_contract(mode, version, records):
    print(f"PASS  {mode} local release contract for {version}")
    for role in ("updaterPackage", "webInstaller", "payhipBundle", "latestYml"):
        record = records[role]
        print(f"  {record['role']:<16} {record['path'].name} {record['sha256']}")


def main(argv=None, env=None, client_factory=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if env is None else env
    client_factory = contract.make_s3_client if client_factory is None else client_factory
    hold, only, check, art_dir, evidence_path, version, records = prepare(argv)
    mode = "prestage" if hold else "activate"
    stage_records = [records["updaterPackage"], records["webInstaller"]]
    upload_records = stage_records if hold else [records["latestYml"]]
    if check:
        _print_contract(mode, version, records)
        return 0

    bucket = env.get("R2_BUCKET", "shokkerpaintbooth").strip()
    endpoint = env.get("R2_ENDPOINT", "").strip()
    s3 = client_factory(env)
    print(f"Release  : {version}\nBucket   : {bucket}\nEndpoint : {endpoint}\nFrom     : {art_dir}")
    print("Uploading (this release only):")
    for record in upload_records:
        print(f"   {record['path'].name:<48} {contract.human(record['bytes'])}  sha256={record['sha256']}")
    print()

    # Both objects referenced by latest.yml must already be exact before activation.
    if only:
        for record in stage_records:
            try:
                head = s3.head_object(Bucket=bucket, Key=record["path"].name)
                contract.validate_head(record, head)
            except Exception as exc:
                raise ValueError(f"REFUSING to activate: staged {record['role']} is not exact: {exc}") from exc
            print(f"Activation check OK: {record['path'].name} ({record['sha256']}).")

    xfer = contract.TransferConfig(multipart_threshold=64 * 1024 * 1024,
                                   multipart_chunksize=64 * 1024 * 1024,
                                   max_concurrency=4, use_threads=True)
    for record in upload_records:
        try:
            contract.upload_record(s3, bucket, record, version, xfer)
        except Exception as exc:
            print()
            raise ValueError(f"Upload or SHA verification FAILED for {record['path'].name}: {exc}") from exc

    public = env.get("R2_PUBLIC_URL", "").rstrip("/")
    print(f"\nAll {len(upload_records)} objects uploaded and SHA-verified for {version}.")
    if public:
        for record in upload_records:
            print(f"   {public}/{record['path'].name}")
    if hold:
        print("\n*** STAGED — NOT ACTIVATED ***")
        print("Both feed-referenced objects are exact on R2; latest.yml was NOT published.")
        print(f'Activate only after smoke evidence is final: py -3 deploy_r2.py "{art_dir}" --only-latest --evidence="{evidence_path}"')
    else:
        print(f"\n*** ACTIVATED — exact latest.yml for {version} was uploaded and SHA-verified. ***")
        print(f"Updater feed: {public}/latest.yml" if public else "latest.yml published.")
    return 0


def cli():
    try:
        return main()
    except (ValueError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
