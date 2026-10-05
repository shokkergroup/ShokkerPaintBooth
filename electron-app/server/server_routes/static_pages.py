"""Static HTML page routes for Shokker Paint Booth.

These routes were extracted from server.py so page-serving tweaks can happen in
a small module without loading the full render/API server.
"""

from __future__ import annotations

import os
import time

from flask import Response, request, send_file


def register_static_page_routes(app, *, server_dir: str, bundle_dir: str) -> None:
    """Register the root Paint Booth and standalone HTML page routes."""

    @app.route('/SPB_AUDIT_astra.html')
    def astra_owner_review():
        # SPB-105 / ASTRA: local read-only evidence.
        review_path = os.path.join(server_dir, 'SPB_AUDIT_astra.html')
        if not os.path.isfile(review_path):
            return Response('ASTRA owner review is available in the development workspace.', status=404)
        return send_file(review_path)

    @app.route('/SPB_AUDIT_coreworks.html')
    def coreworks_owner_review():
        # SPB-105 / CORE-WORKS: read-only local before/actual-output evidence.
        review_path = os.path.join(server_dir, 'SPB_AUDIT_coreworks.html')
        if not os.path.isfile(review_path):
            return Response('SHOKK WORKS review is available in the development workspace.', status=404)
        return send_file(review_path)

    @app.route('/')
    @app.route('/paint-booth-v2.html')
    def serve_paint_booth():
        """Serve the Paint Booth UI at the root URL (and at its literal filename).

        SPB 2026-06-08: also bind /paint-booth-v2.html so sub-tools (Spec Sculpt etc.)
        that link back to that filename resolve to the HTML instead of falling through
        to the server_v5 catch-all (which only serves .js/.css/.png/.svg/.ico and 404s
        everything else with a not_found JSON). This literal rule outranks the
        /<path:filename> catch-all in Werkzeug, so it wins.
        """
        for candidate in [
            os.path.join(server_dir, 'paint-booth-v2.html'),
            os.path.join(bundle_dir, 'paint-booth-v2.html'),
            os.path.join(server_dir, '..', 'app', 'paint-booth-v2.html'),
        ]:
            if os.path.exists(candidate):
                try:
                    with open(os.path.abspath(candidate), 'r', encoding='utf-8') as hf:
                        html_content = hf.read()
                    html_content = html_content.replace(
                        '</head>',
                        f'<!-- FLASK-SERVED-BUILD-27 PID={os.getpid()} TIME={time.strftime("%H:%M:%S")} -->\n</head>',
                        1,
                    )
                    return Response(html_content, mimetype='text/html')
                except Exception:
                    return send_file(os.path.abspath(candidate), mimetype='text/html')
        return "Paint Booth HTML not found", 404

    @app.route('/finish-viewer.html')
    def serve_finish_viewer():
        for candidate in [
            os.path.join(server_dir, 'finish-viewer.html'),
            os.path.join(bundle_dir, 'finish-viewer.html'),
        ]:
            if os.path.exists(candidate):
                return send_file(os.path.abspath(candidate), mimetype='text/html')
        return "Finish Viewer HTML not found", 404

    @app.route('/SPB_PATTERN_AUDIT.html')
    @app.route('/SPB_PATTERN_QUALITY_REVIEW.html')
    def serve_pattern_audit_page():
        page_name = os.path.basename(request.path)
        for candidate in [
            os.path.join(server_dir, page_name),
            os.path.join(bundle_dir, page_name),
        ]:
            if os.path.exists(candidate):
                return send_file(os.path.abspath(candidate), mimetype='text/html')
        return f"{page_name} not found", 404

    @app.route('/spec-sculpt.html')
    def serve_spec_sculpt_lab():
        """Standalone Spec Sculpt Lab UI (full-page tool, same hosting pattern as Paint Lab)."""
        for candidate in [
            os.path.join(server_dir, 'spec-sculpt.html'),
            os.path.join(bundle_dir, 'spec-sculpt.html'),
        ]:
            if os.path.exists(candidate):
                return send_file(os.path.abspath(candidate), mimetype='text/html')
        return "Spec Sculpt Lab HTML not found", 404

    def _serve_html_page(page_name: str, not_found_label: str):
        for candidate in [
            os.path.join(server_dir, page_name),
            os.path.join(bundle_dir, page_name),
        ]:
            if os.path.exists(candidate):
                return send_file(os.path.abspath(candidate), mimetype='text/html')
        return f"{not_found_label} not found", 404

    @app.route('/spec-sculpt-audit.html')
    def serve_spec_sculpt_audit():
        """Spec Sculpt preset AUDIT tool — owner triage (KEEP/REBUILD/RENAME/BUILD NEW).
        Self-contained page (thumbnails embedded); Save posts to /api/spec-sculpt/audit."""
        return _serve_html_page('spec-sculpt-audit.html', 'Spec Sculpt Audit HTML')

    @app.route('/shokk-drop.html')
    def serve_shokk_drop_lab():
        """SHOKK DROP — import art, DNA spec, share .spbdrop packs."""
        return _serve_html_page('shokk-drop.html', 'Shokk Drop HTML')

    @app.route('/auto-painter.html')
    def serve_auto_painter_lab():
        """AUTO PAINTER (Shokk Trace) — turn an iRacing template into editable zones.
        SPB-AUTOPAINT-001: was 404ing because no route existed here (unlike the other
        sideload tools). Same hosting pattern as shokk-drop.html."""
        return _serve_html_page('auto-painter.html', 'Auto Painter HTML')

    @app.route('/forge-page.html')
    def serve_shokk_forge():
        """Guided SHOKK FORGE intake/reconstruction page."""
        return _serve_html_page('forge-page.html', 'SHOKK FORGE HTML')

    @app.route('/SHOKK_DROP_BIBLE.html')
    def serve_shokk_drop_bible():
        """SHOKK DROP product bible — architecture, roadmap, API map (SPB-109)."""
        return _serve_html_page('SHOKK_DROP_BIBLE.html', 'Shokk Drop Bible HTML')

    @app.route('/user-imports-gallery.html')
    def serve_user_imports_gallery_redirect():
        """Legacy gallery URL → shokk-drop.html (or redirect stub)."""
        return _serve_html_page('user-imports-gallery.html', 'Shokk Drop HTML')
