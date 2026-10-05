"""
deploy_r2.py — upload the built Shokker Paint Booth nsis-web artifacts to a
Cloudflare R2 bucket via the S3-compatible API (multipart, so the multi-GB
.nsis.7z payload uploads fine — the browser's 300 MB limit does not apply here).

It has two explicit phases and no one-shot mode:
    --hold-latest  stage the evidence-listed payload + web installer, then
                   verify exact size and spb-sha256 object metadata
    --only-latest  revalidate both staged objects, upload the exact evidence-
                   listed latest.yml, and verify its size/SHA metadata

Credentials are read from the environment so the secret key is never written to
any file on disk:
    R2_ENDPOINT            https://<accountid>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID       (from the R2 API token)
    R2_SECRET_ACCESS_KEY   (from the R2 API token)
    R2_BUCKET              bucket name (default: shokkerpaintbooth)
    R2_PUBLIC_URL          (optional) https://pub-xxxx.r2.dev  — only for printing links

Every network path first runs the matching non-mutating release preflight and
schema-2 local artifact/feed contract. `--check-release-contract` stops before
credential validation/client creation and never contacts R2.

Usage:
    py -3 deploy_r2.py "electron-app\\dist" --hold-latest
    py -3 deploy_r2.py "electron-app\\dist" --only-latest
    py -3 deploy_r2.py "electron-app\\dist" --hold-latest --check-release-contract
"""
import os
import re
import sys
import mimetypes
import base64
import hashlib
import json
import subprocess
from pathlib import Path

try:
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.config import Config as BotoConfig
except ImportError:
    boto3 = TransferConfig = BotoConfig = None


def human(n):
    f = float(n)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if f < 1024 or unit == "GiB":
            return f"{f:.1f} {unit}"
        f /= 1024


def resolve_artifacts_dir(arg: Path) -> Path:
    """nsis-web writes latest.yml/*.nsis.7z/*-Web-Setup.exe into a nsis-web/ subdir.
    Accept either dist/ (descend into nsis-web) or dist/nsis-web/ directly."""
    if (arg / "nsis-web" / "latest.yml").exists():
        return arg / "nsis-web"
    if (arg / "latest.yml").exists():
        return arg
    # Last resort: a nsis-web subdir that at least has a .nsis.7z
    if (arg / "nsis-web").is_dir() and list((arg / "nsis-web").glob("*.nsis.7z")):
        return arg / "nsis-web"
    sys.exit(f"No nsis-web artifacts (latest.yml) found in {arg} or {arg / 'nsis-web'}.\n"
             f"Build first:  set SPB_BUNDLE_ALL=1 && npm run build  (in electron-app)")


def parse_latest_yml(p: Path):
    """Return (version, package_7z_name) from a web-shaped latest.yml.
    Tries PyYAML, falls back to a tolerant regex parse (latest.yml is simple)."""
    text = p.read_text(encoding="utf-8", errors="replace")
    version = None
    pkg = None
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        version = str(data.get("version") or "").strip() or None
        # Prefer the files[] entry that ends in .nsis.7z; fall back to top-level path.
        for f in (data.get("files") or []):
            u = str(f.get("url") or "")
            if u.lower().endswith(".nsis.7z"):
                pkg = os.path.basename(u)
                break
        if not pkg and str(data.get("path") or "").lower().endswith(".nsis.7z"):
            pkg = os.path.basename(str(data["path"]))
    except Exception:
        pass
    if not version:
        m = re.search(r"^version:\s*([0-9][0-9A-Za-z.\-+]*)\s*$", text, re.M)
        version = m.group(1).strip() if m else None
    if not pkg:
        m = re.search(r"([A-Za-z0-9._\-]+\.nsis\.7z)", text)
        pkg = m.group(1) if m else None
    return version, pkg


