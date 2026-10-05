# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.95; invariant nearest 0.50597 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Etched Gear. Identity declared before rendering/scoring."""
from ..machine_designs import etched_gear
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_etched_gear',
 'display_name': 'Etched Gear - spec overlay',
 'promise': 'Etched Gear assembles gear annuli, etched teeth, hub spokes, index keyway and witness '
            'dimples.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Etched Gear assembles gear annuli, etched teeth, hub spokes, index keyway and '
                    'witness dimples. Geometry is independently authored in '
                    'machine_designs.py:etched_gear.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to gear annuli, etched teeth, '
                 'hub spokes, index keyway, witness dimples.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'gear_annuli',
                 'role': 'Gear annuli use M/R/Cc intervals [(54, 246), (0, 246), (16, 244)] in their '
                         'own geometry.'},
                {'name': 'etched_teeth',
                 'role': 'Etched teeth use M/R/Cc intervals [(6, 120), (156, 250), (140, 255)] in their '
                         'own geometry.'},
                {'name': 'hub_spokes',
                 'role': 'Hub spokes use M/R/Cc intervals [(154, 255), (0, 88), (0, 122)] in their own '
                         'geometry.'},
                {'name': 'index_keyway',
                 'role': 'Index keyway use M/R/Cc intervals [(12, 148), (100, 232), (52, 178)] in their '
                         'own geometry.'},
                {'name': 'witness_dimples',
                 'role': 'Witness dimples use M/R/Cc intervals [(108, 222), (40, 136), (112, 250)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['gear_annuli',
                            'etched_teeth',
                            'hub_spokes',
                            'index_keyway',
                            'witness_dimples'],
                      'R': ['gear_annuli',
                            'etched_teeth',
                            'hub_spokes',
                            'index_keyway',
                            'witness_dimples'],
                      'Cc': ['gear_annuli',
                             'etched_teeth',
                             'hub_spokes',
                             'index_keyway',
                             'witness_dimples']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Etched Gear must visibly separate through gear annuli, etched '
                                      'teeth, hub spokes and the remaining named marks, not color or '
                                      'parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Etched Gear must visibly separate through gear annuli, etched '
                                      'teeth, hub spokes and the remaining named marks, not color or '
                                      'parameter changes.'}],
 'name_truth': {'visible_evidence': ['An etched pinion sits beside a narrow toothed rack.',
                                     'gear annuli is present in the native named-feature coverage '
                                     'probe.',
                                     'etched teeth is present in the native named-feature coverage '
                                     'probe.',
                                     'hub spokes is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/etched_gear/independent-feature-carrier',
 'spec_key': 'spec-v2/etched_gear/named-material-bindings'}

render = build_renderer(etched_gear, IDENTITY_CONTRACT)
