# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.66; invariant nearest 0.40655 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Slotted Knurl. Identity declared before rendering/scoring."""
from ..machine_designs import slotted_knurl
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_slotted_knurl',
 'display_name': 'Slotted Knurl - spec overlay',
 'promise': 'Slotted Knurl assembles knurl teeth, relief slots, tooth bevels, corner punches and worn '
            'bridges.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Slotted Knurl assembles knurl teeth, relief slots, tooth bevels, corner punches '
                    'and worn bridges. Geometry is independently authored in '
                    'machine_designs.py:slotted_knurl.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to knurl teeth, relief slots, '
                 'tooth bevels, corner punches, worn bridges.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'knurl_teeth',
                 'role': 'Knurl teeth use M/R/Cc intervals [(38, 254), (16, 182), (22, 250)] in their '
                         'own geometry.'},
                {'name': 'relief_slots',
                 'role': 'Relief slots use M/R/Cc intervals [(0, 96), (148, 255), (130, 242)] in their '
                         'own geometry.'},
                {'name': 'tooth_bevels',
                 'role': 'Tooth bevels use M/R/Cc intervals [(150, 254), (26, 128), (0, 108)] in their '
                         'own geometry.'},
                {'name': 'corner_punches',
                 'role': 'Corner punches use M/R/Cc intervals [(12, 148), (106, 226), (54, 188)] in '
                         'their own geometry.'},
                {'name': 'worn_bridges',
                 'role': 'Worn bridges use M/R/Cc intervals [(64, 218), (44, 200), (96, 254)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['knurl_teeth',
                            'relief_slots',
                            'tooth_bevels',
                            'corner_punches',
                            'worn_bridges'],
                      'R': ['knurl_teeth',
                            'relief_slots',
                            'tooth_bevels',
                            'corner_punches',
                            'worn_bridges'],
                      'Cc': ['knurl_teeth',
                             'relief_slots',
                             'tooth_bevels',
                             'corner_punches',
                             'worn_bridges']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Slotted Knurl must visibly separate through knurl teeth, relief '
                                      'slots, tooth bevels and the remaining named marks, not color or '
                                      'parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Slotted Knurl must visibly separate through knurl teeth, relief '
                                      'slots, tooth bevels and the remaining named marks, not color or '
                                      'parameter changes.'}],
 'name_truth': {'visible_evidence': ['Lozenge teeth surround long narrow relief slots.',
                                     'knurl teeth is present in the native named-feature coverage '
                                     'probe.',
                                     'relief slots is present in the native named-feature coverage '
                                     'probe.',
                                     'tooth bevels is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/slotted_knurl/independent-feature-carrier',
 'spec_key': 'spec-v2/slotted_knurl/named-material-bindings'}

render = build_renderer(slotted_knurl, IDENTITY_CONTRACT)