def parse_latest_contract(p: Path):
    """Read every local object reference and integrity field from electron-builder latest.yml."""
    text = p.read_text(encoding="utf-8", errors="strict")
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(text) or {}
        package = ((data.get("packages") or {}).get("x64") or {})
        return {
            "version": str(data.get("version") or "").strip(),
            "files_urls": [str(row.get("url") or "").strip() for row in (data.get("files") or [])],
            "path": str(data.get("path") or "").strip(),
            "sha512": str(data.get("sha512") or "").strip(),
            "package_path": str(package.get("path") or "").strip(),
            "package_file": str(package.get("file") or "").strip(),
            "package_size": int(package.get("size") or 0),
            "package_sha512": str(package.get("sha512") or "").strip(),
        }
    except Exception:
        def take(pattern, source=text):
            match = re.search(pattern, source, re.M)
            return (match.group(1).strip().strip("'\"") if match else "")

        package_match = re.search(r"^packages:\s*$([\s\S]*?)(?=^[^ \t]|\Z)", text, re.M)
        package = package_match.group(1) if package_match else ""
        return {
            "version": take(r"^version:\s*(\S.*?)\s*$"),
            "files_urls": [value.strip().strip("'\"") for value in re.findall(r"^\s{2}-\s+url:\s*(\S.*?)\s*$", text, re.M)],
            "path": take(r"^path:\s*(\S.*?)\s*$"),
            "sha512": take(r"^sha512:\s*(\S.*?)\s*$"),
            "package_path": take(r"^\s+path:\s*(\S.*?)\s*$", package),
            "package_file": take(r"^\s+file:\s*(\S.*?)\s*$", package),
            "package_size": int(take(r"^\s+size:\s*(\d+)\s*$", package) or 0),
            "package_sha512": take(r"^\s+sha512:\s*(\S.*?)\s*$", package),
        }


def hash_file(path: Path, algorithm="sha256", encoding="hex"):
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii") if encoding == "base64" else digest.hexdigest()


def workspace_file(root: Path, relative, label):
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(f"{label} path is missing")
    root = root.resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the canonical workspace") from exc
    if not candidate.is_file():
        raise ValueError(f"{label} is not a file: {relative}")
    return candidate


