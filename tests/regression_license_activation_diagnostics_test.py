from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[1]
MAIN_JS = REPO / "electron-app" / "main.js"


def _main_source() -> str:
    return MAIN_JS.read_text(encoding="utf-8")


def test_electron_main_license_path_still_parses():
    result = subprocess.run(
        ["node", "--check", str(MAIN_JS)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_license_activation_has_chromium_network_fallback_and_error_codes():
    src = _main_source()

    assert "requestPayhipViaHttps" in src
    assert "requestPayhipViaElectronNet" in src
    assert "Retrying Payhip verify through electron:net" in src
    assert "Could not reach license server (${code})" in src
    assert "code=${code}" in src


def test_license_activation_logs_response_shape_without_logging_secret():
    src = _main_source()

    assert "Payhip verify ${transport} status=${statusCode}" in src
    assert "dataType=${Array.isArray(json.data) ? 'array' : typeof json.data}" in src
    assert "summarizePayhipBody" in src
    assert "product-secret-key" in src
    assert "PAYHIP_PRODUCT_SECRET}" not in src


def test_license_activation_has_machine_bound_offline_rescue_path():
    src = _main_source()

    assert "saveLocalLicense(licenseKey, email, options = {})" in src
    assert "offlineActivated: !!options.offlineActivated" in src
    assert "offlineReason: options.offlineReason || ''" in src
    assert "saveLocalLicense(trimmedKey, '', { offlineActivated: true, offlineReason: result.reason })" in src
    assert "Saved offline activation on this PC." in src
    assert "Starting 3-day offline activation grace" not in src
    assert "ACTIVATION_GRACE_FILE" in src
    assert "machineId: getMachineId()" in src
    assert "startOrContinueActivationGrace" in src
    assert "hasActiveActivationGrace()" in src
    assert "clearActivationGrace('activated')" in src
    assert "activated === true || activated === 'grace'" in src
