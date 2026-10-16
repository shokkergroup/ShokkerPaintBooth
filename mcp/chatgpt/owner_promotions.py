"""Recognize reviewed owner implementations without patching their kill paths."""
import hashlib
import json
import re
from pathlib import Path

CONTRACTS = Path(__file__).with_name('owner-promotion-contracts.json')

def function_text(source, name):
    start = re.search(r'^    function ' + re.escape(name) + r'\(', source, re.M)
    if not start:
        raise RuntimeError('Missing promoted function: ' + name)
    line_end = source.find('\n', start.start())
    first = source[start.start():line_end if line_end >= 0 else len(source)]
    # Known owner functions are either one-line or close at the four-space margin.
    if re.search(r'\}\s*(?://.*)?$', first):
        return first
    end = re.search(r'^    \}\s*$', source[line_end + 1:], re.M)
    if not end:
        raise RuntimeError('Unknown promoted function boundary: ' + name)
    return source[start.start():line_end + 1 + end.end()]

def fingerprint(text):
    return hashlib.sha256(text.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')).hexdigest()

def reviewed(relative, source):
    contract = json.loads(CONTRACTS.read_text(encoding='utf-8')).get(relative)
    if not contract or 'SPB_CX3_OFF' not in source:
        return None
    for name, expected in contract['functions'].items():
        if fingerprint(function_text(source, name)) != expected:
            raise RuntimeError('Promoted owner implementation changed: ' + relative + ' / ' + name)
    for fragment in contract.get('fragments', []):
        if source.count(fragment) != 1:
            raise RuntimeError('Promoted owner fragment changed: ' + relative)
    return contract

def filter_edits(relative, source, edits):
    contract = reviewed(relative, source)
    if not contract:
        return edits, False
    expected = contract.get('base_edit_count')
    if expected is not None and len(edits) != expected:
        raise RuntimeError('Private promotion edit list changed: ' + relative)
    skip = set(contract['skip_indices'])
    return [edit for i, edit in enumerate(edits) if i not in skip], True

def filter_inventory_edits(relative, source, edits):
    # Preserve the reviewed owner guard/kill switch; extend its completed-answer
    # case to saved/live design explanations, whose wording need not classify
    # as standalone advice (e.g. "why would the second suit this car?").
    if relative == 'js/spb-pbn.js' and reviewed(relative, source):
        if len(edits) != 1:
            raise RuntimeError('Private PBN inventory edit list changed')
        return [("readAns3.id === 'assistant.template_layers' &&", "(readAns3.id === 'assistant.template_layers' || readAns3.id === 'assistant.design_advice') &&", 1)]
    return edits
