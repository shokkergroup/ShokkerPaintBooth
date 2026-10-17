"""11.0.3 (Claude 2026-10-17): the hover-preview fetch must not depend on the Windows certificate store alone.

A PC that cached the expired ISRG Root X2 cross-certificate made Python reject r2.dev, so every hover fell back to
the grid card. preview_cdn.tls_context() adds the roots r2.dev chains to on top of the system store. No network here.
"""
import hashlib
import ssl

from server_routes import preview_cdn

EXPECTED = {
    '96bcec06264976f37460779acf28c5a7cfe8a3c0aae11a8ffcee05c0bddf08c6',  # ISRG Root X1
    '69729b8e15a86efc177a57afb7171dfc64add28c2fca8cf1507e34453ccb1470',  # ISRG Root X2
    'd947432abde7b7fa90fc2e6b59101b1280e0e1c7e4e40fa3c6887fff57a7f4cf',  # GTS Root R1
    '349dfa4058c5e263123b398ae795573c4e1313c83fe68f93556cd5e8031b3c7d',  # GTS Root R4
}


def test_bundled_roots_are_the_pinned_certificates():
    pems = preview_cdn._ROOTS.split('-----END CERTIFICATE-----')[:-1]
    fps = {hashlib.sha256(ssl.PEM_cert_to_DER_cert(p[p.index('-----BEGIN'):] + '-----END CERTIFICATE-----\n')).hexdigest()
           for p in pems}
    assert fps == EXPECTED


def test_context_verifies_and_trusts_the_bundled_roots():
    ctx = preview_cdn.tls_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    subjects = {dict(x[0] for x in c['subject']).get('commonName') for c in ctx.get_ca_certs()}
    assert {'ISRG Root X1', 'ISRG Root X2', 'GTS Root R1', 'GTS Root R4'} <= subjects
    assert preview_cdn.tls_context() is ctx  # built once


def test_fetch_master_passes_the_context(monkeypatch):
    seen = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return b'png'

    def fake_urlopen(request, timeout=None, context=None):
        seen['context'] = context
        return Resp()

    monkeypatch.setattr(preview_cdn.urllib.request, 'urlopen', fake_urlopen)
    monkeypatch.delenv('SPB_PREVIEW_CDN_OFF', raising=False)
    assert preview_cdn.fetch_master('0' * 64 + '.png') == b'png'
    assert seen['context'] is preview_cdn.tls_context()
