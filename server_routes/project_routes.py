# -*- coding: utf-8 -*-
"""SPB Layered Workflow project files (``.spbproj``).

Version 2 projects preserve every live layer raster, including edited layers
that originated in a PSD. The routes retain read compatibility with version 1
JSON projects and add a bounded, ordered chunk upload for projects larger than
Flask's app-wide request limit.

Stored next to the SHOKK Library: ``~/Documents/Shokker Paint Booth/SPB Projects``
"""
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
from server_routes._swallow import swallow as _spb_swallow  # [2026-09-05 F4] counted swallows


PROJECT_SCHEMA_VERSION = 2
PROJECT_VERSION = "2.0"
MAX_PROJECT_BYTES = 256 * 1024 * 1024
MAX_CHUNK_BYTES = 4 * 1024 * 1024
UPLOAD_TTL_SECONDS = 60 * 60


def _default_projects_dir():
    return os.path.join(os.path.expanduser("~"), "Documents",
                        "Shokker Paint Booth", "SPB Projects")


def _safe_name(name):
    clean = re.sub(r'[^A-Za-z0-9 _\-()\[\]]+', '_', str(name or '')).strip()
    return clean[:80] or 'Untitled Project'


def _source_fingerprint(path):
    """Return a content identity without trusting client-supplied metadata."""
    raw = str(path or '').strip()
    if not raw:
        return {"exists": False, "error": "missing_source_path"}
    normalized = os.path.abspath(os.path.normpath(
        os.path.expandvars(os.path.expanduser(raw))))
    if not os.path.isfile(normalized):
        return {
            "exists": False,
            "error": "source_not_found",
            "path": normalized,
        }
    try:
        stat = os.stat(normalized)
        digest = hashlib.sha256()
        with open(normalized, 'rb') as source:
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as error:
        return {
            "exists": False,
            "error": "source_unreadable",
            "detail": str(error),
            "path": normalized,
        }
    return {
        "exists": True,
        "algorithm": "sha256",
        "sha256": digest.hexdigest(),
        "size": stat.st_size,
        "mtimeNs": getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1e9)),
        "path": normalized,
    }


def _fingerprints_match(expected, current):
    if not isinstance(expected, dict) or not expected.get('sha256'):
        return None
    if not isinstance(current, dict) or not current.get('exists'):
        return False
    return (expected.get('algorithm', 'sha256') == 'sha256'
            and expected.get('sha256') == current.get('sha256')
            and int(expected.get('size', -1)) == int(current.get('size', -2)))