def validate_release_contract(root: Path, art_dir: Path, evidence_path: Path):
    """Pure local verifier used before any credential lookup, R2 call, or upload."""
    evidence_file = workspace_file(root, str(evidence_path), "release evidence") if not evidence_path.is_absolute() \
        else workspace_file(root, os.path.relpath(evidence_path, root), "release evidence")
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    if evidence.get("schemaVersion") != 2:
        raise ValueError("release evidence schemaVersion must be 2")
    latest_row = evidence.get("latestYml") or {}
    latest = workspace_file(root, latest_row.get("path"), "latest.yml")
    art_dir = art_dir.resolve(strict=True)
    if latest != (art_dir / "latest.yml").resolve(strict=True):
        raise ValueError("evidence latest.yml is not the selected nsis-web/latest.yml")
    expected_mappings = {"filesUrl": "webInstaller", "path": "webInstaller",
                         "packagesX64Path": "updaterPackage", "packagesX64File": "updaterPackage"}
    if latest_row.get("mappings") != expected_mappings:
        raise ValueError("latest.yml mappings are incomplete or substituted")

    expected_channels = {"updaterPackage": ["r2"], "webInstaller": ["r2", "payhip"],
                         "payhipBundle": ["payhip"]}
    rows = evidence.get("distributables")
    if not isinstance(rows, list) or len(rows) != len(expected_channels):
        raise ValueError("distributables must enumerate exactly three release artifacts")
    roles = {}
    for row in rows:
        role = row.get("role") if isinstance(row, dict) else None
        if role not in expected_channels or role in roles:
            raise ValueError("distributable role is unknown or duplicated")
        if row.get("channels") != expected_channels[role]:
            raise ValueError(f"{role} channels do not match the release contract")
        file = workspace_file(root, row.get("path"), f"{role} distributable")
        actual = hash_file(file)
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256") or ""), re.I) or actual.lower() != row["sha256"].lower():
            raise ValueError(f"{role} SHA-256 does not match")
        if file.stat().st_size != row.get("bytes"):
            raise ValueError(f"{role} byte size does not match")
        roles[role] = {"role": role, "path": file, "sha256": actual, "bytes": file.stat().st_size}
    for role in ("updaterPackage", "webInstaller"):
        if roles[role]["path"].parent != art_dir:
            raise ValueError(f"{role} is not in the selected nsis-web directory")
    if not roles["updaterPackage"]["path"].name.lower().endswith(".nsis.7z"):
        raise ValueError("updaterPackage must be an .nsis.7z file")
    if not roles["webInstaller"]["path"].name.lower().endswith("-web-setup.exe"):
        raise ValueError("webInstaller must be a -Web-Setup.exe file")

    if hash_file(latest) != str(latest_row.get("sha256") or "").lower() or latest.stat().st_size != latest_row.get("bytes"):
        raise ValueError("latest.yml SHA-256 or byte size does not match")
    parsed = parse_latest_contract(latest)
    version = str(evidence.get("version") or "")
    if not roles["payhipBundle"]["path"].name.lower().endswith(".zip") or version not in roles["payhipBundle"]["path"].name:
        raise ValueError("payhipBundle must be a versioned zip")
    installer, package = roles["webInstaller"], roles["updaterPackage"]
    if parsed["version"] != version:
        raise ValueError("latest.yml version does not match release evidence")
    if parsed["files_urls"] != [installer["path"].name] or parsed["path"] != installer["path"].name:
        raise ValueError("latest.yml installer references do not match webInstaller")
    if parsed["package_path"] != package["path"].name or parsed["package_file"] != package["path"].name:
        raise ValueError("latest.yml package references do not match updaterPackage")
    if parsed["package_size"] != package["bytes"]:
        raise ValueError("latest.yml package size does not match updaterPackage")
    if parsed["sha512"] != hash_file(installer["path"], "sha512", "base64"):
        raise ValueError("latest.yml installer SHA-512 does not match webInstaller")
    if parsed["package_sha512"] != hash_file(package["path"], "sha512", "base64"):
        raise ValueError("latest.yml package SHA-512 does not match updaterPackage")
    roles["latestYml"] = {"role": "latestYml", "path": latest,
                          "sha256": hash_file(latest), "bytes": latest.stat().st_size}
    return version, roles


def run_preflight(root: Path, mode: str, evidence_path: Path):
    command = ["node", str(root / "scripts" / "spb_release_preflight.js"), f"--mode={mode}",
               f"--manifest={evidence_path}"]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=10 * 60)
    if result.returncode:
        detail = (result.stdout + result.stderr).strip()
        raise ValueError(f"{mode} release preflight blocked:\n{detail[-8000:]}")


def content_type_for(p: Path):
    name = p.name.lower()
    if name.endswith(".yml") or name.endswith(".yaml"):
        return "application/yaml"        # standards-correct (electron-updater reads body regardless)
    if name.endswith(".7z"):
        return "application/x-7z-compressed"
    if name.endswith(".exe"):
        return "application/octet-stream"
    return mimetypes.guess_type(str(p))[0] or "application/octet-stream"


def metadata_for(record, version):
    return {"spb-sha256": record["sha256"], "spb-role": record["role"], "spb-version": version}


def validate_head(record, head):
    metadata = {str(key).lower(): str(value) for key, value in (head.get("Metadata") or {}).items()}
    remote_hash = metadata.get("spb-sha256", "")
    if head.get("ContentLength") != record["bytes"]:
        raise ValueError(f"R2 {record['path'].name} size does not match local evidence")
    if not re.fullmatch(r"[0-9a-f]{64}", remote_hash, re.I) or remote_hash.lower() != record["sha256"]:
        raise ValueError(f"R2 {record['path'].name} SHA-256 metadata is missing or does not match")


