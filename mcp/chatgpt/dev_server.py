"""Private ChatGPT integration host. Explicitly refuses the owner's live port."""
import argparse
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import re
import subprocess
import types


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=59910)
    parser.add_argument('--candidate-routing', action='store_true')
    parser.add_argument('--candidate-psd-raster', action='store_true')
    parser.add_argument('--candidate-layer-visibility', action='store_true')
    parser.add_argument('--candidate-knowledge', action='store_true')
    parser.add_argument('--candidate-editor-actions', action='store_true')
    parser.add_argument('--candidate-polite-redo', action='store_true')
    parser.add_argument('--candidate-redo-empty', action='store_true')
    parser.add_argument('--candidate-output-advice', action='store_true')
    parser.add_argument('--candidate-topic-readiness', action='store_true')
    parser.add_argument('--topic-cars-fail-first', action='store_true')
    parser.add_argument('--candidate-concise-reference', action='store_true')
    parser.add_argument('--candidate-reference-history', action='store_true')
    parser.add_argument('--candidate-paint-availability', action='store_true')
    parser.add_argument('--candidate-reference-dock', action='store_true')
    parser.add_argument('--topic-cars-controlled', action='store_true')
    parser.add_argument('--prepared-browser', action='store_true', help='Serve hash-verified physical frontend files without HTML injection')
    args = parser.parse_args()
    if not 59910 <= args.port <= 59999:
        parser.error('Use a dedicated development port in 59910..59999.')
    root = Path(__file__).resolve().parents[2]
    prepared_dir = Path(__file__).resolve().parent / 'prepared-browser/server'
    prepared_manifest = None
    if args.prepared_browser:
        subprocess.run(['node', str(Path(__file__).resolve().parent / 'prepared-browser/verify.cjs')], check=True)
        prepared_manifest = json.loads((prepared_dir.parent / 'manifest.json').read_bytes())
    if args.candidate_routing:
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / 'car-knowledge/build_knowledge.py'), '--check'], cwd=root, check=True)
    state = root / '_codex_mcp_work' / 'chatgpt-dev' / str(args.port)
    output = root / '_release_evidence' / 'chatgpt-dev' / str(args.port)
    state.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    os.environ.update(SHOKKER_PORT=str(args.port), SHOKKER_NO_CLEAN='1',
                      SPB_NO_LIVE_LINK='1', SPB_ISOLATED_OUTPUT_DIR=str(output),
                      SPB_MCP_DIR=str(state / 'pairing'), SPB_AI_LOG_DIR=str(output / 'ai_logs'), PYTHONHASHSEED='0')
    sys.path.insert(0, str(root))
    from config import CFG
    # Test-only configuration before importing any application module.
    CFG.CONFIG_FILE = str(state / 'shokker_config.json')
    CFG.SHOKK_LIBRARY_DIR = str(state / 'shokk_library')
    CFG.SHOKK_FACTORY_DIR = str(state / 'shokk_factory')
    # Project testing must never list or write the customer's real project library.
    import server_routes.project_routes as project_routes
    project_routes._default_projects_dir = lambda: str(output / 'projects')
    candidates = Path(__file__).resolve().parent / 'candidates'
    knowledge_overlay = {}
    if args.candidate_knowledge:
        from fresh_knowledge_overlay import load as load_knowledge_overlay
        knowledge_overlay = load_knowledge_overlay(args.port)
    if args.candidate_editor_actions:
        from editor_action_overlay import load as load_editor_action_overlay
        knowledge_overlay.update(load_editor_action_overlay(args.port))
    if args.candidate_polite_redo:
        if not args.candidate_editor_actions:
            parser.error('Polite Redo requires the tested editor-actions overlay.')
        from editor_action_overlay import polite_redo
        knowledge_overlay.update(polite_redo(args.port, knowledge_overlay))
    if args.candidate_redo_empty:
        if not args.candidate_polite_redo:
            parser.error('Empty Redo requires the tested polite-redo overlay.')
        from editor_action_overlay import empty_redo
        knowledge_overlay.update(empty_redo(args.port, knowledge_overlay))
    if args.candidate_output_advice:
        if not args.candidate_redo_empty:
            parser.error('Output advice requires the tested empty-redo overlay.')
        from editor_action_overlay import output_advice
        knowledge_overlay.update(output_advice(args.port, knowledge_overlay))
    if args.candidate_topic_readiness:
        if not args.candidate_output_advice:
            parser.error('Topic readiness requires the tested output-advice overlay.')
        from editor_action_overlay import topic_readiness
        knowledge_overlay.update(topic_readiness(args.port, knowledge_overlay))
    if args.topic_cars_fail_first and (not args.candidate_topic_readiness or args.port != 59910):
        parser.error('Car-read refusal fixture requires private59910 topic readiness.')
    topic_refusal = {'remaining': 1 if args.topic_cars_fail_first else 0}
    if args.candidate_concise_reference:
        if not args.candidate_topic_readiness:
            parser.error('Concise reference requires the tested topic overlay.')
        from editor_action_overlay import concise_reference
        knowledge_overlay.update(concise_reference(args.port, knowledge_overlay))
    if args.candidate_reference_history:
        if not args.candidate_concise_reference:
            parser.error('Reference history requires concise/readiness predecessors.')
        from editor_action_overlay import reference_history
        knowledge_overlay.update(reference_history(args.port, knowledge_overlay))
    if args.candidate_paint_availability:
        if not args.candidate_reference_history:
            parser.error('Paint availability requires the accepted reference-history caller.')
        from editor_action_overlay import paint_availability
        knowledge_overlay.update(paint_availability(args.port, knowledge_overlay))
    if args.candidate_reference_dock:
        if not args.candidate_paint_availability:
            parser.error('Reference dock requires the accepted paintability predecessor.')
        from editor_action_overlay import reference_dock
        knowledge_overlay.update(reference_dock(args.port, knowledge_overlay))
    if args.topic_cars_controlled and (not args.candidate_topic_readiness or args.port != 59910):
        parser.error('Controlled car fixture requires private59910 topic readiness.')
    topic_control_path = Path(__file__).resolve().parent / 'body-output-consistency/concise-reference/native-control.json'
    visibility_candidate = None
    if args.candidate_layer_visibility:
        from layer_visibility_candidate import candidate as visibility_proposal
        visibility_path = root / 'js/canvas/layer/clipping-mask.js'
        visibility_source = visibility_proposal(visibility_path.read_text(encoding='utf-8'))
        visibility_candidate = {'source_sha256': hashlib.sha256(visibility_path.read_bytes()).hexdigest(),
                                'candidate_sha256': hashlib.sha256(visibility_source.encode()).hexdigest()}
    if args.candidate_routing:
        for stem in ('mcp_bridge_routes', 'v5_entrypoint_security'):
            name = 'server_routes.' + stem
            spec = importlib.util.spec_from_file_location(name, candidates / (stem + '.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.__file__ = str(root / 'server_routes' / (stem + '.py'))
            sys.modules[name] = module
    raster_candidate = None
    if args.candidate_psd_raster:
        from psd_raster_candidate import candidate
        source_path = root / 'server_routes' / 'psd_import_routes.py'
        original = source_path.read_text(encoding='utf-8')
        proposed = candidate(original)
        name = 'server_routes.psd_import_routes'
        module = types.ModuleType(name)
        module.__file__ = str(source_path)
        module.__package__ = 'server_routes'
        exec(compile(proposed, str(source_path), 'exec'), module.__dict__)
        sys.modules[name] = module
        raster_candidate = {'source_sha256': hashlib.sha256(original.encode()).hexdigest(),
                            'candidate_sha256': hashlib.sha256(proposed.encode()).hexdigest()}
    import server_v5
    from flask import request, send_file, Response, jsonify
    if args.prepared_browser:
        @server_v5.app.before_request
        def physical_prepared_frontend():
            relative = 'paint-booth-v2.html' if request.path == '/' else request.path.lstrip('/')
            if args.topic_cars_controlled and relative == 'data/encyclopedia/cars.json':
                from prepared_browser_fixture import spec
                fixture = spec(args.port, relative, json.loads(topic_control_path.read_bytes()))
                if fixture['delay_ms']:
                    import time
                    time.sleep(fixture['delay_ms'] / 1000)
                if fixture['refuse']:
                    server_v5.app.logger.warning('PREPARED_CAR_FIXTURE: physical car read refused')
                    return jsonify(error='Private prepared car-read failure fixture'), 503
            item = prepared_manifest['files'].get(relative)
            if item:
                raw = (prepared_dir / relative).read_bytes()
                if hashlib.sha256(raw).hexdigest() != item['sha256']:
                    return jsonify(error='Prepared browser file drift'), 409
                return send_file(prepared_dir / relative, max_age=0, conditional=False,
                                 etag=False), 200, {'X-SPB-Prepared-Browser': item['sha256'], 'Cache-Control': 'no-store'}
            # Never hide a missing frontend dependency by falling through to development files.
            if relative.endswith(('.js', '.css')) or relative.startswith('data/encyclopedia/'):
                return jsonify(error='Absent from prepared browser snapshot', path=relative), 404
    if args.candidate_routing:
        @server_v5.app.before_request
        def private_candidate_script():
            if request.path in knowledge_overlay:
                asset = knowledge_overlay[request.path]
                return Response(asset['bytes'], mimetype='application/json' if request.path.endswith('.json') else 'text/javascript',
                                headers={'Cache-Control': 'no-store', 'X-SPB-Private-Knowledge': asset['sha256']})
            if request.path == '/js/spb-convo-state.js':
                return send_file(candidates / 'spb-convo-state.js', max_age=0, conditional=False)
            if request.path == '/js/ui/spb-nuq-fix.js':
                return send_file(candidates / 'spb-nuq-fix.js', max_age=0, conditional=False)
            if request.path in ('/js/spb-intent-model.js', '/js/spb-intent-frame.js', '/js/spb-intent-plan.js'):
                return send_file(candidates / Path(request.path).name, max_age=0, conditional=False)
            if request.path == '/js/canvas/layer/clipping-mask.js' and visibility_candidate:
                return Response(visibility_source, mimetype='text/javascript', headers={'Cache-Control': 'no-store'})
            if request.path in ('/mcp/chatgpt/panel-location.js', '/mcp/chatgpt/layer-colour-followup.js', '/mcp/chatgpt/element-resize-scope.js', '/mcp/chatgpt/editor-capabilities.js', '/mcp/chatgpt/offline-ready.js', '/mcp/chatgpt/design-intent.js', '/mcp/chatgpt/preserved-colours.js', '/mcp/chatgpt/layer-targets.js', '/mcp/chatgpt/native-layer-colour.js', '/mcp/chatgpt/colour-report-scope.js', '/mcp/chatgpt/conversation-scope.js', '/mcp/chatgpt/design-brief.js', '/mcp/chatgpt/car-knowledge/core.js', '/mcp/chatgpt/car-knowledge/live-identity.js', '/mcp/chatgpt/car-knowledge/layer-reading.js', '/mcp/chatgpt/car-knowledge/offline-answer.js'):
                return send_file(root / request.path.lstrip('/'), max_age=0, conditional=False)
            if request.path == '/data/encyclopedia/cars.json':
                if args.topic_cars_controlled:
                    control = json.loads(topic_control_path.read_bytes())
                    delay = max(0, min(8000, int(control.get('delay_ms', 0))))
                    if delay:
                        import time
                        time.sleep(delay / 1000)
                    if control.get('refuse') is True:
                        server_v5.app.logger.warning('PRIVATE_TOPIC_CONTROL: car reference read refused')
                        return jsonify(error='Private car-reference failure fixture.'), 503
                    server_v5.app.logger.warning('PRIVATE_TOPIC_CONTROL: verified car reference read allowed')
                if topic_refusal['remaining']:
                    topic_refusal['remaining'] -= 1
                    server_v5.app.logger.warning('PRIVATE_TOPIC_FIXTURE: one car article read refused; later reads use verified bundle')
                    return jsonify(error='Private readiness test: retry car reference.'), 503
                build = Path(__file__).resolve().parent / 'car-knowledge/build'
                try:
                    manifest = json.loads((build / 'manifest.json').read_bytes())
                    raw = (build / 'cars.json').read_bytes()
                    if manifest['schema'] != 'spb-car-build/1' or hashlib.sha256(raw).hexdigest() != manifest['outputs']['cars.json']:
                        raise ValueError('Mixed car knowledge generation')
                    return Response(raw, mimetype='application/json', headers={'Cache-Control': 'no-store'})
                except (OSError, ValueError, KeyError):
                    return jsonify(error='Car reference is being rebuilt; please retry.'), 503
            if request.path in ('/js/spb-mcp-bridge.js', '/js/spb-ai-connect.js', '/js/spb-offline-answer.js', '/js/spb-offline-builder.js', '/js/spb-pbn.js', '/js/spb-pro-ai.js', '/js/spb-pro-edit.js', '/js/spb-pro-zone-kit.js', '/js/spb-intent-report.js', '/js/spb-mcp-frames.js', '/js/spb-pro-carmap.js', '/paint-booth-3-canvas.js', '/js/features/spb-projects.js'):
                return send_file(candidates / Path(request.path).name, max_age=0, conditional=False)

    @server_v5.app.after_request
    def private_dev_label(response):
        if args.prepared_browser:
            return response
        if request.path in ('/', '/paint-booth-v2.html') and response.mimetype == 'text/html':
            response.direct_passthrough = False
            html = response.get_data(as_text=True)
            if args.candidate_routing:
                extra = ['panel-location.js', 'layer-colour-followup.js', 'element-resize-scope.js', 'editor-capabilities.js', 'offline-ready.js', 'design-intent.js', 'preserved-colours.js', 'layer-targets.js', 'native-layer-colour.js', 'colour-report-scope.js', 'conversation-scope.js', 'design-brief.js', 'car-knowledge/core.js', 'car-knowledge/live-identity.js', 'car-knowledge/layer-reading.js', 'car-knowledge/offline-answer.js']
                scripts = ''.join('<script src="/mcp/chatgpt/' + name + '?v=' + hashlib.sha256((Path(__file__).resolve().parent / name).read_bytes()).hexdigest()[:12] + '"></script>' for name in extra)
                html = html.replace('</body>', scripts + '</body>')
                def version(match):
                    name = match.group(1).split('?')[0].split('/')[-1]
                    digest = hashlib.sha256((candidates / name).read_bytes()).hexdigest()[:12]
                    return match.group(1) + 'chatgpt-dev-' + digest
                html = re.sub(r'(js/ui/spb-nuq-fix\.js\?v=)[^"\s]+', version, html)
                html = re.sub(r'(js/spb-convo-state\.js\?v=)[^"\s]+', version, html)
                html = re.sub(r'((?:js/spb-(?:ai-connect|offline-answer|offline-builder|pbn|pro-ai|pro-edit|pro-zone-kit|intent-report|intent-model|intent-frame|intent-plan|mcp-frames|mcp-bridge|pro-carmap)|paint-booth-3-canvas|js/features/spb-projects)\.js\?v=)[^"\s]+', version, html)
            for route, asset in knowledge_overlay.items():
                if route.endswith('.js'):
                    html = re.sub('(' + re.escape(route.lstrip('/')) + r'\?v=)[^"\s]+',
                                  lambda m: m.group(1) + 'knowledge-' + asset['sha256'][:12], html)
            html = html.replace('</body>', '<div style="position:fixed;right:10px;bottom:4px;z-index:2147483647;background:#183747;color:#fff;padding:3px 8px;font:12px sans-serif">CHATGPT DEVELOPMENT · ' + str(args.port) + '</div></body>')
            response.set_data(html)
        return response
    metadata = {'pid': os.getpid(), 'port': args.port, 'host': '127.0.0.1',
                'pairing_dir': os.environ['SPB_MCP_DIR'], 'output': str(output),
                'config': CFG.CONFIG_FILE, 'runtime': 'server_v5.app', 'candidate_routing': args.candidate_routing}
    metadata['psd_raster_candidate'] = raster_candidate
    metadata['layer_visibility_candidate'] = visibility_candidate
    metadata['knowledge_overlay'] = {name: item['sha256'] for name, item in knowledge_overlay.items()}
    metadata['prepared_browser'] = {'enabled': args.prepared_browser, 'html_injection': False if args.prepared_browser else None,
        'manifest_sha256': hashlib.sha256((prepared_dir.parent / 'manifest.json').read_bytes()).hexdigest() if args.prepared_browser else None}
    metadata['prepared_car_fixture'] = {'enabled': bool(args.prepared_browser and args.topic_cars_controlled), 'max_delay_ms': 8000}
    (state / 'server.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    # Importing V5 and serving its app avoids its production startup/port-file hooks.
    server_v5.app.run(host='127.0.0.1', port=args.port, threaded=True,
                      debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