def register_project_routes(
        app, logger, projects_dir_getter=None, external_write_guard=None):
    from flask import jsonify, request

    uploads = {}
    uploads_lock = threading.Lock()

    def _dir():
        d = (projects_dir_getter() if projects_dir_getter else None) or _default_projects_dir()
        # GET/read routes historically initialized this directory. Verification
        # mode must stay read-only, so skip that convenience mkdir when the
        # shared path-aware policy identifies this as external storage.
        denial = (external_write_guard(d, "project-storage-init")
                  if external_write_guard is not None else None)
        if not denial:
            os.makedirs(d, exist_ok=True)
        return d

    @app.before_request
    def _guard_project_mutations():
        if external_write_guard is None:
            return None
        path = request.path
        writes = (
            path == "/api/projects/save"
            or path == "/api/projects/save/start"
            or path.startswith("/api/projects/save/chunk/")
            or path.startswith("/api/projects/save/commit/")
            or path.startswith("/api/projects/save/abort/")
            or path == "/api/projects/delete"
        )
        if not writes:
            return None
        denial = external_write_guard(
            (projects_dir_getter() if projects_dir_getter else None)
            or _default_projects_dir(),
            "project-storage",
        )
        if denial:
            return jsonify(denial), 403
        return None

    def _project_path(filename):
        fn = os.path.basename(str(filename or ''))
        if not fn.lower().endswith('.spbproj'):
            raise ValueError("not a .spbproj file")
        full = os.path.abspath(os.path.join(_dir(), fn))
        root = os.path.abspath(_dir())
        if os.path.commonpath([root, full]) != root:
            raise ValueError("project path escaped project directory")
        if os.path.islink(full):
            raise ValueError("project symlinks are not supported")
        return fn, full

    def _metadata_path(full):
        return full + '.meta.json'

    def _read_current_metadata(full):
        meta_file = _metadata_path(full)
        if not os.path.isfile(meta_file):
            return None
        with io.open(meta_file, encoding='utf-8') as source:
            meta = json.load(source)
        actual_size = os.path.getsize(full)
        actual_modified = os.path.getmtime(full)
        if (int(meta.get('size', -1)) != actual_size or
                abs(float(meta.get('modified', -1)) - actual_modified) > 0.000001):
            return None
        return meta

    def _project_metadata(project, full=None):
        config = project.get('config') if isinstance(project.get('config'), dict) else {}
        source = str(project.get('sourcePaintFile') or
                     config.get('sourcePaintFile') or '')
        entry = {
            "name": project.get('name') or '',
            "sourcePaintFile": source,
            "zoneCount": len(config.get('zones') or []),
            "layerCount": len(project.get('layers') or []),
            "schemaVersion": project.get('schemaVersion') or 1,
            "version": project.get('version') or '1.0',
            "sourceFingerprint": project.get('sourceFingerprint'),
        }
        if full and os.path.exists(full):
            entry.update({
                "modified": os.path.getmtime(full),
                "size": os.path.getsize(full),
            })
        return entry

    def _write_json_atomic(full, value):
        tmp = full + '.tmp-' + secrets.token_hex(8)
        try:
            encoded = json.dumps(value, ensure_ascii=False,
                                 separators=(',', ':')).encode('utf-8')
            if len(encoded) > MAX_PROJECT_BYTES:
                raise ValueError(
                    "project is too large (%d MB; maximum is %d MB)" %
                    (len(encoded) // (1024 * 1024),
                     MAX_PROJECT_BYTES // (1024 * 1024)))
            with open(tmp, 'wb') as output:
                output.write(encoded)
                output.flush()
                os.fsync(output.fileno())
            os.replace(tmp, full)
            return len(encoded)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError as _spb_ex:
                    _spb_swallow('_write_json_atomic@L197', _spb_ex)

    def _validate_project(project):
        if not isinstance(project, dict):
            raise ValueError("missing project payload")
        try:
            schema = int(project.get('schemaVersion') or 1)
        except (TypeError, ValueError):
            raise ValueError("project schema version is invalid")
        if schema < 1 or schema > PROJECT_SCHEMA_VERSION:
            raise ValueError("project schema %s is not supported by this build" % schema)
        config = project.get('config')
        if not isinstance(config, dict):
            raise ValueError("project config is missing or invalid")
        layers = project.get('layers', [])
        if not isinstance(layers, list):
            raise ValueError("project layers must be a list")
        if len(layers) > 5000:
            raise ValueError("project has too many layers")
        layer_ids = set()
        for index, layer in enumerate(layers):
            if not isinstance(layer, dict):
                raise ValueError("project layer %d is invalid" % index)
            if schema >= 2:
                layer_id = layer.get('id')
                if not isinstance(layer_id, str) or not layer_id.strip():
                    raise ValueError("project layer %d has no stable id" % index)
                if layer_id in layer_ids:
                    raise ValueError("project has duplicate layer id: %s" % layer_id)
                layer_ids.add(layer_id)
            image = layer.get('imgData')
            if image is not None and (not isinstance(image, str) or
                                      not image.startswith('data:image/png;base64,')):
                raise ValueError("project layer %d has invalid pixel data" % index)
            if schema >= 2 and layer.get('pixelState') == 'embedded' and not image:
                raise ValueError("project layer %d is missing embedded pixels" % index)
        selected = project.get('selectedLayerId')
        if schema >= 2 and selected is not None and selected not in layer_ids:
            raise ValueError("project selected Layer does not exist in the saved stack")

    def _save_project_envelope(envelope):
        if not isinstance(envelope, dict):
            raise ValueError("invalid save request")
        project = envelope.get('project')
        _validate_project(project)
        incoming_schema = int(project.get('schemaVersion') or 1)
        name = _safe_name(envelope.get('name') or project.get('name'))
        project['name'] = name
        project['_spb_project'] = True
        # A pre-v2 client did not serialize stable IDs or every live raster.
        # Preserve that schema rather than falsely labelling an incomplete v1
        # payload as lossless. Opening and saving through the v2 client upgrades
        # it because that client constructs a fresh complete payload.
        project['schemaVersion'] = incoming_schema
        project['version'] = PROJECT_VERSION if incoming_schema >= 2 else '1.0'
        project['modified'] = time.time()
        project.setdefault('created', project['modified'])

        source = (project.get('sourcePaintFile') or
                  (project.get('config') or {}).get('sourcePaintFile') or '')
        source_identity = _source_fingerprint(source)
        if not source_identity.get('exists'):
            raise FileNotFoundError(
                "source paint is unavailable; project was not saved: %s" %
                (source_identity.get('path') or source or '(no path)'))
        project['sourcePaintFile'] = source
        project['sourceFingerprint'] = {
            key: source_identity[key]
            for key in ('algorithm', 'sha256', 'size', 'mtimeNs')
        }

        _, full = _project_path(name + '.spbproj')
        byte_count = _write_json_atomic(full, project)
        metadata = _project_metadata(project, full)
        metadata_warning = None
        try:
            _write_json_atomic(_metadata_path(full), metadata)
        except Exception as error:
            # The sidecar only keeps list views from parsing embedded PNGs. The
            # atomic .spbproj is already durable, so never report a false save
            # failure because this optional cache could not be written.
            metadata_warning = "project saved, metadata cache failed: %s" % error
            logger.warning("[projects] %s" % metadata_warning)
        logger.info("[projects] saved '%s' (%d bytes)" % (name, byte_count))
        return {
            "ok": True,
            "file": os.path.basename(full),
            "path": full,
            "bytes": byte_count,
            "schemaVersion": incoming_schema,
            "sourceFingerprint": project['sourceFingerprint'],
            "warning": metadata_warning,
        }

    def _load_project(full):
        size = os.path.getsize(full)
        if size > MAX_PROJECT_BYTES:
            raise ValueError("project exceeds the %d MB safety limit" %
                             (MAX_PROJECT_BYTES // (1024 * 1024)))
        with io.open(full, encoding='utf-8') as source:
            project = json.load(source)
        _validate_project(project)
        if not project.get('_spb_project'):
            raise ValueError("file is not an SPB project")
        return project

    def _source_status(project):
        source = (project.get('sourcePaintFile') or
                  (project.get('config') or {}).get('sourcePaintFile') or '')
        current = _source_fingerprint(source)
        expected = project.get('sourceFingerprint')
        matches = _fingerprints_match(expected, current)
        return {
            "requestedPath": source,
            "exists": bool(current.get('exists')),
            "matchesSavedFingerprint": matches,
            "legacyUnverified": matches is None,
            "expected": expected if isinstance(expected, dict) else None,
            "current": {
                key: current.get(key)
                for key in ('algorithm', 'sha256', 'size', 'mtimeNs')
                if current.get(key) is not None
            } if current.get('exists') else None,
            "error": current.get('error'),
        }

    def _cleanup_uploads():
        cutoff = time.time() - UPLOAD_TTL_SECONDS
        stale = []
        with uploads_lock:
            for token, state in list(uploads.items()):
                if state['created'] < cutoff:
                    stale.append(uploads.pop(token))
        for state in stale:
            try:
                os.remove(state['tmp'])
            except OSError as _spb_ex:
                _spb_swallow('_cleanup_uploads@L334', _spb_ex)

    @app.route('/api/projects/list', methods=['GET'])
    def api_projects_list():
        try:
            d = _dir()
            if not os.path.isdir(d):
                return jsonify({"ok": True, "projects": [], "dir": d})
            out = []
            for fn in sorted(os.listdir(d)):
                if not fn.lower().endswith('.spbproj'):
                    continue
                full = os.path.join(d, fn)
                entry = {
                    "file": fn,
                    "name": os.path.splitext(fn)[0],
                    "modified": os.path.getmtime(full),
                    "size": os.path.getsize(full),
                }
                try:
                    meta = _read_current_metadata(full)
                    if meta is None:
                        meta = _project_metadata(_load_project(full), full)
                    for key in ('name', 'sourcePaintFile', 'zoneCount',
                                'layerCount', 'schemaVersion', 'version',
                                'modified', 'size'):
                        if key in meta:
                            entry[key] = meta[key]
                    source_path = entry.get('sourcePaintFile') or ''
                    entry['sourceAvailable'] = bool(source_path and
                                                    os.path.isfile(source_path))
                except Exception:
                    entry["corrupt"] = True
                out.append(entry)
            out.sort(key=lambda value: -value.get("modified", 0))
            return jsonify({"ok": True, "projects": out, "dir": d})
        except Exception as error:
            logger.error("/api/projects/list error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/save', methods=['POST'])
    def api_projects_save():
        try:
            data = request.get_json(silent=True)
            return jsonify(_save_project_envelope(data))
        except FileNotFoundError as error:
            return jsonify({"error": str(error), "code": "source_unavailable"}), 409
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_project"}), 400
        except Exception as error:
            logger.error("/api/projects/save error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/save/start', methods=['POST'])
    def api_projects_save_start():
        _cleanup_uploads()
        try:
            data = request.get_json(silent=True) or {}
            total = int(data.get('totalBytes') or 0)
            if total <= 0 or total > MAX_PROJECT_BYTES:
                raise ValueError("project upload size must be between 1 byte and %d MB" %
                                 (MAX_PROJECT_BYTES // (1024 * 1024)))
            token = secrets.token_hex(24)
            tmp = os.path.join(_dir(), '._spb-project-upload-' + token + '.tmp')
            with open(tmp, 'xb'):
                pass
            with uploads_lock:
                uploads[token] = {
                    "tmp": tmp,
                    "total": total,
                    "bytes": 0,
                    "nextIndex": 0,
                    "created": time.time(),
                }
            return jsonify({
                "ok": True,
                "uploadId": token,
                "chunkBytes": MAX_CHUNK_BYTES,
            })
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_upload"}), 400
        except Exception as error:
            logger.error("/api/projects/save/start error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/save/chunk/<upload_id>', methods=['POST'])
    def api_projects_save_chunk(upload_id):
        try:
            index = int(request.headers.get('X-SPB-Chunk-Index', '-1'))
            block = request.get_data(cache=False)
            if not block or len(block) > MAX_CHUNK_BYTES:
                raise ValueError("project chunk is empty or exceeds the chunk limit")
            with uploads_lock:
                state = uploads.get(upload_id)
                if not state:
                    return jsonify({"error": "upload session not found",
                                    "code": "upload_not_found"}), 404
                if index != state['nextIndex']:
                    raise ValueError("out-of-order project chunk")
                if state['bytes'] + len(block) > state['total']:
                    raise ValueError("project upload exceeds declared size")
                with open(state['tmp'], 'ab') as output:
                    output.write(block)
                state['bytes'] += len(block)
                state['nextIndex'] += 1
                received = state['bytes']
            return jsonify({"ok": True, "received": received})
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_chunk"}), 409
        except Exception as error:
            logger.error("/api/projects/save/chunk error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/save/commit/<upload_id>', methods=['POST'])
    def api_projects_save_commit(upload_id):
        state = None
        try:
            with uploads_lock:
                state = uploads.pop(upload_id, None)
            if not state:
                return jsonify({"error": "upload session not found",
                                "code": "upload_not_found"}), 404
            if state['bytes'] != state['total']:
                raise ValueError("project upload is incomplete (%d/%d bytes)" %
                                 (state['bytes'], state['total']))
            with io.open(state['tmp'], encoding='utf-8') as source:
                envelope = json.load(source)
            return jsonify(_save_project_envelope(envelope))
        except FileNotFoundError as error:
            return jsonify({"error": str(error), "code": "source_unavailable"}), 409
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            return jsonify({"error": str(error), "code": "invalid_project"}), 400
        except Exception as error:
            logger.error("/api/projects/save/commit error: %s" % error)
            return jsonify({"error": str(error)}), 500
        finally:
            if state:
                try:
                    os.remove(state['tmp'])
                except OSError as _spb_ex:
                    _spb_swallow('api_projects_save_commit@L474', _spb_ex)

    @app.route('/api/projects/save/abort/<upload_id>', methods=['POST'])
    def api_projects_save_abort(upload_id):
        with uploads_lock:
            state = uploads.pop(upload_id, None)
        if state:
            try:
                os.remove(state['tmp'])
            except OSError as _spb_ex:
                _spb_swallow('api_projects_save_abort@L484', _spb_ex)
        return jsonify({"ok": True})

    @app.route('/api/projects/open', methods=['POST'])
    def api_projects_open():
        try:
            data = request.get_json(silent=True) or {}
            fn, full = _project_path(data.get('file'))
            if not os.path.isfile(full):
                return jsonify({"error": "project not found: %s" % fn,
                                "code": "project_not_found"}), 404
            project = _load_project(full)
            return jsonify({
                "ok": True,
                "project": project,
                "file": fn,
                "sourceStatus": _source_status(project),
            })
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            return jsonify({"error": "project is corrupt: %s" % error,
                            "code": "corrupt_project"}), 400
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_project"}), 400
        except Exception as error:
            logger.error("/api/projects/open error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/verify-source', methods=['POST'])
    def api_projects_verify_source():
        """Recheck source bytes after the asynchronous client loader settles."""
        try:
            data = request.get_json(silent=True) or {}
            fn, full = _project_path(data.get('file'))
            if not os.path.isfile(full):
                return jsonify({"error": "project not found: %s" % fn,
                                "code": "project_not_found"}), 404
            meta = _read_current_metadata(full)
            if meta is not None:
                project_identity = {
                    "sourcePaintFile": meta.get('sourcePaintFile') or '',
                    "sourceFingerprint": meta.get('sourceFingerprint'),
                    "config": {},
                }
            else:
                project_identity = _load_project(full)
            return jsonify({
                "ok": True,
                "file": fn,
                "sourceStatus": _source_status(project_identity),
            })
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            return jsonify({"error": "project metadata is corrupt: %s" % error,
                            "code": "corrupt_project"}), 400
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_project"}), 400
        except Exception as error:
            logger.error("/api/projects/verify-source error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/delete', methods=['POST'])
    def api_projects_delete():
        try:
            data = request.get_json(silent=True) or {}
            fn, full = _project_path(data.get('file'))
            if not os.path.isfile(full):
                return jsonify({"error": "project not found",
                                "code": "project_not_found"}), 404
            os.remove(full)
            try:
                os.remove(_metadata_path(full))
            except OSError as _spb_ex:
                _spb_swallow('api_projects_delete@L555', _spb_ex)
            logger.info("[projects] deleted %s" % fn)
            return jsonify({"ok": True})
        except ValueError as error:
            return jsonify({"error": str(error), "code": "invalid_project"}), 400
        except Exception as error:
            logger.error("/api/projects/delete error: %s" % error)
            return jsonify({"error": str(error)}), 500

    @app.route('/api/projects/dir', methods=['GET'])
    def api_projects_dir():
        try:
            return jsonify({"ok": True, "dir": _dir()})
        except Exception as error:
            return jsonify({"error": str(error)}), 500

    logger.info("[projects] routes registered (dir: %s)" % _dir())