def make_s3_client(env):
    if boto3 is None:
        raise ValueError("boto3 not installed. Run: py -3 -m pip install boto3")
    endpoint, access_key = env.get("R2_ENDPOINT", "").strip(), env.get("R2_ACCESS_KEY_ID", "").strip()
    secret_key = env.get("R2_SECRET_ACCESS_KEY", "").strip()
    missing = [key for key, value in {"R2_ENDPOINT": endpoint, "R2_ACCESS_KEY_ID": access_key,
                                      "R2_SECRET_ACCESS_KEY": secret_key}.items() if not value]
    if missing:
        raise ValueError("Missing env var(s): " + ", ".join(missing))
    cfg_kwargs = dict(retries={"max_attempts": 5, "mode": "standard"}, region_name="auto")
    try:
        boto_cfg = BotoConfig(request_checksum_calculation="when_required",
                              response_checksum_validation="when_required", **cfg_kwargs)
    except TypeError:
        print("NOTE: botocore too old for checksum kwargs; relying on default (may fail on R2).")
        boto_cfg = BotoConfig(**cfg_kwargs)
    return boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key, config=boto_cfg)


def release_inputs(argv):
    """Parse the explicit stage/activate boundary without reading credentials."""
    hold_latest, only_latest = "--hold-latest" in argv, "--only-latest" in argv
    check_only = "--check-release-contract" in argv
    evidence_arg = next((item.split("=", 1)[1] for item in argv if item.startswith("--evidence=")), None)
    known = {"--hold-latest", "--only-latest", "--check-release-contract"}
    unknown = [item for item in argv if item.startswith("--") and item not in known and not item.startswith("--evidence=")]
    pos = [item for item in argv if not item.startswith("--")]
    if unknown:
        raise ValueError("Unknown option(s): " + ", ".join(unknown))
    if hold_latest == only_latest:
        raise ValueError("Choose exactly one explicit phase: --hold-latest (stage) or --only-latest (activate).")
    if len(pos) != 1:
        raise ValueError('Usage: py -3 deploy_r2.py "<dist or nsis-web>" (--hold-latest | --only-latest) [--evidence=<json>] [--check-release-contract]')
    root, art_dir = Path(__file__).resolve().parent, resolve_artifacts_dir(Path(pos[0]).resolve())
    feed_version, _ = parse_latest_yml(art_dir / "latest.yml")
    if not feed_version:
        raise ValueError("latest.yml has no release version")
    evidence_path = Path(evidence_arg).resolve() if evidence_arg else root / "_release_evidence" / feed_version / "release-evidence.json"
    return hold_latest, only_latest, check_only, root, art_dir, feed_version, evidence_path


def upload_record(s3, bucket, record, version, xfer):
    file, size, state = record["path"], record["bytes"], {"done": 0, "last": -1}
    cache = "no-cache, max-age=0" if file.suffix.lower() in (".yml", ".yaml") else "public, max-age=31536000, immutable"
    extra = {"ContentType": content_type_for(file), "CacheControl": cache,
             "Metadata": metadata_for(record, version)}

    def progress(chunk):
        state["done"] += chunk
        pct = int(state["done"] * 100 / size) if size else 100
        if pct != state["last"] and (pct % 2 == 0 or pct == 100):
            state["last"] = pct
            print(f"\r   {file.name:<40} {pct:3d}%  ({human(state['done'])}/{human(size)})", end="", flush=True)

    print(f" -> {file.name}")
    s3.upload_file(str(file), bucket, file.name, ExtraArgs=extra, Config=xfer, Callback=progress)
    validate_head(record, s3.head_object(Bucket=bucket, Key=file.name))
    print(f"\r   {file.name:<40} 100%  ({human(size)}/{human(size)})  SHA VERIFIED")


if __name__ == "__main__":
    from scripts.spb_release_r2_publish import cli
    sys.exit(cli())
