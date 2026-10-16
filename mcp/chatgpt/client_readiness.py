"""Read-only installed-client checks; no inference, setup writes or API fallback.

This is a private diagnostic, not a launcher or model entitlement check.
Version numbers alone never establish that a model can complete a turn.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

REMOVED_ENV = ('OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL',
               'OPENAI_API_BASE', 'CODEX_ACCESS_TOKEN', 'ACCESS_TOKEN')
VERSION = re.compile(r'^codex(?:-cli)?\s+(\d+\.\d+\.\d+(?:[-+][\w.]+)?)\s*$', re.M)


def run_check(executable, arguments, env):
    try:
        result = subprocess.run([executable, *arguments], shell=False,
                                capture_output=True, text=True, errors='replace',
                                env=env, timeout=8,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return result.returncode, result.stdout + '\n' + result.stderr, None
    except subprocess.TimeoutExpired:
        return None, '', 'timeout'
    except OSError:
        return None, '', 'could_not_start'


def inspect_client(executable, *, check_auth=False, runner=run_check, environ=None):
    env = dict(os.environ if environ is None else environ)
    for key in REMOVED_ENV:
        env.pop(key, None)
    path = str(Path(executable).resolve())
    row = {'path': path, 'version': None, 'version_check': 'not_checked',
           'authentication': 'not_checked', 'inference_verified': False,
           'api_fallback': False, 'settings_written': False}
    if not Path(path).is_file():
        row['version_check'] = 'not_found'
        return row
    code, output, error = runner(path, ['--version'], env)
    match = VERSION.search(output)
    if error or code != 0 or not match:
        row['version_check'] = error or 'unrecognized_client'
        return row
    row.update(version=match.group(1), version_check='passed')
    if check_auth:
        code, output, error = runner(path, ['login', 'status'], env)
        if error:
            row['authentication'] = error
        elif code == 0 and re.search(r'^Logged in using ChatGPT\s*$', output, re.M):
            row['authentication'] = 'chatgpt'
        elif re.search(r'Logged in using an API key', output, re.I):
            row['authentication'] = 'api_login_not_accepted'
        elif re.search(r'(?:Error loading config|invalid value|unknown variant)', output, re.I):
            row['authentication'] = 'configuration_error'
        elif re.search(r'Not logged in', output, re.I):
            row['authentication'] = 'not_logged_in'
        else:
            row['authentication'] = 'unverified'
    # Never persist raw output: it can contain config text or credential fragments.
    return row


def report(paths, *, check_auth=False, runner=run_check, environ=None):
    unique = []
    for candidate in paths:
        resolved = str(Path(candidate).resolve())
        if os.path.normcase(resolved) not in [os.path.normcase(p) for p in unique]:
            unique.append(resolved)
    clients = [inspect_client(p, check_auth=check_auth, runner=runner, environ=environ)
               for p in unique[:4]]
    versions = {r['version'] for r in clients if r['version']}
    return {'schema': 'spb-client-readiness/1', 'clients': clients,
            'version_mismatch': len(versions) > 1, 'selected_client': None,
            'inference_verified': False, 'api_fallback': False,
            'message': ('Multiple installed versions differ. Use the client you checked; '
                        'do not assume the PATH command matches the desktop app.'
                        if len(versions) > 1 else
                        'Client/sign-in checks do not establish model access or a listening SPB session.'),
            'next_step': 'Complete a bounded read-only SPB conversation with the chosen client before claiming it works.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', action='append', default=[],
                        help='Installed executable to inspect; at most four. Default: Codex on PATH.')
    parser.add_argument('--auth', action='store_true', help='Also run read-only login status.')
    parser.add_argument('--record', help='Optional private diagnostic JSON file.')
    args = parser.parse_args()
    if len(args.client) > 4:
        parser.error('Use at most four installed clients.')
    paths = args.client or ([shutil.which('codex')] if shutil.which('codex') else [])
    result = report(paths, check_auth=args.auth)
    if args.record:
        target = Path(args.record)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
