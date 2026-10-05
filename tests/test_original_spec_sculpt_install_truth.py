import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "spec-sculpt.html"
RUNTIME_PATH = ROOT / "electron-app" / "server" / "spec-sculpt.html"


def _extract_function(source: str, name: str) -> str:
    start = source.index(f"function {name}(")
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"Could not extract {name}")


def test_install_assessment_rejects_nested_failure_or_unverified_partial_pair():
    source = SOURCE_PATH.read_text(encoding="utf-8")
    helpers = "\n".join(
        _extract_function(source, name)
        for name in ("_installResultNames", "_assessGenerateInstall")
    )
    cases = [
        {
            "label": "nested deploy failure",
            "body": {"deploy_car_folder": "dirtlatemodel 438", "iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True, "deploy_to_iracing": {"success": False, "verified": False, "error": "copy locked"}},
            "ok": False,
        },
        {
            "label": "missing nested deploy receipt",
            "body": {"deploy_car_folder": "dirtlatemodel 438", "iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True},
            "ok": False,
        },
        {
            "label": "unverified deploy",
            "body": {"deploy_car_folder": "dirtlatemodel 438", "iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True, "deploy_to_iracing": {"success": True, "verified": False, "deployed": ["car_num_23371.tga", "car_spec_23371.tga"]}},
            "ok": False,
        },
        {
            "label": "partial deploy pair",
            "body": {"deploy_car_folder": "dirtlatemodel 438", "iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True, "deploy_to_iracing": {"success": True, "verified": True, "deployed": ["car_spec_23371.tga"]}},
            "ok": False,
        },
        {
            "label": "exact custom-number pair",
            "body": {"deploy_car_folder": "dirtlatemodel 438", "iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True, "deploy_to_iracing": {"success": True, "verified": True, "deployed": ["car_spec_23371.tga", "car_num_23371.tga"]}},
            "ok": True,
        },
        {
            "label": "nested output_dir failure",
            "body": {"output_dir": "C:/paint/car", "iracing_id": "23371", "use_custom_number": False},
            "result": {"success": True, "output_dir": {"success": False, "verified": False, "error": "folder missing"}},
            "ok": False,
        },
        {
            "label": "nested output_folder alias failure",
            "body": {"output_dir": "C:/paint/car", "iracing_id": "23371", "use_custom_number": False},
            "result": {"success": True, "output_folder": {"success": False, "verified": False, "error": "folder missing"}},
            "ok": False,
        },
        {
            "label": "exact sim-stamped output pair",
            "body": {"output_dir": "C:/paint/car", "iracing_id": "23371", "use_custom_number": False},
            "result": {"success": True, "output_dir": {"success": True, "verified": True, "pushed_files": ["car_23371.tga", "car_spec_23371.tga"]}},
            "ok": True,
        },
        {
            "label": "advanced render-only remains valid",
            "body": {"iracing_id": "23371", "use_custom_number": True},
            "result": {"success": True},
            "ok": True,
        },
    ]
    script = (
        helpers
        + "\nconst cases = "
        + json.dumps(cases)
        + ";\nprocess.stdout.write(JSON.stringify(cases.map(c => ({label:c.label, result:_assessGenerateInstall(c.body,c.result)}))));"
    )
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    actual = {row["label"]: row["result"]["ok"] for row in json.loads(completed.stdout)}
    assert actual == {case["label"]: case["ok"] for case in cases}


def test_simple_one_click_generators_share_force_install_contract_but_advanced_stays_opt_in():
    source = SOURCE_PATH.read_text(encoding="utf-8")

    assert "if (getUiMode() === 'simple') out.force_deploy = true;" in source
    assert source.count("generate(_simpleAutoInstallOptions({ fast_trace: true }))") == 3
    assert "await generate(_simpleAutoInstallOptions())" in source
    assert "generate(getUiMode() === 'simple' ? { force_deploy: true } : {})" in source
    assert "$('btnGenerateSimple').addEventListener('click', function () { generate({ force_deploy: true }); })" in source

    # Advanced still requires its existing explicit checkbox/manual request.
    assert "if ($('deployNow').checked || opts.force_deploy)" in source
    assert "if (dep) body.deploy_car_folder = dep" in source
    assert "else if (od) body.output_dir = od" in source


def test_green_done_is_after_nested_install_truth_gate_and_runtime_copy_matches():
    source = SOURCE_PATH.read_text(encoding="utf-8")

    gate = source.index("var installCheck = _assessGenerateInstall(body, j);")
    failure = source.index("<strong>NOT INSTALLED</strong>", gate)
    green_done = source.index("setBanner(msg, 'ok');", gate)
    assert gate < failure < green_done
    assert "let msg = installCheck.required ? 'DONE · INSTALLED + VERIFIED'" in source
    assert "hideSculptLoader(completedSuccessfully)" in source
    assert "var deployCheck = _assessGenerateInstall" in source
    assert "DONE · INSTALLED + VERIFIED — paint + spec are in iRacing" in source

    assert RUNTIME_PATH.read_bytes() == SOURCE_PATH.read_bytes()
