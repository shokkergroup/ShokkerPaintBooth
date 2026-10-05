"""Build a private SPB local plugin without modifying the production bridge."""
import argparse
import hashlib
import json
import re
import struct
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PACKAGE = LANE / "shokker-paint-booth-local"
FILES = [
    "plugin.json", "mcp.json", ".codex-plugin/plugin.json", ".mcp.json",
    "skills/spb-painting/SKILL.md", "README.md", "server/index.js",
    "server/tools.json", "assets/icon.png", "BUILD_PROVENANCE.json",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_manifests():
    manifest = read_json(PACKAGE / "plugin.json")
    overlay = read_json(PACKAGE / ".codex-plugin/plugin.json")
    portable = read_json(PACKAGE / "mcp.json")
    legacy = read_json(PACKAGE / ".mcp.json")
    assert manifest["name"] == PACKAGE.name == overlay["name"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["version"] == overlay["version"]
    assert not {"skills", "apps", "mcpServers", "interface"}.intersection(manifest)
    interface = manifest["extensions"]["com.openai"]["interface"]
    assert interface == overlay["interface"]
    assert len(interface["shortDescription"]) <= 30
    assert isinstance(interface["defaultPrompt"], list)
    assert 1 <= len(interface["defaultPrompt"]) <= 3
    connection = portable["mcpServers"]["shokker-paint-booth"]
    assert connection["type"] == "stdio" and connection["command"] == "node"
    assert connection["args"] == ["${PLUGIN_ROOT}/server/index.js"]
    for field in ("command", "args"):
        assert connection[field] == legacy["mcpServers"]["shokker-paint-booth"][field]
    skill = (PACKAGE / "skills/spb-painting/SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\nname: spb-painting\ndescription:")
    return manifest, portable


def validate_schemas(documents):
    from jsonschema.validators import validator_for
    evidence = []
    for document in documents:
        url = document["$schema"]
        request = urllib.request.Request(url, headers={"User-Agent": "SPB-plugin-pilot/0.1"})
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read(1024 * 1024)
        schema = json.loads(raw)
        validator = validator_for(schema)
        validator.check_schema(schema)
        validator(schema).validate(document)
        evidence.append({"url": url, "schema_sha256": digest(raw), "result": "pass"})
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-schemas", action="store_true")
    args = parser.parse_args()
    snapshots = {}
    for relative in ("mcp/server/index.js", "mcp/server/tools.json"):
        raw = (ROOT / relative).read_bytes()
        target = PACKAGE / "server" / Path(relative).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        snapshots[relative] = {"sha256": digest(raw), "bytes": len(raw)}

    bundle = ROOT / "mcp/shokker-paint-booth.mcpb"
    with zipfile.ZipFile(bundle) as archive:
        icon = archive.read("icon.png")
    assert icon[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", icon[16:24])
    assert width == height and 48 <= width <= 4096 and len(icon) <= 5 * 1024 * 1024
    (PACKAGE / "assets").mkdir(exist_ok=True)
    (PACKAGE / "assets/icon.png").write_bytes(icon)
    for filename in ("plugin.json", ".codex-plugin/plugin.json"):
        document = read_json(PACKAGE / filename)
        presentation = document["extensions"]["com.openai"]["interface"] if filename == "plugin.json" else document["interface"]
        presentation.update({"logo": "./assets/icon.png", "composerIcon": "./assets/icon.png"})
        (PACKAGE / filename).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    manifest, portable = validate_manifests()
    schemas = validate_schemas((manifest, portable)) if args.validate_schemas else []
    for relative, evidence in snapshots.items():
        if digest((ROOT / relative).read_bytes()) != evidence["sha256"]:
            raise RuntimeError("Production source changed during build: " + relative)
    provenance = {
        "package": manifest["name"], "version": manifest["version"],
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "private local pilot; no public submission or hosted UI",
        "sources": snapshots, "icon_sha256": digest(icon),
        "official_schema_validation": schemas,
    }
    (PACKAGE / "BUILD_PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    output = LANE / (PACKAGE.name + "-" + manifest["version"] + ".zip")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = PACKAGE / relative
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("Missing or linked package file: " + relative)
            archive.write(path, PACKAGE.name + "/" + relative)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(FILES)
    print(json.dumps({"archive": str(output), "bytes": output.stat().st_size,
                      "files": len(FILES), "schema_checks": len(schemas)}))


if __name__ == "__main__":
    main()
