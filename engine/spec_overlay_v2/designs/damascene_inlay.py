# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.32; invariant nearest 0.47994 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Damascene Inlay. Identity declared before rendering/scoring."""
from ..engraved_designs import damascene_inlay
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_damascene_inlay',
 'display_name': 'Damascene Inlay - spec overlay',
 'promise': 'Damascene Inlay assembles inlaid leaf blades, scrolling inlay stems, undercut inlay '
            'channels, leaf vein burin cuts and stippling rosettes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Damascene Inlay assembles inlaid leaf blades, scrolling inlay stems, undercut '
                    'inlay channels, leaf vein burin cuts and stippling rosettes. Geometry is '
                    'independently authored in engraved_designs.py:damascene_inlay.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to inlaid leaf blades, '
                 'scrolling inlay stems, undercut inlay channels, leaf vein burin cuts, stippling '
                 'rosettes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'inlaid_leaf_blades',
                 'role': 'Inlaid leaf blades use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'scrolling_inlay_stems',
                 'role': 'Scrolling inlay stems use M/R/Cc intervals [(146, 255), (0, 92), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'undercut_inlay_channels',
                 'role': 'Undercut inlay channels use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'leaf_vein_burin_cuts',
                 'role': 'Leaf vein burin cuts use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'stippling_rosettes',
                 'role': 'Stippling rosettes use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['inlaid_leaf_blades',
                            'scrolling_inlay_stems',
                            'undercut_inlay_channels',
                            'leaf_vein_burin_cuts',
                            'stippling_rosettes'],
                      'R': ['inlaid_leaf_blades',
                            'scrolling_inlay_stems',
                            'undercut_inlay_channels',
                            'leaf_vein_burin_cuts',
                            'stippling_rosettes'],
                      'Cc': ['inlaid_leaf_blades',
                             'scrolling_inlay_stems',
                             'undercut_inlay_channels',
                             'leaf_vein_burin_cuts',
                             'stippling_rosettes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Damascene Inlay must visibly separate through inlaid leaf '
                                      'blades, scrolling inlay stems, undercut inlay channels and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_engine_turn_medallions',
                        'difference': 'Damascene Inlay must visibly separate through inlaid leaf '
                                      'blades, scrolling inlay stems, undercut inlay channels and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Alternating leaf sprigs branch from curved inlay stems.',
                                     'inlaid leaf blades is present in the native named-feature '
                                     'coverage probe.',
                                     'scrolling inlay stems is present in the native named-feature '
                                     'coverage probe.',
                                     'undercut inlay channels is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/damascene_inlay/independent-feature-carrier',
 'spec_key': 'spec-v2/damascene_inlay/named-material-bindings'}

render = build_renderer(damascene_inlay, IDENTITY_CONTRACT)
