"""Personal finish choices survive installer replacement and browser-origin changes."""
import json
import os
from pathlib import Path

from flask import jsonify, request
from engine.atomic_io import atomic_write_json, file_lock


def preference_path():
    return Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'ShokkerPaintBooth' / 'finish-preferences.json'


def _read(path):
    if not path.exists():
        return {'version': 1, 'favorites': {}, 'ratings': {}}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1 or not all(isinstance(data.get(k), dict) for k in ('favorites', 'ratings')):
        raise ValueError('Invalid finish preferences; existing file preserved')
    return data


def _validate(updates):
    if not isinstance(updates, dict):
        raise ValueError('Expected preference object')
    for kind in ('favorites', 'ratings'):
        values = updates.get(kind, {})
        if not isinstance(values, dict) or len(values) > 30000:
            raise ValueError('Invalid ' + kind)
        for key, value in values.items():
            if not isinstance(key, str) or not key or len(key) > 256:
                raise ValueError('Invalid finish ID')
            if kind == 'favorites' and type(value) is not bool:
                raise ValueError('Favorite must be true or false')
            if kind == 'ratings' and (type(value) is not int or not 0 <= value <= 100):
                raise ValueError('Rating must be an integer from 0 to 100')


def register_finish_preferences(app, *, path=None, external_write_guard=None):
    path = Path(path) if path is not None else preference_path()

    @app.route('/api/finish-preferences', methods=['GET', 'POST'])
    def finish_preferences():
        try:
            updates = request.get_json(silent=True) if request.method == 'POST' else None
            if request.method == 'POST':
                _validate(updates)
                if external_write_guard:
                    denial = external_write_guard(str(path), 'finish-preferences-save')
                    if denial:
                        return jsonify(denial), 403
            with file_lock(path):
                data = _read(path)
                if updates is not None:
                    # Migration only fills missing IDs. False entries retain deliberate
                    # removals, preventing an old browser profile resurrecting favorites.
                    for kind in ('favorites', 'ratings'):
                        for key, value in updates.get(kind, {}).items():
                            if not updates.get('migrate') or key not in data[kind]:
                                data[kind][key] = value
                    if path.exists():
                        atomic_write_json(str(path) + '.bak', _read(path))
                    atomic_write_json(path, data)
            return jsonify(data)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except Exception as exc:
            return jsonify(error=str(exc)), 500
